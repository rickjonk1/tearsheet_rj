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


def generate(career: Career, seed=1, teams=None, variety=0.15, rest_days=2, day_budget=80):
    """
    Realistic season assignment: {team_id: [ {race, name, day, month, roster, leader} ]}.

    Realism rules (so top riders focus on real races, not tiny ones):
      * races are filled PRESTIGE-FIRST, so the biggest races get first pick of riders;
      * a rider is penalised for racing far below their level -> stars avoid small races,
        domestiques fill them;
      * each rider has a season race-day BUDGET so nobody rides the whole calendar.
    Does not mutate the career; call `apply` to write results into DYN_team_race.
    """
    rng = _Rng(seed)
    result = {}
    target_teams = teams if teams is not None else list(career.teams)
    tset = set(target_teams)

    invites = {t: [] for t in target_teams}
    for r in career.races.values():
        if r["day"] == 0:
            continue
        for t in r["teams"]:
            if t in tset:
                invites[t].append(r)

    for tid in target_teams:
        roster_pool = career.teams[tid]["riders"]
        if not roster_pool:
            result[tid] = []
            continue
        # prestige-first: the biggest races claim their riders before the small ones
        races = sorted(invites[tid], key=lambda r: (-r["popularity"], _daynum(r["day"], r["month"])))
        busy = {rid: [] for rid in roster_pool}
        spent = {rid: 0 for rid in roster_pool}
        plan = []
        for ra in races:
            start = _daynum(ra["day"], ra["month"])
            days = max(1, ra["stages"])
            end = start + days - 1
            lo, hi = career.class_limits.get(ra["klass"], (6, 7))
            prestige = ra["popularity"]
            # riders far above the race's level are penalised -> they skip small races
            level = 40 + prestige * 0.6
            scored = []
            for rid in roster_pool:
                if spent[rid] + days > day_budget:
                    continue
                if any(not (end < s - rest_days or start > e + rest_days) for s, e in busy[rid]):
                    continue
                abil = career.riders[rid]["ability"]
                fit = career.race_fit(rid, ra["id"])
                penalty = max(0.0, abil - level) * 1.8
                score = (fit * 1.4 + abil - penalty) * rng.jitter(variety)
                scored.append((score, fit, abil, rid))
            if len(scored) < lo:
                continue
            scored.sort(reverse=True)
            chosen = scored[:min(hi, len(scored))]
            roster = [c[3] for c in chosen]
            leader = max(chosen, key=lambda c: c[2] * 1.2 + c[1])[3]
            for rid in roster:
                busy[rid].append((start, end)); spent[rid] += days
            plan.append({"race": ra["id"], "name": ra["name"], "day": ra["day"],
                         "month": ra["month"], "roster": roster, "leader": leader})
        # present chronologically
        plan.sort(key=lambda e: _daynum(e["day"], e["month"]))
        result[tid] = plan
    return result


def apply(career: Career, generated):
    """Write generated rosters back into DYN_team_race (in place)."""
    tr = career.db["DYN_team_race"]
    teamcol, racecol = tr.column("fkIDteam"), tr.column("fkIDrace")
    roster_col = tr.column("gene_ilist_roster")
    index = {}
    for i in range(tr.nrow):
        index[(teamcol[i], racecol[i])] = i
    changed = 0
    for tid, plan in generated.items():
        for entry in plan:
            key = (tid, entry["race"])
            if key in index:
                roster_col[index[key]] = list(entry["roster"])
                changed += 1
    tr.set_column("gene_ilist_roster", roster_col)
    return changed
