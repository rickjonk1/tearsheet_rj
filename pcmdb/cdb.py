"""
cdb.py — Reader/writer for Cyanide .cdb databases (Pro Cycling Manager).

File layout:
  [0:4]   0xFFFFFFFF magic
  [4:8]   uncompressed size (uint32 LE)
  [8:12]  compressed size (uint32 LE)
  [12:]   zlib stream

Decompressed payload is a tree of chunks:
  AA AA AA AA | size(u32) | type(u32) | flags(u32) | descPresent(u32)
    [ if descPresent: strLen(u32 incl NUL) | bytes | pad->4 ]
  BB BB BB BB                         (metadata -> body separator)
  <body>                              (child chunks, and/or DD..EE arrays, or raw leaf bytes)
  CC CC CC CC                         (chunk end)
  size = bytes from the leading AA up to & including the trailing CC.

Arrays inside a body:  DD DD DD DD | count(u32) | <count child chunks> | EE EE EE EE
"""
import struct, zlib

AA = 0xAAAAAAAA  # chunk begin
BB = 0xBBBBBBBB  # meta->body separator
CC = 0xCCCCCCCC  # chunk end
DD = 0xDDDDDDDD  # array begin
EE = 0xEEEEEEEE  # array end

# chunk type ids
WRAPPER, DATABASE_TABLES, DATABASE_FLAGS = 0x00, 0x01, 0x02
TABLE, ROW_COUNT, COLUMN_DEFINITIONS, TABLE_ID, TABLE_FLAGS = 0x10, 0x11, 0x12, 0x15, 0x16
COLUMN, COLUMN_DATA_TYPE, COLUMN_VALUES, COLUMN_BLOB, COLUMN_INDEX = 0x20, 0x21, 0x22, 0x23, 0x24

# data type ids
DT_INT, DT_FLOAT, DT_STRING, DT_BOOL, DT_BYTE, DT_SHORT = 0, 1, 2, 3, 4, 5
DT_FLOAT_LIST, DT_INT_LIST = 10, 11


class Chunk:
    __slots__ = ("type", "flags", "desc", "children", "raw", "is_array", "array_count")

    def __init__(self, type_, flags=0, desc=None):
        self.type = type_
        self.flags = flags
        self.desc = desc            # str or None
        self.children = None        # list[Chunk] for containers
        self.raw = None             # bytes for leaves
        self.is_array = False       # body is a DD..EE array of children
        self.array_count = 0

    def find(self, type_):
        for c in (self.children or ()):
            if c.type == type_:
                return c
        return None

    def find_all(self, type_):
        return [c for c in (self.children or ()) if c.type == type_]


class _R:
    def __init__(self, b):
        self.b = b; self.o = 0
    def u32(self):
        v = struct.unpack_from("<I", self.b, self.o)[0]; self.o += 4; return v
    def peek(self):
        return struct.unpack_from("<I", self.b, self.o)[0]
    def take(self, n):
        s = self.b[self.o:self.o + n]; self.o += n; return s


def _pad4(n):
    return (4 - (n & 3)) & 3


def _read_chunk(r):
    start = r.o
    assert r.u32() == AA, f"expected AA at {start:#x}"
    size = r.u32()
    ctype = r.u32()
    flags = r.u32()
    desc_present = r.u32()
    ch = Chunk(ctype, flags)
    if desc_present:
        slen = r.u32()
        raw = r.take(slen)
        r.take(_pad4(slen))
        ch.desc = raw.rstrip(b"\x00").decode("utf-8", "surrogateescape")
    assert r.u32() == BB, f"expected BB in chunk @{start:#x}"
    body_end = start + size - 4  # trailing CC excluded
    # decide: array / children / raw leaf
    nxt = r.peek() if r.o < body_end else CC
    if nxt == DD:
        r.u32()  # DD
        ch.is_array = True
        ch.array_count = r.u32()
        ch.children = []
        while r.peek() != EE:
            ch.children.append(_read_chunk(r))
        assert r.u32() == EE
    elif nxt == AA:
        ch.children = []
        while r.o < body_end and r.peek() == AA:
            ch.children.append(_read_chunk(r))
    else:
        ch.raw = r.take(body_end - r.o)
    assert r.o == body_end, f"body misalign in chunk @{start:#x} ({r.o:#x} != {body_end:#x})"
    assert r.u32() == CC, f"expected CC ending chunk @{start:#x}"
    return ch


class _W:
    def __init__(self):
        self.buf = bytearray()
    def u32(self, v):
        self.buf += struct.pack("<I", v & 0xFFFFFFFF)
    def raw(self, b):
        self.buf += b


def _write_chunk(w, ch):
    start = len(w.buf)
    w.u32(AA)
    w.u32(0)  # size placeholder
    w.u32(ch.type)
    w.u32(ch.flags)
    if ch.desc is not None:
        w.u32(1)
        s = ch.desc.encode("utf-8", "surrogateescape") + b"\x00"
        w.u32(len(s))
        w.raw(s)
        w.raw(b"\x00" * _pad4(len(s)))
    else:
        w.u32(0)
    w.u32(BB)
    if ch.is_array:
        w.u32(DD)
        w.u32(ch.array_count)
        for c in ch.children:
            _write_chunk(w, c)
        w.u32(EE)
    elif ch.children is not None:
        for c in ch.children:
            _write_chunk(w, c)
    else:
        w.raw(ch.raw)
    w.u32(CC)
    size = len(w.buf) - start
    struct.pack_into("<I", w.buf, start + 4, size)


# ---- public API ----

def load(path):
    data = open(path, "rb").read()
    assert struct.unpack_from("<I", data, 0)[0] == 0xFFFFFFFF, "bad cdb magic"
    payload = zlib.decompress(data[12:])
    r = _R(payload)
    root = _read_chunk(r)
    return root, len(payload)


def load_payload(payload):
    return _read_chunk(_R(payload))


def dump_payload(root):
    w = _W()
    _write_chunk(w, root)
    return bytes(w.buf)


def save(path, root, level=1):
    payload = dump_payload(root)
    comp = zlib.compress(payload, level)
    out = struct.pack("<III", 0xFFFFFFFF, len(payload), len(comp)) + comp
    open(path, "wb").write(out)
    return len(out)
