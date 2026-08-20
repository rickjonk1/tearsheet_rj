"""
Tests for the editor's write paths — the actions that rewrite someone's career.

Each asserts both the in-memory rule AND that the change survives save/load,
because a rule that is right in memory but lost on save is worse than useless.

These check the DATABASE-level contract (what we write, and that it round-trips).
Whether Pro Cycling Manager then acts on those values is a separate, in-game
question these tests deliberately do not claim to answer.
"""
import pytest

from conftest import reload_career
from pcmdb import calendar_gen

YEAR = 2030


def d(month, day):
    return YEAR * 10000 + month * 100 + day


# ---------- fitness peaks ----------

def test_peaks_are_capped_at_two(career, tmp_path):
    """PCM allows at most two fitness peaks per rider."""
    # five targets spread across the year, all far apart
    career.set_peaks(1, [d(7, 4), d(5, 8), d(4, 5), d(9, 1), d(3, 1)])
    assert len(_peaks(reload_career(career, tmp_path), 1)) == 2


def test_peaks_respect_the_ten_week_gap(career, tmp_path):
    """Two peaks must be >= 10 weeks (70 days) apart, so clustered targets
    collapse into one peak instead of producing an illegal pair."""
    # Ronde 5/4, Roubaix 12/4, Luik 26/4 — all within three weeks
    career.set_peaks(1, [d(4, 5), d(4, 12), d(4, 26)])
    peaks = _peaks(reload_career(career, tmp_path), 1)
    assert len(peaks) == 1


def test_peaks_are_ordered_by_priority_not_by_date(career, tmp_path):
    """The first target given wins; a later-but-clustered one is dropped."""
    # Tour (priority) then Giro 8/5 — 57 days earlier, inside the 70-day gap
    career.set_peaks(1, [d(7, 4), d(5, 8)])
    peaks = _peaks(reload_career(career, tmp_path), 1)
    assert [p["end"] for p in peaks] == [d(7, 4)]


def test_peak_window_opens_before_the_target(career, tmp_path):
    career.set_peaks(1, [d(7, 4)], lead_days=20)
    peak = _peaks(reload_career(career, tmp_path), 1)[0]
    assert peak["end"] == d(7, 4)
    assert peak["begin"] == d(6, 14)          # 20 days earlier


