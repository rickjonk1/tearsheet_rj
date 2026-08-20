"""
The real game database has columns we have never seen.

Every writer in this editor rebuilds a table. If it spells out the column list by
hand it will either drop the columns it does not know (KeyError), or append a 0
into them — and a 0 in a list column raises outright. Either way it corrupts
somebody's career.

These tests give the fixture the kind of columns a real save plausibly carries —
including a list column and a string column — and assert every write path still
works AND leaves those unknown columns untouched.
"""
import pytest

from pcmdb import cdb, calendar_gen
from pcmdb.model import Career
from conftest import reload_career, rider_id
import fixture

YEAR = 2030

# columns our code has never heard of, on every table it writes to
SURPRISES = {
    "DYN_cyclist_fitpeak_history": [
        ("value_i_peak_shape", cdb.DT_INT, 3),
        ("gene_sz_label", cdb.DT_STRING, "piek"),
    ],
    "DYN_cyclist_objective": [
        ("value_i_priority", cdb.DT_INT, 2),
        ("gene_ilist_shared", cdb.DT_INT_LIST, []),
    ],
    "DYN_training_stage_booking": [
        ("gene_ilist_participants", cdb.DT_INT_LIST, []),   # the likely real one
        ("value_i_cost", cdb.DT_INT, 5000),
    ],
    "DYN_training_stage_recon": [
        ("value_i_quality", cdb.DT_INT, 4),
    ],
}


@pytest.fixture
def rich_career(tmp_path):
    """A career whose tables carry columns this editor does not model."""
    return Career.load(fixture.write(tmp_path / "rich.cdb", extra_columns=SURPRISES))


def _col(car, table, name):
    return car.db[table].column(name)


def test_setting_peaks_survives_unknown_columns(rich_career, tmp_path):
    rich_career.set_peaks(1, [YEAR * 10000 + 704])
    back = reload_career(rich_career, tmp_path)
    t = back.db["DYN_cyclist_fitpeak_history"]
    assert "value_i_peak_shape" in t.colnames
    assert t.nrow >= 1


def test_peaks_keep_the_unknown_values_of_surviving_rows(rich_career, tmp_path):
    """A row we are not touching must come back byte-for-byte, extra columns included."""
    before = _col(rich_career, "DYN_cyclist_fitpeak_history", "gene_sz_label")
    rich_career.set_peaks(2, [YEAR * 10000 + 704])          # a different rider
    after = _col(reload_career(rich_career, tmp_path), "DYN_cyclist_fitpeak_history", "gene_sz_label")
    assert after[:len(before)] == before


def test_booking_a_camp_survives_a_list_column(rich_career, tmp_path):
    """A participants roster is the column most likely to exist on a real save —
    and the one that used to raise TypeError."""
    rich_career.book_camp(1, 1, YEAR * 10000 + 501, YEAR * 10000 + 518)
    back = reload_career(rich_career, tmp_path)
    t = back.db["DYN_training_stage_booking"]
    assert "gene_ilist_participants" in t.colnames
    assert len(back.team_camps(1)) == 1


def test_a_new_booking_blanks_the_list_column_rather_than_zeroing_it(rich_career):
    rich_career.book_camp(1, 1, YEAR * 10000 + 501, YEAR * 10000 + 518)
    parts = _col(rich_career, "DYN_training_stage_booking", "gene_ilist_participants")
    assert parts[-1] == [], "a list column must get an empty list, never 0"


def test_other_teams_bookings_keep_their_unknown_values(rich_career, tmp_path):
    """Team 2 has a camp in the fixture with cost 5000; booking for team 1 must
    not disturb it."""
    rich_career.book_camp(1, 1, YEAR * 10000 + 501, YEAR * 10000 + 518)
    back = reload_career(rich_career, tmp_path)
    t = back.db["DYN_training_stage_booking"]
    team, cost = t.column("fkIDteam"), t.column("value_i_cost")
    assert [cost[i] for i in range(t.nrow) if team[i] == 2] == [5000]


def test_recon_survives_unknown_columns(rich_career, tmp_path):
    rich_career.set_recon(1, 5, True)
    back = reload_career(rich_career, tmp_path)
    assert 5 in back.rider_recon_races(1)
    assert "value_i_quality" in back.db["DYN_training_stage_recon"].colnames


def test_toggling_an_objective_survives_unknown_columns(rich_career, tmp_path):
    added = rich_career.toggle_objective(1, 5)
    assert added
    back = reload_career(rich_career, tmp_path)
    assert 5 in back.rider_objectives(1)
    assert "value_i_priority" in back.db["DYN_cyclist_objective"].colnames


def test_toggling_twice_removes_it_again(rich_career, tmp_path):
    rich_career.toggle_objective(1, 5)
    rich_career.toggle_objective(1, 5)
    assert 5 not in reload_career(rich_career, tmp_path).rider_objectives(1)


def test_applying_a_season_survives_unknown_columns(rich_career, tmp_path):
    """The full path a user takes: plan a season and write it to a rich database."""
    climber = rider_id(rich_career, "Bergman")
    res = calendar_gen.build_from_captains(rich_career, 1, {climber: [5]},
                                           roles={"leaders": [climber]})
    calendar_gen.apply(rich_career, {1: res})
    back = reload_career(rich_career, tmp_path)
    assert climber in back.rider_objectives(climber) or back.rider_objectives(climber)
    assert "gene_ilist_shared" in back.db["DYN_cyclist_objective"].colnames


def test_untouched_riders_keep_their_objectives(rich_career, tmp_path):
    """The fixture gives rider 16 an objective. Planning team 1 must not wipe it."""
    assert rich_career.rider_objectives(16)
    climber = rider_id(rich_career, "Bergman")
    res = calendar_gen.build_from_captains(rich_career, 1, {climber: [5]},
                                           roles={"leaders": [climber]})
    calendar_gen.apply(rich_career, {1: res})
    assert reload_career(rich_career, tmp_path).rider_objectives(16)


def test_booking_state_is_looked_up_by_name_not_by_lowest_id(career):
    """Taking min(id) is a guess; if a real table starts at CANCELLED every camp
    we write lands in a dead state."""
    t = career.db["STA_training_stages_state"]
    ids, names = t.column("IDtraining_stage_state"), t.column("CONSTANT")
    booked = ids[names.index("BOOKED")]
    assert career.booking_state_booked() == booked


def test_booking_state_falls_back_when_there_is_no_name_match(rich_career):
    """Never crash on an unfamiliar state table — fall back to the lowest id."""
    t = rich_career.db["STA_training_stages_state"]
    t.set_column("CONSTANT", ["IETS", "ANDERS"])
    assert rich_career.booking_state_booked() == min(t.column("IDtraining_stage_state"))


def test_rewrite_rejects_a_column_that_does_not_exist(career):
    """A typo in a writer should fail loudly, not silently write nothing."""
    t = career.db["DYN_cyclist_objective"]
    with pytest.raises(KeyError):
        t.rewrite(add=[{"IDcyclist_objective": 999, "verzonnen_kolom": 1}])
