"""The livery mod pipeline writes a binary the game must parse.

A .pak is not forgiving: one wrong offset, one stale SHA1, one byte of padding and
the game silently ignores the mod. These tests pin the two things that make a pak
readable at all — the hash Unreal looks paths up by, and the round trip through our
own writer and reader — plus the size arithmetic the .ubulk swap depends on.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "livery"))

import pakbuild
import pakread
import uecity
import ubulk

MOUNT = "../../../pcm25_mod1/Plugins/Mod/"

# Taken from the reference CityHash implementation (pip install cityhash).
# Unreal hashes the lowercased path as UTF-16LE, so a real path is 84 bytes and
# exercises the 64-byte main loop, not just the short-string branches.
VECTORS = [
    (b"", 0x9AE16A3B2F90404F, 0x0000000000000000),
    (b"abc", 0x24A5B3A074E7F369, 0x56848711F2055DB1),
    (b"x" * 64, 0xE6A56470446947D1, 0xD851C8B872793CC2),
    (b"y" * 65, 0x397DB415760CF983, 0x02E1C8FD153978D1),
    (b"z" * 200, 0x47FE0D06CBD4F33E, 0x5A0463FEF3C4BD5D),
]


@pytest.mark.parametrize("data,plain,seeded", VECTORS)
def test_cityhash_matches_the_reference(data, plain, seeded):
    assert uecity.cityhash64(data) == plain
    assert uecity.cityhash64_with_seed(data, 0) == seeded


def test_hash_path_is_case_insensitive():
    """FPakFile::HashPath lowercases first — a pak built from mixed-case paths must
    still be found by a lowercase lookup."""
    a = uecity.hash_path("Content/Equipment/Frame/Frm_Cervel_TVL001_25_diff.uasset")
    b = uecity.hash_path("content/equipment/frame/frm_cervel_tvl001_25_diff.uasset")
    assert a == b


def test_hash_path_hashes_utf16_not_utf8():
    """Unreal hashes TCHARs. Hashing the UTF-8 bytes instead gives a pak whose
    lookups all miss, which is exactly the bug that is invisible until in-game."""
    p = "Content/Equipment/Frame/x.uasset"
    assert uecity.hash_path(p) == uecity.cityhash64_with_seed(p.lower().encode("utf-16-le"), 0)
    assert uecity.hash_path(p) != uecity.cityhash64_with_seed(p.lower().encode("utf-8"), 0)


@pytest.fixture
def sample():
    return [("Content/Equipment/Frame/a.uasset", b"AAAA" * 7),
            ("Content/Equipment/Frame/a.uexp", b"B" * 300),
            ("Content/Equipment/Frame/a.ubulk", b"C" * 65536),
            ("Content/Jersey/Team/tvl/j.uasset", b"D" * 11)]


def test_a_built_pak_reads_back(tmp_path, sample):
    p = tmp_path / "t.pak"
    p.write_bytes(pakbuild.build(MOUNT, sample))
    got = pakread.read(str(p))                      # asserts every SHA1 internally
    assert got["ver"] == 11
    assert got["mount"] == MOUNT
    assert got["nfile"] == len(sample)


def test_every_file_comes_back_byte_for_byte(tmp_path, sample):
    import struct
    p = tmp_path / "t.pak"
    p.write_bytes(pakbuild.build(MOUNT, sample))
    got = pakread.read(str(p))
    paths = {}
    for d, ents in got["tree"].items():
        for fn, off in ents.items():
            paths[off] = (d if d != "/" else "") + fn
    for i, (path, data) in enumerate(sample):
        assert paths[i * 12] == path
        _, off, size = struct.unpack_from("<III", got["enc"], i * 12)
        assert got["raw"][off + 53:off + 53 + size] == data


def test_intermediate_directories_are_all_listed(tmp_path, sample):
    """Unreal walks the directory index; a missing parent hides everything under it."""
    p = tmp_path / "t.pak"
    p.write_bytes(pakbuild.build(MOUNT, sample))
    tree = pakread.read(str(p))["tree"]
    for d in ("/", "Content/", "Content/Equipment/", "Content/Equipment/Frame/",
              "Content/Jersey/", "Content/Jersey/Team/", "Content/Jersey/Team/tvl/"):
        assert d in tree, d


def test_path_hash_index_is_sorted(tmp_path, sample):
    """Unreal binary-searches it. Unsorted entries are not found."""
    p = tmp_path / "t.pak"
    p.write_bytes(pakbuild.build(MOUNT, sample))
    hashes = [h for h, _ in pakread.read(str(p))["hashes"]]
    assert hashes == sorted(hashes)


def test_path_hash_index_points_at_the_right_file(tmp_path, sample):
    p = tmp_path / "t.pak"
    p.write_bytes(pakbuild.build(MOUNT, sample))
    got = pakread.read(str(p))
    by_hash = dict(got["hashes"])
    for i, (path, _) in enumerate(sample):
        assert by_hash[uecity.hash_path(path, got["seed"])] == i * 12


def test_the_mip_chain_is_exactly_the_bulk_size():
    """The .ubulk may only be swapped for one of identical length, and that length
    is the sum of six square BC3 mips at one byte per pixel."""
    assert ubulk.SIZES == [128, 256, 512, 1024, 2048, 4096]
    assert ubulk.TOTAL == 22364160
    assert sum(s * s for s in ubulk.SIZES) == ubulk.TOTAL


def test_encode_refuses_a_top_mip_that_is_not_4096(tmp_path):
    from PIL import Image
    small = Image.new("RGB", (2048, 2048))
    alpha = [Image.new("L", (s, s)) for s in ubulk.SIZES]
    with pytest.raises(ValueError, match="4096"):
        ubulk.encode(small, alpha)


def test_encoding_produces_the_exact_bulk_size(tmp_path):
    from PIL import Image
    top = Image.new("RGB", (4096, 4096), (10, 60, 200))
    alpha = [Image.new("L", (s, s), 0) for s in ubulk.SIZES]
    assert len(ubulk.encode(top, alpha)) == ubulk.TOTAL
