"""
Balance tests: a season must be spread sensibly across the year, and a squad
must match the route rather than stacking one specialty.
"""
import pytest

from conftest import race_id, rider_id
from pcmdb import calendar_gen as cg


# ---------- year balance: race density ----------

def _giro_span(career):
    r = career.races[4]                       # Giro d'Italia, 21 stages
    s = cg._daynum(r["day"], r["month"])
    return s, s + max(1, r["stages"]) - 1


def test_rest_days_alone_do_not_prevent_stacking(career):
    """Baseline for the rule below: spacing neighbouring races by a couple of rest
    days still lets a rider start a week-long tour right after a grand tour."""
    s, e = _giro_span(career)
    assert not cg._overlaps([(s, e)], e + 3, e + 9, 2)


def test_a_stage_race_cannot_follow_a_grand_tour(career):
    s, e = _giro_span(career)
    assert cg._window_overload([(s, e)], e + 3, e + 9, 30, 23)


def test_the_same_race_is_fine_once_the_rider_has_recovered(career):
    """The cap must spread the season, not forbid racing later in the year."""
    s, e = _giro_span(career)
    assert not cg._window_overload([(s, e)], e + 40, e + 46, 30, 23)


def test_a_grand_tour_on_its_own_is_always_allowed(career):
    s, e = _giro_span(career)
    assert not cg._window_overload([], s, e, 30, 23)


def test_window_cap_of_zero_disables_the_rule(career):
    s, e = _giro_span(career)
    assert not cg._window_overload([(s, e)], e + 1, e + 9, 30, 0)


def test_no_rider_is_overloaded_in_a_generated_season(career):
    """End-to-end: nobody should exceed the rolling cap anywhere in the year."""
    gen = cg.generate(career, seed=3, teams=[1])
    spans = {}
    for p in gen[1]["plan"]:
        start = cg._daynum(p["day"], p["month"])
        end = start + max(1, career.races[p["race"]]["stages"]) - 1
        for rid in p["roster"]:
            spans.setdefault(rid, []).append((start, end))
    for rid, busy in spans.items():
        days = set()
        for s, e in busy:
            days.update(range(s, e + 1))
        if not days:
            continue
        for w0 in range(min(days), max(days) + 1):
            load = sum(1 for d in days if w0 <= d < w0 + 30)
            assert load <= 23, "rider %d races %d days in a 30-day window" % (rid, load)


def test_a_rider_is_never_in_two_races_at_once(career):
    gen = cg.generate(career, seed=5, teams=[1])
    spans = {}
    for p in gen[1]["plan"]:
        start = cg._daynum(p["day"], p["month"])
        end = start + max(1, career.races[p["race"]]["stages"]) - 1
        for rid in p["roster"]:
            spans.setdefault(rid, []).append((start, end))
    for rid, busy in spans.items():
        busy.sort()
        for (_, e1), (s2, _) in zip(busy, busy[1:]):
            assert s2 > e1, "rider %d double-booked" % rid


# ---------- team balance: squad matches the route ----------

def test_slot_profile_splits_over_the_race_demands(career):
    """A grand tour asks for climbing above all, but not only climbing."""
    slots = cg._slot_profile(career, career.races[5], 7)
    assert len(slots) == 7
    assert slots.count("charac_i_mountain") >= 2, "climbing is the main demand"
    assert len(set(slots)) >= 4, "a grand tour needs several different profiles"


def test_slot_profile_leads_with_the_strongest_demand(career):
    slots = cg._slot_profile(career, career.races[5], 7)
    assert slots[0] == "charac_i_mountain"


def test_a_cobbled_race_asks_for_cobble_riders(career):
    slots = cg._slot_profile(career, career.races[2], 6)   # Paris-Roubaix
    assert slots[0] == "charac_i_cobble"
    assert "charac_i_mountain" not in slots, "no climbing demand on the cobbles"


def test_slot_profile_matches_the_number_of_slots(career):
    for n in range(0, 9):
        assert len(cg._slot_profile(career, career.races[5], n)) == n


def test_grand_tour_squad_is_not_all_climbers(career, climber):
    """The point of the whole exercise: no eight-climber Tour squad."""
    res = cg.build_from_captains(career, 1, {climber: [5]}, roles={"leaders": [climber]})
    roster = next(p["roster"] for p in res["plan"] if p["race"] == 5)
    specialties = [career.riders[r]["specialty"] for r in roster]
    assert len(set(specialties)) >= 3, "squad should cover several profiles, got %r" % specialties


def test_grand_tour_squad_includes_a_sprinter(career, climber):
    """The route has flat days, so the squad needs someone for them."""
    res = cg.build_from_captains(career, 1, {climber: [5]}, roles={"leaders": [climber]})
    roster = next(p["roster"] for p in res["plan"] if p["race"] == 5)
    best_sprint = max(career.riders[r]["charac"]["charac_i_sprint"] for r in roster)
    assert best_sprint >= 80, "no sprinter taken to a race with flat stages"


def test_cobbled_squad_is_built_around_cobble_riders(career, cobbler):
    res = cg.build_from_captains(career, 1, {cobbler: [2]}, roles={"leaders": [cobbler]})
    roster = next(p["roster"] for p in res["plan"] if p["race"] == 2)
    best_cobble = max(career.riders[r]["charac"]["charac_i_cobble"] for r in roster)
    assert best_cobble >= 80


def test_rosters_still_respect_class_limits_with_profile_slots(career, climber):
    res = cg.build_from_captains(career, 1, {climber: [5]}, roles={"leaders": [climber]})
    for p in res["plan"]:
        lo, hi = career.class_limits[career.races[p["race"]]["klass"]]
        assert lo <= len(p["roster"]) <= hi


def test_no_rider_appears_twice_in_one_roster(career, climber, cobbler):
    res = cg.build_from_captains(career, 1, {climber: [5], cobbler: [2]},
                                 roles={"leaders": [climber, cobbler]})
    for p in res["plan"]:
        assert len(p["roster"]) == len(set(p["roster"]))
