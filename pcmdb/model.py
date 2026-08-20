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
    # ---- how a race reads: its jersey and its elevation profile ----
    # The classification jerseys are the legend this product is drawn in, so the
    # mapping from a race's discipline weights to a jersey lives with the data.
    def race_discipline(self, race_id):
        """One of gc / mtn / spr / cls / itt — what kind of race this is."""
        ra = self.races.get(race_id, {})
        w = ra.get("weights") or {}
        if not w:
            return "gc"
        if ra.get("stages", 1) > 3:
            return "gc"                                   # a stage race is a stage race
        ranked = max(w, key=lambda k: w.get(k, 0))
        return {"pav_weight": "cls", "sp_weight": "spr", "pl_weight": "spr",
                "mo_weight": "mtn", "mm_weight": "mtn", "val_weight": "mtn",
                "itt_weight": "itt", "prl_weight": "itt"}.get(ranked, "gc")

    def race_profile(self, race_id, points=9):
        """A tiny elevation sawtooth (0 = valley, 1 = summit) drawn from the race's
        own climbing weights — flat races read flat, mountain races spike."""
        ra = self.races.get(race_id, {})
        w = ra.get("weights") or {}
        total = sum(w.values()) or 1
        climb = (w.get("mo_weight", 0) * 1.0 + w.get("mm_weight", 0) * 0.7
                 + w.get("val_weight", 0) * 0.45) / total          # 0..~1
        out = []
        for i in range(points):
            # deterministic pseudo-relief so a race always draws the same shape
            wave = ((i * 7 + race_id * 13) % 11) / 10.0
            out.append(round(min(1.0, 0.08 + climb * (0.35 + wave * 1.25)), 3))
        return out

    def season_program(self, team_id):
        tr = self.db["DYN_team_race"]
        teamcol, racecol, roster = (tr.column("fkIDteam"), tr.column("fkIDrace"),
                                    tr.column("gene_ilist_roster"))
        out = []
        for i in range(tr.nrow):
            if teamcol[i] != team_id:
                continue
            rid = racecol[i]
            ra = self.races.get(rid, {})
            out.append({"row": i, "race": rid, "name": ra.get("name", "?"),
                        "day": ra.get("day", 0), "month": ra.get("month", 0),
                        "klass": ra.get("klass", 0), "popularity": ra.get("popularity", 0),
                        "stages": ra.get("stages", 1),
                        "disc": self.race_discipline(rid),
                        "profile": self.race_profile(rid),
                        "roster": list(roster[i])})
        out.sort(key=lambda e: (e["month"], e["day"]))
        return out

    # ---- schedule / load / conflicts ----
    def _race_range(self, race_id):
        ra = self.races.get(race_id, {})
        start = (ra.get("month", 0) - 1) * 31 + ra.get("day", 0)
        return start, start + max(1, ra.get("stages", 1)) - 1, max(1, ra.get("stages", 1))

    def team_load(self, team_id, rest_days=2):
        """Per-rider race load + scheduling conflicts for a team's season."""
        prog = self.season_program(team_id)
        byrider = {}
        for e in prog:
            for rid in e["roster"]:
                byrider.setdefault(rid, []).append(e["race"])
        load, conflicts = {}, []
        for rid, races in byrider.items():
            rr = sorted(races, key=lambda r: self._race_range(r)[0])
            days = sum(self._race_range(r)[2] for r in rr)
            bad = set()
            for i in range(len(rr) - 1):
                a, b = rr[i], rr[i + 1]
                sa, ea, _ = self._race_range(a)
                sb, eb, _ = self._race_range(b)
                if sb <= ea:
                    conflicts.append({"rider": rid, "a": a, "b": b, "kind": "overlap"})
                    bad.update((a, b))
                elif sb - ea <= rest_days:
                    conflicts.append({"rider": rid, "a": a, "b": b, "kind": "rest"})
                    bad.update((a, b))
            load[rid] = {"racedays": days, "races": len(rr), "conflicts": len(bad),
                         "conflict_races": list(bad)}
        return {"load": load, "conflicts": conflicts, "byrider": byrider}

    def race_busy_riders(self, team_id, race_id):
        """Riders whose other commitments overlap this race's dates."""
        s0, e0, _ = self._race_range(race_id)
        info = self.team_load(team_id)
        busy = set()
        for rid, races in info["byrider"].items():
            for r in races:
                if r == race_id:
                    continue
                s, e, _ = self._race_range(r)
                if not (e0 < s or s0 > e):
                    busy.add(rid); break
        return busy

    def set_roster(self, row, rider_ids):
        tr = self.db["DYN_team_race"]
        col = tr.column("gene_ilist_roster")
        col[row] = list(rider_ids)
        tr.set_column("gene_ilist_roster", col)

    # ---- season year (derived, works for any career year incl. 2040) ----
    def season_year(self):
        if getattr(self, "_year", None) is None:
            cd = self.db["STA_stage"].column("gene_i_computed_date")
            years = [c // 10000 for c in cd if c > 10000000]
            self._year = max(set(years), key=years.count) if years else 2026
        return self._year

    # ---- form / fitness (DYN_cyclist_fitness — the fatigue system) ----
    FIT_FIELDS = {"fit": "value_f_FIT", "fatigue": "value_f_fat_phy",
                  "freshness": "value_f_freshness", "prepa": "value_f_prepa",
                  "peak": "peak_value"}

    def _fitness_index(self):
        if getattr(self, "_fit_idx", None) is None:
            ids = self.db["DYN_cyclist_fitness"].column("IDcyclist")
            self._fit_idx = {ids[i]: i for i in range(len(ids))}
        return self._fit_idx

    def team_form(self, team_id):
        t = self.db["DYN_cyclist_fitness"]
        idx = self._fitness_index()
        cols = {k: t.column(v) for k, v in self.FIT_FIELDS.items()}
        out = []
        for rid in self.teams[team_id]["riders"]:
            i = idx.get(rid)
            if i is None:
                continue
            r = self.riders[rid]
            out.append({"id": rid, "name": self.rider_label(rid), "ability": r["ability"],
                        "specialty": r["specialty"],
                        **{k: round(cols[k][i], 1) for k in self.FIT_FIELDS}})
        out.sort(key=lambda x: x["ability"], reverse=True)
        return out

    def set_form(self, rider_id, fields):
        t = self.db["DYN_cyclist_fitness"]
        i = self._fitness_index().get(rider_id)
        if i is None:
            raise KeyError("no fitness row for rider %d" % rider_id)
        for k, v in fields.items():
            col_name = self.FIT_FIELDS.get(k)
            if not col_name:
                continue
            vals = t.column(col_name)
            vals[i] = float(v)
            t.set_column(col_name, vals)

    # ---- dynamic form: peak windows (DYN_cyclist_fitpeak_history) ----
    # PCM rules (localstrings 79/80/81/153): a rider has at most TWO fitness peaks,
    # and they must be >= 10 weeks (70 days) apart.
    MAX_PEAKS = 2
    PEAK_MIN_GAP_DAYS = 70

    def set_peaks(self, rider_id, target_dates, lead_days=20):
        """Replace a rider's CURRENT-season peak windows so they peak on their
        target races. `target_dates` are YYYYMMDD ints in PRIORITY order (most
        important first). Selects <=2 dates that are >=10 weeks apart. Other
        seasons are untouched."""
        import datetime

        def to_date(d):
            try:
                return datetime.date(d // 10000, (d // 100) % 100, d % 100)
            except ValueError:
                return None
        # greedily pick, by priority, dates that respect the 10-week spacing
        chosen = []
        for d in target_dates:
            dd = to_date(d)
            if dd is None:
                continue
            if all(abs((dd - c).days) >= self.PEAK_MIN_GAP_DAYS for c in chosen):
                chosen.append(dd)
            if len(chosen) >= self.MAX_PEAKS:
                break
        chosen.sort()

        year = self.season_year()
        t = self.db["DYN_cyclist_fitpeak_history"]
        ids = t.column("IDcyclist_fitpeak_history"); cyc = t.column("fkIDcyclist")
        b = t.column("value_i_date_begin"); emin = t.column("value_i_date_end_min")
        emax = t.column("value_i_date_end_max")
        keep = [i for i in range(len(ids))
                if not (cyc[i] == rider_id and b[i] // 10000 == year)]
        nids = [ids[i] for i in keep]; ncyc = [cyc[i] for i in keep]
        nb = [b[i] for i in keep]; nmin = [emin[i] for i in keep]; nmax = [emax[i] for i in keep]
        nxt = (max(ids) + 1) if ids else 1
        for end in chosen:
            begin = end - datetime.timedelta(days=lead_days)
            bi = begin.year * 10000 + begin.month * 100 + begin.day
            di = end.year * 10000 + end.month * 100 + end.day
            nids.append(nxt); ncyc.append(rider_id); nb.append(bi)
            nmin.append(di); nmax.append(di); nxt += 1
        t.set_data({"IDcyclist_fitpeak_history": nids, "fkIDcyclist": ncyc,
                    "value_i_date_begin": nb, "value_i_date_end_min": nmin,
                    "value_i_date_end_max": nmax})

    # ---- training camps (STA_training_stages / DYN_training_stage_booking) ----
    def camps(self, month=None):
        t = self.db["STA_training_stages"]
        cols = {c: t.column(c) for c in ["IDtraining_stage", "gene_sz_place", "gene_i_stars",
                "fkIDtype_stage", "gene_i_opening_month", "gene_i_closing_month"]}
        out = []
        for i in range(t.nrow):
            om, cm = cols["gene_i_opening_month"][i], cols["gene_i_closing_month"][i]
            if month is not None and not (om <= month <= cm):
                continue
            out.append({"id": cols["IDtraining_stage"][i], "place": cols["gene_sz_place"][i],
                        "stars": cols["gene_i_stars"][i], "type": cols["fkIDtype_stage"][i],
                        "open": om, "close": cm,
                        "altitude": cols["fkIDtype_stage"][i] == 9})
        out.sort(key=lambda c: (-c["stars"], c["place"]))
        return out

    def team_camps(self, team_id):
        t = self.db["DYN_training_stage_booking"]
        if t.nrow == 0:
            return []
        cols = {c: t.column(c) for c in t.colnames}
        camp_name = {c["id"]: c["place"] for c in self.camps()}
        out = []
        for i in range(t.nrow):
            if cols["fkIDteam"][i] != team_id:
                continue
            out.append({"row": i, "stage": cols["fkIDtraining_stage"][i],
                        "place": camp_name.get(cols["fkIDtraining_stage"][i], "?"),
                        "start": cols["gene_i_start_date"][i], "end": cols["gene_i_end_date"][i]})
        return out

    def plan_altitude(self, team_id, target_yyyymmdd, days=18, lead=7):
        """Book the best altitude camp that's open before `target`, ending ~`lead`
        days before it. Returns {id, place, start, end} or None."""
        import datetime
        y, m, d = target_yyyymmdd // 10000, (target_yyyymmdd // 100) % 100, target_yyyymmdd % 100
        try:
            end_d = datetime.date(y, m, d) - datetime.timedelta(days=lead)
        except ValueError:
            return None
        start_d = end_d - datetime.timedelta(days=days)
        cm = end_d.month
        cand = [c for c in self.camps() if c["altitude"] and c["open"] <= cm <= c["close"]]
        if not cand:
            cand = [c for c in self.camps() if c["altitude"]]
        if not cand:
            return None
        camp = max(cand, key=lambda c: c["stars"])
        start = start_d.year * 10000 + start_d.month * 100 + start_d.day
        end = end_d.year * 10000 + end_d.month * 100 + end_d.day
        self.book_camp(team_id, camp["id"], start, end)
        return {"id": camp["id"], "place": camp["place"], "start": start, "end": end, "stars": camp["stars"]}

    # ---- recons (DYN_training_stage_recon: rider -> stage) ----
    def _stage_race_maps(self):
        if getattr(self, "_srmap", None) is None:
            st = self.db["STA_stage"]
            sid = st.column("IDstage"); rid = st.column("fkIDrace")
            self._stage_to_race = {sid[i]: rid[i] for i in range(st.nrow)}
            self._race_to_stages = {}
            for i in range(st.nrow):
                self._race_to_stages.setdefault(rid[i], []).append(sid[i])
            self._srmap = True
        return self._stage_to_race, self._race_to_stages

    def rider_recon_races(self, rider_id):
        s2r, _ = self._stage_race_maps()
        t = self.db["DYN_training_stage_recon"]
        cyc = t.column("fkIDcyclist"); stg = t.column("fkIDstage")
        return {s2r.get(stg[i]) for i in range(t.nrow) if cyc[i] == rider_id}

    def set_recon(self, rider_id, race_id, on):
        _, r2s = self._stage_race_maps()
        stages = set(r2s.get(race_id, []))
        t = self.db["DYN_training_stage_recon"]
        ids = t.column("IDtraining_stage_recon")
        cyc = t.column("fkIDcyclist"); stg = t.column("fkIDstage")
        if on:
            have = {stg[i] for i in range(len(ids)) if cyc[i] == rider_id}
            nxt = (max(ids) + 1) if ids else 1
            for s in stages:
                if s not in have:
                    ids.append(nxt); cyc.append(rider_id); stg.append(s); nxt += 1
        else:
            keep = [i for i in range(len(ids)) if not (cyc[i] == rider_id and stg[i] in stages)]
            ids[:] = [ids[i] for i in keep]; cyc[:] = [cyc[i] for i in keep]; stg[:] = [stg[i] for i in keep]
        t.set_data({"IDtraining_stage_recon": ids, "fkIDcyclist": cyc, "fkIDstage": stg})

    def book_camp(self, team_id, stage_id, start_yyyymmdd, end_yyyymmdd, efficacite=None):
        """Book a training camp. PCM allows only ONE camp per team (localstrings
        369), so any existing booking for this team is replaced."""
        t = self.db["DYN_training_stage_booking"]
        data = {c: t.column(c) for c in t.colnames}
        # drop this team's existing booking(s) — one camp per team
        keep = [i for i in range(t.nrow) if data["fkIDteam"][i] != team_id]
        for c in t.colnames:
            data[c] = [data[c][i] for i in keep]
        new_id = (max(data["IDtraining_stage_booking"]) + 1) if data["IDtraining_stage_booking"] else 1
        stars = next((c["stars"] for c in self.camps() if c["id"] == stage_id), 3)
        state0 = min(self.db["STA_training_stages_state"].column("IDtraining_stage_state"))
        row = {"IDtraining_stage_booking": new_id, "fkIDtraining_stage": stage_id,
               "gene_i_start_date": start_yyyymmdd, "gene_i_end_date": end_yyyymmdd,
               "fkIDteam": team_id, "fkIDstate": state0,
               "value_i_efficacite": efficacite if efficacite is not None else stars * 20}
        for c in t.colnames:
            data[c].append(row.get(c, 0))
        t.set_data(data)
        return new_id

    # ---- bike balance (STA_equipment_template frame archetypes) ----
    FRAME_LABELS = {"plain": "Aero (vlak/sprint)", "mountain": "Bergfiets (klim)",
                    "poly": "Allround", "cobbles": "Comfort (kasseien)",
                    "tt_flat": "Tijdrit (vlak)", "tt_poly": "Tijdrit (heuvel)"}

    @staticmethod
    def _frame_base(name):
        import re
        return re.sub(r"\d+$", "", name)

    def bike_frames(self):
        """Frame archetypes (grouped over their 4 versions) with aero/light/comfort."""
        t = self.db["STA_equipment_template"]
        typ = t.column("fkIDequipment_type"); cst = t.column("CONSTANT")
        a = t.column("gene_i_weight_aero"); li = t.column("gene_i_weight_light")
        cf = t.column("gene_i_weight_confort")
        out = {}
        for i in range(t.nrow):
            if typ[i] != 1:
                continue
            base = self._frame_base(cst[i])
            out.setdefault(base, {"base": base, "label": self.FRAME_LABELS.get(base, base),
                                  "aero": a[i], "light": li[i], "confort": cf[i], "count": 0})
            out[base]["count"] += 1
        order = ["plain", "poly", "mountain", "cobbles", "tt_flat", "tt_poly"]
        return sorted(out.values(), key=lambda x: order.index(x["base"]) if x["base"] in order else 99)

    def set_frame_archetype(self, base, aero, light, confort):
        """Set aero/light/comfort for every version of a frame archetype."""
        t = self.db["STA_equipment_template"]
        typ = t.column("fkIDequipment_type"); cst = t.column("CONSTANT")
        a = t.column("gene_i_weight_aero"); li = t.column("gene_i_weight_light")
        cf = t.column("gene_i_weight_confort")
        for i in range(t.nrow):
            if typ[i] == 1 and self._frame_base(cst[i]) == base:
                a[i] = int(aero); li[i] = int(light); cf[i] = int(confort)
        t.set_column("gene_i_weight_aero", a)
        t.set_column("gene_i_weight_light", li)
        t.set_column("gene_i_weight_confort", cf)

    # a rebalance that turns the "poly dominates" default into genuine specialisation
    REBALANCE_SPECIALISED = {
        "plain":    (3, 0, 1),   # aero bike: best on the flat, poor climbing
        "mountain": (0, 3, 1),   # climbing bike: best on climbs, poor aero
        "poly":     (2, 2, 1),   # all-round: a compromise, never the best
        "cobbles":  (0, 1, 3),   # comfort: cobbles only
        "tt_flat":  (3, 0, 0),
        "tt_poly":  (3, 1, 0),
    }

    def rebalance_bikes(self, preset=None):
        preset = preset or self.REBALANCE_SPECIALISED
        for base, (a, l, c) in preset.items():
            self.set_frame_archetype(base, a, l, c)

    def save(self, path=None):
        cdb.save(path or self.path, self.db.root)