def test_setting_peaks_leaves_other_seasons_alone(career, tmp_path):
    """The fixture carries a peak from last season; rewriting this season's
    peaks must not delete a rider's history."""
    before = _all_peak_rows(career, 1)
    assert any(p["begin"] // 10000 == YEAR - 1 for p in before)

    career.set_peaks(1, [d(7, 4)])
    after = _all_peak_rows(reload_career(career, tmp_path), 1)
    assert any(p["begin"] // 10000 == YEAR - 1 for p in after), "past season was wiped"


def test_setting_peaks_does_not_touch_other_riders(career, tmp_path):
    career.set_peaks(1, [d(7, 4)])
    back = reload_career(career, tmp_path)
    assert _all_peak_rows(back, 2) == []


def _all_peak_rows(car, rider_id):
    t = car.db["DYN_cyclist_fitpeak_history"]
    cyc = t.column("fkIDcyclist")
    beg = t.column("value_i_date_begin")
    end = t.column("value_i_date_end_max")
    return [{"begin": beg[i], "end": end[i]}
            for i in range(t.nrow) if cyc[i] == rider_id]


def _peaks(car, rider_id):
    """This season's peaks only, in date order."""
    rows = [p for p in _all_peak_rows(car, rider_id) if p["begin"] // 10000 == YEAR]
    return sorted(rows, key=lambda p: p["end"])


# ---------- training camps ----------

def test_a_team_can_only_have_one_camp(career, tmp_path):
    """PCM: 'A training camp is already booked. You cannot book a second.'"""
    career.book_camp(1, 1, d(5, 1), d(5, 18))
    career.book_camp(1, 2, d(6, 1), d(6, 18))
    camps = reload_career(career, tmp_path).team_camps(1)
    assert len(camps) == 1
    assert camps[0]["stage"] == 2, "the newer booking should win"


def test_booking_a_camp_leaves_other_teams_untouched(career, tmp_path):
    """Team 2 starts with a camp in the fixture; team 1 booking must not clear it."""
    assert len(career.team_camps(2)) == 1
    career.book_camp(1, 1, d(5, 1), d(5, 18))
    back = reload_career(career, tmp_path)
    assert len(back.team_camps(2)) == 1
    assert len(back.team_camps(1)) == 1


def test_altitude_camp_lands_before_the_target_race(career, tmp_path):
    camp = career.plan_altitude(1, d(7, 4), days=18, lead=7)
    assert camp is not None
    assert camp["end"] == d(6, 27)            # 7 days before the target
    assert camp["start"] == d(6, 9)           # 18 days before that
    booked = reload_career(career, tmp_path).team_camps(1)
    assert booked[0]["start"] == camp["start"]


def test_altitude_camp_picks_an_altitude_venue(career):
    """Only type-9 venues are altitude camps; the flat one must never be chosen."""
    camp = career.plan_altitude(1, d(7, 4))
    altitude_places = {c["place"] for c in career.camps() if c["altitude"]}
    assert camp["place"] in altitude_places
    assert camp["place"] == "Teide", "should take the best-rated open venue"


# ---------- recons ----------

def test_recon_marks_every_stage_of_the_race(career, tmp_path):
    career.set_recon(1, 5, True)
    assert 5 in reload_career(career, tmp_path).rider_recon_races(1)


def test_recon_can_be_turned_off_again(career, tmp_path):
    career.set_recon(1, 5, True)
    career.set_recon(1, 5, False)
    assert 5 not in reload_career(career, tmp_path).rider_recon_races(1)


def test_recon_is_idempotent(career):
    """Toggling on twice must not double the rows."""
    career.set_recon(1, 5, True)
    n1 = career.db["DYN_training_stage_recon"].nrow
    career.set_recon(1, 5, True)
    assert career.db["DYN_training_stage_recon"].nrow == n1


def test_recon_off_leaves_other_riders_alone(career, tmp_path):
    """The fixture pre-loads a recon for rider 16; clearing rider 1 must keep it."""
    career.set_recon(1, 6, True)
    career.set_recon(1, 6, False)
    assert 6 in reload_career(career, tmp_path).rider_recon_races(16)


# ---------- bike balance ----------

def test_default_frames_are_unbalanced(career):
    """Baseline: the all-round frame dominates the climbing frame (same light
    rating, but poly also gets aero) — the imbalance the rebalance exists to fix."""
    f = {x["base"]: x for x in career.bike_frames()}
    assert f["poly"]["light"] == f["mountain"]["light"]
    assert f["poly"]["aero"] > f["mountain"]["aero"]


def test_rebalance_removes_the_dominance(career, tmp_path):
    career.rebalance_bikes()
    f = {x["base"]: x for x in reload_career(career, tmp_path).bike_frames()}
    # the climbing frame must now be strictly the best climber
    assert f["mountain"]["light"] > f["poly"]["light"]
    assert f["mountain"]["light"] > f["plain"]["light"]
    # and the aero frame strictly the best aero
    assert f["plain"]["aero"] > f["poly"]["aero"]
    assert f["plain"]["aero"] > f["mountain"]["aero"]


def test_rebalance_applies_to_every_version_of_an_archetype(career, tmp_path):
    """Each archetype exists 4x (poly, poly2, poly3, poly4); missing one would
    leave a stray dominant frame in the game."""
    career.rebalance_bikes()
    t = reload_career(career, tmp_path).db["STA_equipment_template"]
    const, light = t.column("CONSTANT"), t.column("gene_i_weight_light")
    poly = {light[i] for i in range(t.nrow) if const[i].startswith("poly")}
    assert poly == {2}, "all four poly versions should share the new value"


def test_set_frame_archetype_round_trips(career, tmp_path):
    career.set_frame_archetype("mountain", 1, 3, 2)
    f = {x["base"]: x for x in reload_career(career, tmp_path).bike_frames()}
    assert (f["mountain"]["aero"], f["mountain"]["light"], f["mountain"]["confort"]) == (1, 3, 2)


# ---------- planner: route fit ----------

def test_a_climber_is_never_offered_the_cobbled_classics(career):
    """The property the whole planner rests on: candidates are gated on profile."""
    names = {c["name"] for c in calendar_gen.candidates_for(career, 1, 1)}
    assert "Paris-Roubaix" not in names
    assert "Ronde van Vlaanderen" not in names
    assert "Tour de France" in names


def test_a_cobbler_is_offered_the_cobbled_classics(career):
    names = {c["name"] for c in calendar_gen.candidates_for(career, 1, 2)}
    assert {"Paris-Roubaix", "Ronde van Vlaanderen"} <= names
    assert "Tour de France" not in names


# ---------- planner: building and applying a season ----------

def test_captain_choices_become_objectives(career):
    res = calendar_gen.build_from_captains(career, 1, {1: [5]}, roles={"leaders": [1]})
    assert res["objectives"][1] == [5]
    assert any(p["race"] == 5 and 1 in p["roster"] for p in res["plan"])


def test_overlapping_races_are_not_double_booked(career):
    """The Giro (8/5, 21 stages) and the Tour (4/7) do not overlap, but asking
    for a rider to ride both plus a clashing race must not seat him twice."""
    res = calendar_gen.build_from_captains(career, 1, {1: [4, 5]}, roles={"leaders": [1]})
    days = []
    for p in res["plan"]:
        if 1 in p["roster"]:
            start = (p["month"] - 1) * 31 + p["day"]
            days.append((start, start + max(1, career.races[p["race"]]["stages"]) - 1))
    days.sort()
    for (s1, e1), (s2, _) in zip(days, days[1:]):
        assert s2 > e1, "rider seated in overlapping races"


def test_rosters_respect_the_class_size_limits(career):
    res = calendar_gen.build_from_captains(career, 1, {1: [5]}, roles={"leaders": [1]})
    for p in res["plan"]:
        lo, hi = career.class_limits[career.races[p["race"]]["klass"]]
        assert lo <= len(p["roster"]) <= hi


def test_apply_writes_rosters_into_the_database(career, tmp_path):
    res = calendar_gen.build_from_captains(career, 1, {1: [5]}, roles={"leaders": [1]})
    changed = calendar_gen.apply(career, {1: res})
    assert changed > 0

    back = reload_career(career, tmp_path)
    tr = back.db["DYN_team_race"]
    team, race, roster = tr.column("fkIDteam"), tr.column("fkIDrace"), tr.column("gene_ilist_roster")
    row = next(i for i in range(tr.nrow) if team[i] == 1 and race[i] == 5)
    assert 1 in roster[row], "the captain should be in the Tour roster"


def test_apply_only_touches_the_teams_you_planned(career, tmp_path):
    res = calendar_gen.build_from_captains(career, 1, {1: [5]}, roles={"leaders": [1]})
    calendar_gen.apply(career, {1: res})

    tr = reload_career(career, tmp_path).db["DYN_team_race"]
    team, roster = tr.column("fkIDteam"), tr.column("gene_ilist_roster")
    assert all(roster[i] == [] for i in range(tr.nrow) if team[i] == 2)


def test_generate_can_exclude_your_own_team(career):
    """The AI-peloton pass must not overwrite the team you just planned."""
    gen = calendar_gen.generate(career, seed=1, teams=[2])
    assert set(gen) == {2}


def test_generated_plan_is_deterministic_for_a_seed(career):
    a = calendar_gen.generate(career, seed=7, teams=[1])
    b = calendar_gen.generate(career, seed=7, teams=[1])
    assert [p["race"] for p in a[1]["plan"]] == [p["race"] for p in b[1]["plan"]]
