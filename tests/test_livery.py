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


FRAME_MIPS = [128, 256, 512, 1024, 2048, 4096]
FRAME_BYTES = 22364160          # de echte lengte van Frm_Cervel_TVL001_25_diff.ubulk


def test_the_frame_mip_chain_comes_out_of_the_real_bulk_size():
    """De .ubulk mag alleen vervangen worden door een even lange. Die lengte is de
    som van de vierkante BC3-mips, en daar valt de keten uit terug te rekenen."""
    assert ubulk.mip_chain(FRAME_BYTES, "PF_DXT5") == FRAME_MIPS
    assert sum(s * s for s in FRAME_MIPS) == FRAME_BYTES


@pytest.mark.parametrize("nbytes,fmt,sizes", [
    (22364160, "PF_DXT5", [128, 256, 512, 1024, 2048, 4096]),
    (11182080, "PF_DXT1", [128, 256, 512, 1024, 2048, 4096]),   # halve bytes per pixel
    (1398080, "PF_DXT5", [8, 16, 32, 64, 128, 256, 512, 1024]),
    (87360, "PF_DXT5", [8, 16, 32, 64, 128, 256]),
])
def test_mip_chains_are_inferred_not_hardcoded(nbytes, fmt, sizes):
    """Een wiel of helm is kleiner dan een frame en soms DXT1. Wie de keten
    hardcodeert op 4096/DXT5 schrijft daar een .ubulk van de verkeerde lengte."""
    assert ubulk.mip_chain(nbytes, fmt) == sizes


def test_a_length_that_fits_no_chain_is_refused():
    with pytest.raises(ValueError, match="geen mipketen"):
        ubulk.mip_chain(FRAME_BYTES + 1, "PF_DXT5")


def test_dxt1_and_dxt5_do_not_share_a_chain():
    """Het formaat uit de .uasset bepaalt de bytes per pixel; verwar je die, dan komt
    er een half of dubbel zo lange .ubulk uit."""
    assert ubulk.mip_chain(FRAME_BYTES, "PF_DXT5") == FRAME_MIPS
    with pytest.raises(ValueError):
        ubulk.mip_chain(FRAME_BYTES, "PF_DXT1")


def test_encode_refuses_a_top_mip_of_the_wrong_size():
    from PIL import Image
    small = Image.new("RGB", (2048, 2048))
    alpha = [Image.new("L", (s, s)) for s in FRAME_MIPS]
    with pytest.raises(ValueError, match="4096x4096"):
        ubulk.encode(small, alpha, "PF_DXT5")


def test_encoding_produces_the_exact_bulk_size():
    from PIL import Image
    top = Image.new("RGB", (4096, 4096), (10, 60, 200))
    alpha = [Image.new("L", (s, s), 0) for s in FRAME_MIPS]
    assert len(ubulk.encode(top, alpha, "PF_DXT5")) == FRAME_BYTES


def test_a_smaller_texture_encodes_to_its_own_size():
    """Dezelfde code moet een wiel aankunnen, niet alleen een frame."""
    from PIL import Image
    sizes = ubulk.mip_chain(87360, "PF_DXT5")
    top = Image.new("RGB", (sizes[-1], sizes[-1]), (200, 30, 10))
    alpha = [Image.new("L", (s, s), 255) for s in sizes]
    assert len(ubulk.encode(top, alpha, "PF_DXT5")) == 87360


# Uit een echte PCM-asset (Frm_Cervel_TVL001_25_diff.uasset): naam, zoals het
# spel hem opslaat, met de twee hashes die erachter staan.
NAMES = [
    ("None", 0x03F4, 0x0DC5),
    ("PF_DXT5", 0x8385, 0x51AE),
    ("/Mod/Equipment/Frame/Frm_Cervel_XXX001_25/Frm_Cervel_TVL001_25_diff", 0xAEE2, 0x8B1A),
    ("/Script/CoreUObject", 0x49F8, 0x3E2D),
    ("/Script/Engine", 0x4086, 0x4985),
    ("Class", 0x7774, 0x9178),
    ("Default__Texture2D", 0x684A, 0x9301),
    ("Frm_Cervel_TVL001_25_diff", 0x9D32, 0xA5CB),
    ("Package", 0x4773, 0x1588),
    ("Texture2D", 0xFDFE, 0xD140),
]


@pytest.mark.parametrize("name,h1,h2", NAMES)
def test_name_hashes_match_a_real_asset(name, h1, h2):
    import uename
    assert uename.hashes(name) == (h1, h2)


def test_the_two_hashes_are_not_the_same_function():
    """Ze verschillen in hoofdlettergevoeligheid; wie ze verwisselt, breekt de
    FName-lookup in het spel zonder dat er iets crasht."""
    import uename
    assert uename.strihash("Texture2D") == uename.strihash("TEXTURE2D")
    assert uename.strcrc32("Texture2D") != uename.strcrc32("TEXTURE2D")


def _fake_package(names):
    """Een minimale naamtabel zoals in een cooked .uasset."""
    import struct
    import uename
    out = bytearray()
    for n in names:
        b = n.encode() + b"\x00"
        out += struct.pack("<i", len(b)) + b + struct.pack("<HH", *uename.hashes(n))
    return bytes(out)


def test_rename_keeps_the_package_the_same_length():
    import uename
    data = _fake_package(["Frm_Cervel_TVL001_25_diff", "Texture2D"])
    out, n = uename.rename(data, "TVL", "VDK")
    assert n == 1
    assert len(out) == len(data)


def test_rename_recomputes_both_hashes():
    """De hashes horen bij de naam. Alleen de letters overschrijven laat ze fout
    achter, en dat is precies het soort fout dat pas in de game zichtbaar wordt."""
    import uename
    data = _fake_package(["Frm_Cervel_TVL001_25_diff"])
    out, _ = uename.rename(data, "TVL", "VDK")
    assert uename.verify(out) == []
    assert [n for _, n, _, _ in uename.name_table(out)] == ["Frm_Cervel_VDK001_25_diff"]


def test_rename_refuses_a_different_length():
    import uename
    data = _fake_package(["Frm_Cervel_TVL001_25_diff"])
    with pytest.raises(ValueError, match="even lang"):
        uename.rename(data, "TVL", "X-VOO")


def test_rename_refuses_a_name_that_is_not_there():
    import uename
    with pytest.raises(ValueError, match="komt in geen enkele naam voor"):
        uename.rename(_fake_package(["Texture2D"]), "TVL", "VDK")
