"""FName-hashes in een cooked Unreal package, en het hernoemen van een asset.

Elke naam in de naamtabel van een .uasset staat er als:

    int32 lengte | de bytes incl. \\0 | uint16 NonCasePreservingHash | uint16 CasePreservingHash

Die twee hashes zijn afgeleid uit de naam zelf, dus je kunt een asset niet hernoemen
door alleen de letters te overschrijven — dan wijst de FName-lookup in het spel naar
de verkeerde bucket. Beide zijn hier teruggerekend uit een echte PCM-asset en op alle
tien namen daarin geverifieerd:

    CasePreservingHash    = FCrc::StrCrc32(naam)          low 16
    NonCasePreservingHash = FCrc::Strihash_DEPRECATED(naam) low 16

StrCrc32 draait over de tekens als UTF-32LE (Unreal verwerkt vier bytes per teken,
ook bij een 16-bits TCHAR). Strihash_DEPRECATED gaat over de HOOFDLETTER-vorm, één
byte per teken, met de oude CRC-tabel uit poly 0x04C11DB7 en zonder in- of
uitcomplement.
"""
import struct
import zlib

_M = 0xFFFFFFFF


def _deprecated_table():
    t = []
    for i in range(256):
        c = i << 24
        for _ in range(8):
            c = ((c << 1) ^ (0x04C11DB7 if c & 0x80000000 else 0)) & _M
        t.append(c)
    return t


_TABLE = _deprecated_table()


def strcrc32(name):
    """FCrc::StrCrc32 — CRC32 over de tekens als UTF-32LE."""
    return zlib.crc32(name.encode("utf-32-le")) & _M


def strihash(name):
    """FCrc::Strihash_DEPRECATED — hoofdletters, één byte per teken, oude tabel."""
    h = 0
    for ch in name.upper():
        h = ((h >> 8) & 0x00FFFFFF) ^ _TABLE[(h ^ (ord(ch) & 0xFF)) & 0xFF]
    return h & _M


def hashes(name):
    """(NonCasePreservingHash, CasePreservingHash) zoals ze in het bestand staan."""
    return strihash(name) & 0xFFFF, strcrc32(name) & 0xFFFF


def name_table(data, start=None):
    """Loop de naamtabel af. Geeft (offset, naam, h1, h2) per entry."""
    def walk(o):
        out = []
        while o + 4 <= len(data):
            n = struct.unpack_from("<i", data, o)[0]
            if not 1 <= n <= 1024:
                break
            s = data[o + 4:o + 4 + n]
            if len(s) < n or s[-1] != 0 or not all(32 <= c < 127 for c in s[:-1]):
                break
            if o + 4 + n + 4 > len(data):
                break
            h1, h2 = struct.unpack_from("<HH", data, o + 4 + n)
            out.append((o, s[:-1].decode(), h1, h2))
            o += 4 + n + 4
        return out

    if start is not None:
        return walk(start)
    return max((walk(o) for o in range(min(len(data), 4096))), key=len)


def verify(data):
    """Klopt onze hashberekening met wat er in dit pakket staat?"""
    bad = [(n, h1, h2) for _, n, h1, h2 in name_table(data) if hashes(n) != (h1, h2)]
    return bad


def rename(data, old, new):
    """Vervang `old` door `new` in elke naam van de tabel en herbereken de hashes.

    De vervanging moet even lang zijn, anders verschuift alles in het pakket: elke
    offset in de summary (import-, export- en exporttabel) zou dan opnieuw berekend
    moeten worden. Met TVL -> VDK of TVL -> XXX blijft alles op zijn plek staan.
    """
    if len(old) != len(new):
        raise ValueError("%r en %r moeten even lang zijn" % (old, new))
    out = bytearray(data)
    changed = 0
    for off, name, _, _ in name_table(data):
        if old not in name:
            continue
        fresh = name.replace(old, new)
        out[off + 4:off + 4 + len(fresh)] = fresh.encode()
        struct.pack_into("<HH", out, off + 4 + len(name) + 1, *hashes(fresh))
        changed += 1
    if not changed:
        raise ValueError("%r komt in geen enkele naam voor" % old)
    return bytes(out), changed
