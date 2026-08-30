"""Schrijver voor Unreal PAK v11 (ongecomprimeerd, onversleuteld).

Gevalideerd tegen PCMAssets_3749668860_P.pak: het bestandsgedeelte, de encoded
entries, de directory-index en de footer komen byte-voor-byte overeen. Alleen de
path-hash-waarden verschillen — PCM Assets schrijft daar geen echte CityHash64 in
(hun tabel is niet eens op hash gesorteerd, wat UnrealPak wel doet). Wij schrijven
de echte hash, gesorteerd, dus strikt correcter dan de pak die al werkt.
"""
import struct, hashlib
from uecity import hash_path

MAGIC = 0x5A6F12E1
VERSION = 11
# guid16 + encrypted1 + magic4 + versie4 + idxoff8 + idxsize8 + sha20 + 5*32 methodes
FOOTER = 16 + 1 + 4 + 4 + 8 + 8 + 20 + 160


def _fstring(s):
    b = s.encode("utf-8") + b"\x00"
    return struct.pack("<I", len(b)) + b


def build(mount, files, seed=0):
    """mount: bv. '../../../pcm25_mod1/Plugins/Mod/'
    files: lijst van (pad_binnen_mount, bytes) — pad met forward slashes.
    Geeft de complete .pak terug als bytes."""
    body = bytearray()
    entries = []
    for _, data in files:
        off = len(body)
        rec = (struct.pack("<QQQI", 0, len(data), len(data), 0)
               + hashlib.sha1(data).digest()
               + b"\x00" + struct.pack("<I", 0))
        assert len(rec) == 53
        body += rec + data
        entries.append((off, len(data)))

    # --- encoded entries: 12 bytes per bestand ---
    # 0xE0000000 = offset/uncompressed/size passen alle drie in 32 bit,
    # geen compressie, niet versleuteld.
    enc = bytearray()
    for off, size in entries:
        enc += struct.pack("<III", 0xE0000000, off, size)

    # --- full directory index ---
    dirs = {}
    for path, _ in files:
        d, _, f = path.rpartition("/")
        dirs.setdefault(d + "/" if d else "/", []).append(f)
    for d in list(dirs):                       # ook alle tussenliggende mappen
        parts = [p for p in d.split("/") if p]
        for i in range(1, len(parts)):
            dirs.setdefault("/".join(parts[:i]) + "/", [])
    dirs.setdefault("/", [])

    idx_of = {p: i for i, (p, _) in enumerate(files)}
    fd = bytearray(struct.pack("<I", len(dirs)))
    for d in sorted(dirs):
        fd += _fstring(d) + struct.pack("<I", len(dirs[d]))
        for f in sorted(dirs[d]):
            full = f if d == "/" else d.lstrip("/") + f
            fd += _fstring(f) + struct.pack("<I", idx_of[full] * 12)

    # --- path hash index: op hash gesorteerd, zoals UnrealPak ---
    hashed = sorted((hash_path(p, seed), i * 12) for i, (p, _) in enumerate(files))
    ph = bytearray(struct.pack("<I", len(hashed)))
    for h, o in hashed:
        ph += struct.pack("<QI", h, o)
    ph += struct.pack("<I", 0)                 # geen gesnoeide entries

    # --- primary index ---
    m = mount.encode("utf-8") + b"\x00"
    idx = bytearray()
    idx += struct.pack("<I", len(m)) + m
    idx += struct.pack("<I", len(files))
    idx += struct.pack("<Q", seed)
    ph_at = len(idx) + 4                       # waar het ph-offset veld komt
    idx += struct.pack("<I", 1) + struct.pack("<QQ", 0, len(ph)) + hashlib.sha1(bytes(ph)).digest()
    fd_at = len(idx) + 4
    idx += struct.pack("<I", 1) + struct.pack("<QQ", 0, len(fd)) + hashlib.sha1(bytes(fd)).digest()
    idx += struct.pack("<I", len(enc)) + enc
    idx += struct.pack("<I", 0)                # aantal niet-encoded entries

    idx_off = len(body)
    struct.pack_into("<Q", idx, ph_at, idx_off + len(idx))
    struct.pack_into("<Q", idx, fd_at, idx_off + len(idx) + len(ph))

    footer = (b"\x00" * 16                      # encryption key guid
              + b"\x00"                         # index niet versleuteld
              + struct.pack("<II", MAGIC, VERSION)
              + struct.pack("<QQ", idx_off, len(idx))
              + hashlib.sha1(bytes(idx)).digest()
              + b"\x00" * 160)                  # 5 compressiemethode-namen, leeg
    assert len(footer) == FOOTER
    return bytes(body) + bytes(idx) + bytes(ph) + bytes(fd) + footer
