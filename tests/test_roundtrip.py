"""
Round-trip & encoder-inverse tests.

These require a real career .cdb. Point the env var PCM_CDB at one:
    PCM_CDB=/path/to/Career.cdb python -m pytest tests/ -v

The tests assert the two invariants the whole editor rests on:
  1. parse -> serialise is byte-exact (the chunk engine loses nothing)
  2. decode -> encode is byte-exact for every column (edits touch only what you change)
"""
import os
import struct
import pytest

from pcmdb import cdb
from pcmdb.schema import Database, _decode_column

CDB = os.environ.get("PCM_CDB")
pytestmark = pytest.mark.skipif(not CDB, reason="set PCM_CDB to a career .cdb")


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


def test_edit_persists_through_save_load(tmp_path):
    root = cdb.load_payload(_payload())
    db = Database(root)
    tr = db["DYN_team_race"]
    roster = tr.column("gene_ilist_roster")
    target = next(i for i in range(tr.nrow) if len(roster[i]) >= 3)
    new = list(roster[target]); new[0] = 91234
    roster[target] = new
    tr.set_column("gene_ilist_roster", roster)

    out = tmp_path / "edited.cdb"
    cdb.save(str(out), root)

    root2, _ = cdb.load(str(out))
    got = Database(root2)["DYN_team_race"].column("gene_ilist_roster")[target]
    assert got == new
