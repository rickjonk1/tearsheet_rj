"""
calendar_gen.py — realistic, dynamic season-calendar generator for AI teams.

Assigns each invited team's riders to the races it is invited to, driven by:
  * specialty fit  (race discipline weights x rider characteristics)
  * rider quality  (current ability -> who leads, who supports)
  * support groups (a leader pulls in team-mates that suit the same race)
  * roster limits  (per race class min/max riders)
  * rider load     (rest days between races, no double-booking overlaps)
  * seeded variety (weighted randomness -> different every season/seed)

Deterministic for a given seed, so "not the same every year" is a knob, not chaos.
"""
from .model import Career

# a stable LCG so we never touch Math.random-style globals and stay reproducible
class _Rng:
    def __init__(self, seed):
        self.s = (seed ^ 0x9E3779B9) & 0xFFFFFFFF
    def next(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s / 0x7FFFFFFF
    def jitter(self, pct):
        return 1.0 + (self.next() * 2 - 1) * pct


def _daynum(day, month):
    return (month - 1) * 31 + day


def assign_roles(career: Career, team_id, leaders=None, coleaders=None,
                 n_leaders=3, n_coleaders=4):
    """Split a squad into leaders / co-leaders / domestiques (by ability by default)."""
    pool = sorted(career.teams[team_id]["riders"],
                  key=lambda r: career.riders[r]["ability"], reverse=True)
    leaders = list(leaders) if leaders is not None else pool[:n_leaders]
    rest = [r for r in pool if r not in leaders]
    coleaders = list(coleaders) if coleaders is not None else rest[:n_coleaders]
    captains = leaders + [r for r in coleaders if r not in leaders]
    doms = [r for r in pool if r not in captains]
    return leaders, coleaders, doms


def _best_fit(career, rid, races):
    return max((career.race_fit(rid, r["id"]) for r in races), default=1.0) or 1.0


def _overlaps(busy_list, start, end, rest_days):
    return any(not (end < s - rest_days or start > e + rest_days) for s, e in busy_list)


def generate(career: Career, seed=1, teams=None, variety=0.12, rest_days=2,
             leader_budget=62, dom_budget=85, roles=None, wt_prestige=45):
    """
    Role-based, route-aware season generation.

    1. Roles: leaders / co-leaders / domestiques (given per team via `roles`, else by ability).
    2. Captains (leaders then co-leaders) pick their OWN races — only races that FIT their
       profile (a relative fit gate, so a climber never targets a cobbled classic), taken
       prestige-first, spaced out, within a race-day budget. These become their objectives.
    3. Helpers: every captained race (plus big uncaptained races) is filled to roster size
       with the best ROUTE-FIT domestiques — so a cobbled race gets cobble riders, a
       mountainous one gets climbers.

    Returns {team_id: {"plan":[{race,name,day,month,roster,leader,captains}],
                       "objectives": {rider_id:[race_id...]},
                       "roles": {"leaders":[],"coleaders":[],"domestiques":[]}}}.
    """
    rng = _Rng(seed)
    result = {}
    target_teams = teams if teams is not None else list(career.teams)
    tset = set(target_teams)
    roles = roles or {}

    invites = {t: [] for t in target_teams}
    for r in career.races.values():
        if r["day"] == 0:
            continue
        for t in r["teams"]:
            if t in tset:
                invites[t].append(r)

    for tid in target_teams:
        pool = career.teams[tid]["riders"]
        if not pool:
            result[tid] = {"plan": [], "objectives": {}, "roles": {}}
            continue
        rr = roles.get(tid, {})
        leaders, coleaders, doms = assign_roles(career, tid, rr.get("leaders"), rr.get("coleaders"))
        races = invites[tid]
        race_by_id = {r["id"]: r for r in races}

        busy = {rid: [] for rid in pool}
        spent = {rid: 0 for rid in pool}
        captains_of = {}          # race_id -> [captain ids]
        objectives = {}           # rider_id -> [race_id]

        # --- pass 1: each captain builds a personal, fitting schedule ---
        for role_riders, gate_frac, budget in ((leaders, 0.90, leader_budget),
                                               (coleaders, 0.83, dom_budget - 10)):
            for cap in role_riders:
                best = _best_fit(career, cap, races)
                gate = best * gate_frac
                cand = [r for r in races if career.race_fit(cap, r["id"]) >= gate]
                # prestige-first, small jitter so seasons differ
                cand.sort(key=lambda r: -(r["popularity"] * rng.jitter(variety)))
                for r in cand:
                    days = max(1, r["stages"])
                    s = _daynum(r["day"], r["month"]); e = s + days - 1
                    if spent[cap] + days > budget:
                        continue
                    if _overlaps(busy[cap], s, e, rest_days):
                        continue
                    busy[cap].append((s, e)); spent[cap] += days
                    captains_of.setdefault(r["id"], []).append(cap)
                    objectives.setdefault(cap, []).append(r["id"])

        # --- pass 2: fill helpers by route fit ---
        # races to field: everything a captain wants + big races (so the team still shows up)
        field = set(captains_of)
        for r in races:
            if r["popularity"] >= wt_prestige:
                field.add(r["id"])
        plan = []
        for rid_ in sorted(field, key=lambda x: _daynum(race_by_id[x]["day"], race_by_id[x]["month"])):
            r = race_by_id[rid_]
            days = max(1, r["stages"])
            s = _daynum(r["day"], r["month"]); e = s + days - 1
            lo, hi = career.class_limits.get(r["klass"], (6, 7))
            caps = list(captains_of.get(rid_, []))
            roster = list(caps)
            # candidate helpers: domestiques (and spare co-leaders) available, by ROUTE fit
            cand = []
            for rid2 in pool:
                if rid2 in roster:
                    continue
                if spent[rid2] + days > (leader_budget if rid2 in leaders else dom_budget):
                    continue
                if _overlaps(busy[rid2], s, e, rest_days):
                    continue
                fit = career.race_fit(rid2, rid_)
                cand.append(((fit + career.riders[rid2]["ability"] * 0.3) * rng.jitter(variety), fit, rid2))
            cand.sort(reverse=True)
            for _, _, rid2 in cand:
                if len(roster) >= hi:
                    break
                roster.append(rid2)
            if len(roster) < lo:
                continue
            for rid2 in roster:
                if (s, e) not in busy[rid2]:
                    busy[rid2].append((s, e)); spent[rid2] += days
            leader = caps[0] if caps else max(
                roster, key=lambda x: career.riders[x]["ability"])
            plan.append({"race": rid_, "name": r["name"], "day": r["day"], "month": r["month"],
                         "roster": roster, "leader": leader, "captains": caps})
        plan.sort(key=lambda p: _daynum(p["day"], p["month"]))
        result[tid] = {"plan": plan, "objectives": objectives,
                       "roles": {"leaders": leaders, "coleaders": coleaders, "domestiques": doms}}
    return result


def apply(career: Career, generated, objectives=True):
    """Write generated rosters (and optionally objectives) back into the database."""
    tr = career.db["DYN_team_race"]
    teamcol, racecol = tr.column("fkIDteam"), tr.column("fkIDrace")
    roster_col = tr.column("gene_ilist_roster")
    index = {}
    for i in range(tr.nrow):
        index[(teamcol[i], racecol[i])] = i
    changed = 0
    all_obj = {}
    for tid, res in generated.items():
        plan = res["plan"] if isinstance(res, dict) else res
        for entry in plan:
            key = (tid, entry["race"])
            if key in index:
                roster_col[index[key]] = list(entry["roster"])
                changed += 1
        if isinstance(res, dict):
            all_obj.update(res.get("objectives", {}))
    tr.set_column("gene_ilist_roster", roster_col)
    if objectives and all_obj:
        _apply_objectives(career, all_obj)
    return changed


def _apply_objectives(career: Career, obj_by_rider):
    """Rebuild DYN_cyclist_objective from generated captain->races objectives,
    replacing objectives for the involved riders."""
    t = career.db["DYN_cyclist_objective"]
    ids = t.column("IDcyclist_objective")
    cyc = t.column("fkIDcyclist")
    rac = t.column("fkIDrace")
    involved = set(obj_by_rider)
    keep = [i for i in range(len(ids)) if cyc[i] not in involved]
    nids = [ids[i] for i in keep]
    ncyc = [cyc[i] for i in keep]
    nrac = [rac[i] for i in keep]
    nxt = (max(ids) + 1) if ids else 1
    for rider, races in obj_by_rider.items():
        for r in races:
            nids.append(nxt); ncyc.append(rider); nrac.append(r); nxt += 1
    t.set_data({"IDcyclist_objective": nids, "fkIDcyclist": ncyc, "fkIDrace": nrac})
