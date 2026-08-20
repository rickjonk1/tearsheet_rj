"""
Chunk-engine and column-codec tests that run everywhere — no game save needed.

These cover the layer everything else sits on: if the reader/writer or the
column encoders are wrong, every edit silently corrupts someone's career.
"""
import struct

import pytest

from pcmdb import cdb
from pcmdb.schema import Database, _decode_column, _encode_column


def test_parse_then_serialise_is_byte_exact(career_path):
    payload = _payload(career_path)
    assert cdb.dump_payload(cdb.load_payload(payload)) == payload


def _payload(path):
    import zlib
    return zlib.decompress(open(path, "rb").read()[12:])


def test_reencoding_every_column_changes_nothing(career_path):
    """Decode each column and write it straight back: the file must not move."""
    payload = _payload(career_path)
    root = cdb.load_payload(payload)
    db = Database(root)
    for tname, table in db.tables.items():
        for c in table.cols:
            table.set_column(c.desc, _decode_column(c, table.nrow))
    assert cdb.dump_payload(root) == payload


def test_saved_file_reloads_identically(career_path, tmp_path):
    root, _ = cdb.load(career_path)
    out = tmp_path / "again.cdb"
    cdb.save(str(out), root)
    assert _payload(out) == _payload(career_path)


@pytest.mark.parametrize("dtype,values", [
    (cdb.DT_INT, [0, 1, -7, 2 ** 30]),
    (cdb.DT_FLOAT, [0.0, 1.5, -2.25]),
    (cdb.DT_BYTE, [0, 1, -128, 127]),
    (cdb.DT_SHORT, [0, 1, 65535]),
    (cdb.DT_BOOL, [True, False, True, True, False, False, True, False, True]),
    (cdb.DT_STRING, ["", "Bergman", "Ronde van Vlaanderen", "accentué"]),
    (cdb.DT_INT_LIST, [[], [1], [1, 2, 3], [-4, 5]]),
    (cdb.DT_FLOAT_LIST, [[], [1.5], [0.25, -0.5]]),
])
def test_encode_decode_is_lossless(dtype, values):
    """Every supported column type must survive encode -> decode unchanged."""
    vbytes, bbytes = _encode_column(dtype, values)
    col = cdb.Chunk(cdb.COLUMN, desc="probe")
    col.children = [
        _raw(cdb.COLUMN_DATA_TYPE, struct.pack("<I", dtype)),
        _raw(cdb.COLUMN_VALUES, vbytes),
    ]
    if bbytes is not None:
        col.children.append(_raw(cdb.COLUMN_BLOB, bbytes))
    got = _decode_column(col, len(values))
    if dtype == cdb.DT_FLOAT:
        assert got == pytest.approx(values)
    elif dtype == cdb.DT_FLOAT_LIST:
        assert [list(map(float, g)) for g in got] == [list(map(float, v)) for v in values]
    else:
        assert got == values


def _raw(type_, raw):
    ch = cdb.Chunk(type_)
    ch.raw = raw
    return ch


def test_writing_a_list_column_that_had_no_blob_chunk(career_path, tmp_path):
    """A list column with no data yet stores no COLUMN_BLOB chunk; writing data
    must create one. Regression: pre-season saves have empty rosters."""
    root, _ = cdb.load(career_path)
    db = Database(root)
    tr = db["DYN_team_race"]
    col = next(c for c in tr.cols if c.desc == "gene_ilist_roster")
    col.children = [ch for ch in col.children if ch.type != cdb.COLUMN_BLOB]
    col.find(cdb.COLUMN_VALUES).raw = struct.pack("<%dI" % tr.nrow, *([0] * tr.nrow))
    assert col.find(cdb.COLUMN_BLOB) is None

    tr.set_column("gene_ilist_roster", [[101, 202, 303]] + [[]] * (tr.nrow - 1))
    out = tmp_path / "roster.cdb"
    cdb.save(str(out), root)

    got = Database(cdb.load(str(out))[0])["DYN_team_race"].column("gene_ilist_roster")
    assert got[0] == [101, 202, 303]
    assert got[1] == []


def test_edit_persists_through_save_load(career_path, tmp_path):
    root, _ = cdb.load(career_path)
    db = Database(root)
    tr = db["DYN_team_race"]
    roster = tr.column("gene_ilist_roster")
    roster[0] = [11, 22, 33]
    tr.set_column("gene_ilist_roster", roster)

    out = tmp_path / "edited.cdb"
    cdb.save(str(out), root)
    assert Database(cdb.load(str(out))[0])["DYN_team_race"].column("gene_ilist_roster")[0] == [11, 22, 33]


def test_replacing_a_table_body_updates_row_count(career_path, tmp_path):
    """set_data rewrites a whole table — the row count must follow, or every
    later read of that table is misaligned."""
    root, _ = cdb.load(career_path)
    db = Database(root)
    t = db["DYN_cyclist_objective"]
    t.set_data({"IDcyclist_objective": [1, 2, 3],
                "fkIDcyclist": [4, 5, 6],
                "fkIDrace": [1, 2, 3]})
    out = tmp_path / "grown.cdb"
    cdb.save(str(out), root)

    back = Database(cdb.load(str(out))[0])["DYN_cyclist_objective"]
    assert back.nrow == 3
    assert back.column("fkIDcyclist") == [4, 5, 6]


def test_set_column_rejects_wrong_length(career_path):
    db = Database.load(career_path)
    t = db["DYN_team"]
    with pytest.raises(ValueError):
        t.set_column("IDteam", [1, 2, 3, 4, 5])
