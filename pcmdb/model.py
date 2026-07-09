"""
model.py — high-level career facade for the app.

Turns the raw tables into ergonomic objects the UI/planner/generator use:
riders (with characteristics + derived specialty), races (with dates, class,
discipline weights, invited teams) and teams. Editing goes back through the
proven schema layer so it can be saved to a game-readable .cdb.
"""
from . import cdb
from .schema import Database

# race_type discipline weight  ->  rider characteristic
WEIGHT_TO_CHARAC = {
    "mo_weight": "charac_i_mountain",
    "mm_weight": "charac_i_medium_mountain",
    "val_weight": "charac_i_hill",
    "rec_weight": "charac_i_recuperation",
    "itt_weight": "charac_i_timetrial",
    "prl_weight": "charac_i_prologue",
    "sp_weight": "charac_i_sprint",
    "pav_weight": "charac_i_cobble",
    "pl_weight": "charac_i_plain",
}

# characteristic -> short specialty label (for the derived rider profile)
SPECIALTY = [
    ("charac_i_mountain", "Klimmer"),
    ("charac_i_sprint", "Sprinter"),
    ("charac_i_timetrial", "Tijdrijder"),
    ("charac_i_cobble", "Kasseienspecialist"),
    ("charac_i_hill", "Puncheur"),
    ("charac_i_medium_mountain", "Heuvelklimmer"),
    ("charac_i_baroudeur", "Aanvaller"),
    ("charac_i_plain", "Rouleur"),
]
CHARAC_LABELS = {
    "charac_i_mountain": "Berg", "charac_i_medium_mountain": "Midden-berg",
    "charac_i_hill": "Heuvel", "charac_i_plain": "Vlak",
    "charac_i_timetrial": "Tijdrit", "charac_i_prologue": "Proloog",
    "charac_i_sprint": "Sprint", "charac_i_cobble": "Kasseien",
    "charac_i_acceleration": "Versnelling", "charac_i_endurance": "Uithouding",
    "charac_i_resistance": "Weerstand", "charac_i_recuperation": "Herstel",
    "charac_i_baroudeur": "Vluchter", "charac_i_downhilling": "Afdaling",
}


