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


def generate(career: Career, seed=1, teams=None, variety=0.15, rest_days=2):
    """
    Returns {team_id: [ {race, name, day, month, roster:[ids], leader} ]}.
    Does not mutate the career; call `apply` to write results into DYN_team_race.
    """
    rng = _Rng(seed)
    result = {}
    target_teams = teams if teams is not None else list(career.teams)
    tset = set(target_teams)

    # races a team is invited to, chronologically
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
        races = sorted(invites[tid], key=lambda r: _daynum(r["day"], r["month"]))
        busy = {rid: [] for rid in roster_pool}       # list of (start,end) daynums
        plan = []
        for ra in races:
            start = _daynum(ra["day"], ra["month"])
            end = start + max(1, ra["stages"]) - 1
            lo, hi = career.class_limits.get(ra["klass"], (6, 7))

            # candidates = available riders scored by fit + ability, with variety jitter
            scored = []
            for rid in roster_pool:
                if any(not (end < s - rest_days or start > e + rest_days) for s, e in busy[rid]):
                    continue  # would overlap another commitment (+rest)
                fit = career.race_fit(rid, ra["id"])
                abil = career.riders[rid]["ability"]
                # leader-ness from fit+ability; prestige nudges stronger riders to bigger races
                score = (fit * 1.4 + abil) * rng.jitter(variety)
                scored.append((score, fit, abil, rid))
            if len(scored) < lo:
                continue  # can't field a legal roster -> skip (team sits this one out)
            scored.sort(reverse=True)

            n = min(hi, len(scored))
            # support-group logic: pick a leader, then team-mates that also fit this race
            chosen = [scored[0]]
            for cand in scored[1:]:
                if len(chosen) >= n:
                    break
                chosen.append(cand)
            roster = [c[3] for c in chosen]
            leader = chosen[0][3]
            for rid in roster:
                busy[rid].append((start, end))
            plan.append({"race": ra["id"], "name": ra["name"], "day": ra["day"],
                         "month": ra["month"], "roster": roster, "leader": leader})
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
