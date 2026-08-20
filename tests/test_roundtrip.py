"""
Round-trip & encoder-inverse tests against a REAL game save.

These assert the two invariants the whole editor rests on:
  1. parse -> serialise is byte-exact (the chunk engine loses nothing)
  2. decode -> encode is byte-exact for every column (edits touch only what you change)

Byte-exactness against a file Cyanide itself produced can only be proven with a
real save, so these stay opt-in. Point PCM_CDB at one:
    PCM_CDB=/path/to/Career.cdb python -m pytest tests/ -v

Without it they skip; the synthetic-fixture suites still cover the same code
paths (see test_cdb_synthetic.py and test_editor_actions.py).
"""
import os
import struct
import pytest

from pcmdb import cdb
from pcmdb.schema import Database, _decode_column

CDB = os.environ.get("PCM_CDB")
# guard on the FILE, not just the env var: a stale PCM_CDB pointing at a missing
# path used to raise FileNotFoundError in every test instead of skipping.
pytestmark = pytest.mark.skipif(
    not (CDB and os.path.isfile(CDB)),
    reason="set PCM_CDB to an existing career .cdb",
)


def _payload():
    data = open(CDB, "rb").read()
    import zlib
    return zlib.decompress(data[12:])


def test_chunk_roundtrip_byte_exact():
    payload = _payload()
    root = cdb.load_payload(payload)
    assert cdb.dump_payload(root) == payload


def test_column_encode_is_inverse_of_decode():
    payload = _payload()
    root = cdb.load_payload(payload)
    db = Database(root)
    # re-encode every column of a representative set from its own decoded values
    for tname in ["DYN_cyclist", "DYN_team_race", "STA_race", "STA_stage"]:
        t = db[tname]
        for c in t.cols:
            t.set_column(c.desc, _decode_column(c, t.nrow))
    assert cdb.dump_payload(root) == payload


def test_list_column_without_blob_chunk_can_be_written(tmp_path):
    """A list/string column with no data yet stores no COLUMN_BLOB chunk; writing
    data into it must create one (regression: pre-season saves with empty rosters)."""
    import struct
    root = cdb.load_payload(_payload())
    db = Database(root)
    tr = db["DYN_team_race"]
    col = next(c for c in tr.cols if c.desc == "gene_ilist_roster")
    col.find(cdb.COLUMN_VALUES).raw = struct.pack("<%dI" % tr.nrow, *([0] * tr.nrow))
    col.children = [ch for ch in col.children if ch.type != cdb.COLUMN_BLOB]
    assert col.find(cdb.COLUMN_BLOB) is None

    tr.set_column("gene_ilist_roster", [[101, 202, 303]] + [[]] * (tr.nrow - 1))
    out = tmp_path / "t.cdb"
    cdb.save(str(out), root)
    got = Database(cdb.load(str(out))[0])["DYN_team_race"].column("gene_ilist_roster")
    assert got[0] == [101, 202, 303] and got[1] == []


def test_edit_persists_through_save_load(tmp_path):
    root = cdb.load_payload(_payload())
    db = Database(root)
    tr = db["DYN_team_race"]
    roster = tr.column("gene_ilist_roster")
    # a pre-season save has no rosters yet — that case is covered synthetically
    target = next((i for i in range(tr.nrow) if len(roster[i]) >= 3), None)
    if target is None:
        pytest.skip("save has no filled rosters (pre-season)")
    new = list(roster[target]); new[0] = 91234
    roster[target] = new
    tr.set_column("gene_ilist_roster", roster)

    out = tmp_path / "edited.cdb"
    cdb.save(str(out), root)

    root2, _ = cdb.load(str(out))
    got = Database(root2)["DYN_team_race"].column("gene_ilist_roster")[target]
    assert got == new