class Career:
    def __init__(self, db: Database, path=None):
        self.db = db
        self.path = path
        self._build()

    @classmethod
    def load(cls, path):
        return cls(Database.load(path), path)

    def _col(self, table, name):
        return self.db[table].column(name)

    def _build(self):
        db = self.db
        # ---- races & stages ----
        st = db["STA_stage"]
        sid, sday, smon = st.column("IDstage"), st.column("gene_i_day"), st.column("gene_i_month")
        stage_date = {sid[i]: (sday[i], smon[i]) for i in range(st.nrow)}

        rt = db["STA_race_type"]
        rtid = rt.column("IDrace_type")
        wcols = [c for c in rt.colnames if c.endswith("_weight")]
        type_weights = {rtid[i]: {c: rt.column(c)[i] for c in wcols} for i in range(rt.nrow)}

        ra = db["STA_race"]
        self.races = {}
        cols = {c: ra.column(c) for c in ["IDrace", "gene_sz_race_name", "fkIDrace_class",
                "fkIDrace_type", "gene_f_popularity", "fkIDcountry", "fkIDfirst_stage",
                "gene_i_number_stages", "gene_ilist_fkIDteam"]}
        for i in range(ra.nrow):
            rid = cols["IDrace"][i]
            fs = cols["fkIDfirst_stage"][i]
            d, m = stage_date.get(fs, (0, 0))
            self.races[rid] = {
                "id": rid, "name": cols["gene_sz_race_name"][i],
                "klass": cols["fkIDrace_class"][i], "type": cols["fkIDrace_type"][i],
                "popularity": round(cols["gene_f_popularity"][i], 1),
                "country": cols["fkIDcountry"][i], "day": d, "month": m,
                "stages": cols["gene_i_number_stages"][i],
                "teams": list(cols["gene_ilist_fkIDteam"][i]),
                "weights": type_weights.get(cols["fkIDrace_type"][i], {}),
            }

        # roster limits per race class
        rc = db["STA_race_class"]
        rcid = rc.column("IDrace_class")
        self.class_limits = {rcid[i]: (rc.column("gene_i_min_riders")[i],
                                       rc.column("gene_i_max_riders")[i]) for i in range(rc.nrow)}

        # ---- teams ----
        tm = db["DYN_team"]
        tid = tm.column("IDteam")
        namecol = next((c for c in tm.colnames if "name" in c.lower()), None)
        tnm = tm.column(namecol) if namecol else None
        self.teams = {tid[i]: {"id": tid[i], "name": (tnm[i] if tnm else str(tid[i])),
                               "riders": []} for i in range(tm.nrow)}

        # ---- riders ----
        cy = db["DYN_cyclist"]
        n = cy.nrow
        c = {name: cy.column(name) for name in ["IDcyclist", "gene_sz_lastname",
             "gene_sz_firstname", "fkIDteam", "value_f_current_ability",
             "value_f_potentiel", "gene_i_birthdate", "fkIDtype_rider"]}
        charac_cols = [x for x in cy.colnames if x.startswith("charac_i_")]
        cvals = {x: cy.column(x) for x in charac_cols}
        self.riders = {}
        for i in range(n):
            rid = c["IDcyclist"][i]
            ch = {x: cvals[x][i] for x in charac_cols}
            spec, specval = "Rouleur", 0
            for key, label in SPECIALTY:
                if ch.get(key, 0) > specval:
                    specval, spec = ch.get(key, 0), label
            r = {
                "id": rid, "first": c["gene_sz_firstname"][i], "last": c["gene_sz_lastname"][i],
                "team": c["fkIDteam"][i], "ability": round(c["value_f_current_ability"][i], 1),
                "potential": round(c["value_f_potentiel"][i], 1),
                "type": c["fkIDtype_rider"][i], "charac": ch, "specialty": spec,
            }
            self.riders[rid] = r
            if c["fkIDteam"][i] in self.teams:
                self.teams[c["fkIDteam"][i]]["riders"].append(rid)

        # ---- objectives (rider -> target races) ----
        co = db["DYN_cyclist_objective"]
        self._obj_id = co.column("IDcyclist_objective")
        self._obj_cyc = co.column("fkIDcyclist")
        self._obj_race = co.column("fkIDrace")

    def objectives_for_race(self, race_id):
        return {self._obj_cyc[i] for i in range(len(self._obj_race)) if self._obj_race[i] == race_id}

    def rider_objectives(self, rider_id):
        return [self._obj_race[i] for i in range(len(self._obj_cyc)) if self._obj_cyc[i] == rider_id]

    def toggle_objective(self, rider_id, race_id):
        """Add/remove a rider's objective for a race; rebuilds DYN_cyclist_objective."""
        ids, cyc, rac = self._obj_id, self._obj_cyc, self._obj_race
        keep = [i for i in range(len(ids)) if not (cyc[i] == rider_id and rac[i] == race_id)]
        if len(keep) == len(ids):                      # not present -> add
            new_id = (max(ids) + 1) if ids else 1
            ids.append(new_id); cyc.append(rider_id); rac.append(race_id)
            added = True
        else:                                          # present -> remove
            ids[:] = [ids[i] for i in keep]
            cyc[:] = [cyc[i] for i in keep]
            rac[:] = [rac[i] for i in keep]
            added = False
        self.db["DYN_cyclist_objective"].set_data({
            "IDcyclist_objective": ids, "fkIDcyclist": cyc, "fkIDrace": rac})
        return added

    # ---- fit scoring ----
    def race_fit(self, rider_id, race_id):
        """0..100 how well a rider's profile matches a race's demands."""
        r = self.riders.get(rider_id); ra = self.races.get(race_id)
        if not r or not ra:
            return 0.0
        w = ra["weights"]
        tot = sum(w.values()) or 1
        s = 0.0
        for wk, ck in WEIGHT_TO_CHARAC.items():
            s += w.get(wk, 0) * r["charac"].get(ck, 0)
        return round(s / tot, 1)

    def rider_label(self, rid):
        r = self.riders.get(rid)
        return f"{r['first']} {r['last']}".strip() if r else str(rid)

    # ---- season program (editable) ----
    def season_program(self, team_id):
        tr = self.db["DYN_team_race"]
        teamcol, racecol, roster = (tr.column("fkIDteam"), tr.column("fkIDrace"),
                                    tr.column("gene_ilist_roster"))
        out = []
        for i in range(tr.nrow):
            if teamcol[i] != team_id:
                continue
            ra = self.races.get(racecol[i], {})
            out.append({"row": i, "race": racecol[i], "name": ra.get("name", "?"),
                        "day": ra.get("day", 0), "month": ra.get("month", 0),
                        "klass": ra.get("klass", 0), "popularity": ra.get("popularity", 0),
                        "roster": list(roster[i])})
        out.sort(key=lambda e: (e["month"], e["day"]))
        return out

    def set_roster(self, row, rider_ids):
        tr = self.db["DYN_team_race"]
        col = tr.column("gene_ilist_roster")
        col[row] = list(rider_ids)
        tr.set_column("gene_ilist_roster", col)

    def save(self, path=None):
        cdb.save(path or self.path, self.db.root)
