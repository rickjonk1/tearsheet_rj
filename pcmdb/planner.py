"""
planner.py — season-planner domain model on top of the typed schema layer.

The season planner is really an editor over three tables:

  * STA_race / STA_stage  -> the race calendar (names, class, dates)
  * DYN_team_race         -> which team rides which race, with `gene_ilist_roster`
                             (the list of assigned cyclist ids) — the core editable link
  * DYN_cyclist_objective -> per-rider race objectives

This module joins them into an ergonomic API so a UI (or CLI) can list a team's
season program, and add/remove riders from a race roster, then save back to .cdb.
"""
from . import cdb
from .schema import Database


class RaceEntry:
    """One race in a team's season program."""
    def __init__(self, team_race_row, race_id, name, klass, day, month, roster):
        self.team_race_row = team_race_row   # index into DYN_team_race (edit anchor)
        self.race_id = race_id
        self.name = name
        self.klass = klass
        self.day = day
        self.month = month
        self.roster = roster                 # list[int] cyclist ids

    @property
    def date_key(self):
        return (self.month, self.day)


class Planner:
    def __init__(self, db: Database):
        self.db = db
        self._build_lookups()

    @classmethod
    def load(cls, path):
        return cls(Database.load(path))

    def _build_lookups(self):
        cyc = self.db["DYN_cyclist"]
        cid = cyc.column("IDcyclist")
        ln = cyc.column("gene_sz_lastname")
        fn = cyc.column("gene_sz_firstname")
        self.rider_name = {cid[i]: (fn[i], ln[i]) for i in range(cyc.nrow)}

        tm = self.db["DYN_team"]
        tid = tm.column("IDteam")
        namecol = next((c for c in tm.colnames if "name" in c.lower()), None)
        tnm = tm.column(namecol) if namecol else None
        self.team_name = {tid[i]: (tnm[i] if tnm else str(tid[i])) for i in range(tm.nrow)}

        ra = self.db["STA_race"]
        rid = ra.column("IDrace")
        self.race_name = {rid[i]: ra.column("gene_sz_race_name")[i] for i in range(ra.nrow)}
        self.race_class = {rid[i]: ra.column("fkIDrace_class")[i] for i in range(ra.nrow)}
        first = ra.column("fkIDfirst_stage")
        self.race_first_stage = {rid[i]: first[i] for i in range(ra.nrow)}

        st = self.db["STA_stage"]
        sid = st.column("IDstage")
        sday = st.column("gene_i_day")
        smon = st.column("gene_i_month")
        self.stage_date = {sid[i]: (sday[i], smon[i]) for i in range(st.nrow)}

    def teams(self):
        """Return {team_id: name} sorted by name."""
        return dict(sorted(self.team_name.items(), key=lambda kv: str(kv[1])))

    def rider_label(self, cid):
        fn, ln = self.rider_name.get(cid, ("", str(cid)))
        return f"{fn} {ln}".strip()

    def season_program(self, team_id):
        """List[RaceEntry] for `team_id`, sorted by date."""
        tr = self.db["DYN_team_race"]
        teamcol = tr.column("fkIDteam")
        racecol = tr.column("fkIDrace")
        roster = tr.column("gene_ilist_roster")
        out = []
        for i in range(tr.nrow):
            if teamcol[i] != team_id:
                continue
            r = racecol[i]
            fs = self.race_first_stage.get(r)
            d, m = self.stage_date.get(fs, (0, 0))
            out.append(RaceEntry(
                team_race_row=i, race_id=r,
                name=self.race_name.get(r, "?"),
                klass=self.race_class.get(r, 0),
                day=d, month=m, roster=list(roster[i]),
            ))
        out.sort(key=lambda e: e.date_key)
        return out

    # ---- mutations ----

    def set_roster(self, team_race_row, cyclist_ids):
        tr = self.db["DYN_team_race"]
        col = tr.column("gene_ilist_roster")
        col[team_race_row] = list(cyclist_ids)
        tr.set_column("gene_ilist_roster", col)

    def add_rider(self, team_race_row, cyclist_id):
        tr = self.db["DYN_team_race"]
        col = tr.column("gene_ilist_roster")
        if cyclist_id not in col[team_race_row]:
            col[team_race_row] = col[team_race_row] + [cyclist_id]
            tr.set_column("gene_ilist_roster", col)

    def remove_rider(self, team_race_row, cyclist_id):
        tr = self.db["DYN_team_race"]
        col = tr.column("gene_ilist_roster")
        if cyclist_id in col[team_race_row]:
            col[team_race_row] = [x for x in col[team_race_row] if x != cyclist_id]
            tr.set_column("gene_ilist_roster", col)

    def save(self, path):
        cdb.save(path, self.db.root)
