"""Typed table layer on top of cdb.py chunk tree."""
import struct
from . import cdb


def _decode_column(col, nrow):
    dt = col.find(cdb.COLUMN_DATA_TYPE).raw
    dtype = struct.unpack("<I", dt)[0]
    vals_chunk = col.find(cdb.COLUMN_VALUES)
    blob_chunk = col.find(cdb.COLUMN_BLOB)
    vraw = vals_chunk.raw if vals_chunk else b""
    braw = blob_chunk.raw if blob_chunk else b""

    if dtype == cdb.DT_INT:
        return list(struct.unpack_from("<%di" % nrow, vraw, 0))
    if dtype == cdb.DT_FLOAT:
        return list(struct.unpack_from("<%df" % nrow, vraw, 0))
    if dtype == cdb.DT_BYTE:
        return list(struct.unpack_from("<%db" % nrow, vraw, 0))
    if dtype == cdb.DT_SHORT:
        return list(struct.unpack_from("<%dH" % nrow, vraw, 0))
    if dtype == cdb.DT_BOOL:
        out = []
        for i in range(nrow):
            out.append(bool((vraw[i >> 3] >> (i & 7)) & 1))
        return out
    if dtype == cdb.DT_STRING:
        lens = struct.unpack_from("<%dI" % nrow, vraw, 0)
        out = []
        o = 4  # skip u32 blob-length prefix
        for ln in lens:
            s = braw[o:o + ln]
            o += ln
            out.append(s.rstrip(b"\x00").decode("utf-8", "surrogateescape"))
        return out
    if dtype in (cdb.DT_FLOAT_LIST, cdb.DT_INT_LIST):
        counts = struct.unpack_from("<%dI" % nrow, vraw, 0)
        fmt = "<f" if dtype == cdb.DT_FLOAT_LIST else "<i"
        out = []
        o = 4  # skip u32 blob-length prefix
        for cnt in counts:
            items = []
            for _ in range(cnt):
                items.append(struct.unpack_from(fmt, braw, o)[0]); o += 4
            out.append(items)
        return out
    raise ValueError("unknown dtype %d in column %r" % (dtype, col.desc))


def _encode_column(dtype, values):
    """Return (values_bytes, blob_bytes_or_None) for a column of `values`."""
    n = len(values)
    if dtype == cdb.DT_INT:
        return struct.pack("<%di" % n, *values), None
    if dtype == cdb.DT_FLOAT:
        return struct.pack("<%df" % n, *values), None
    if dtype == cdb.DT_BYTE:
        return struct.pack("<%db" % n, *values), None
    if dtype == cdb.DT_SHORT:
        return struct.pack("<%dH" % n, *values), None
    if dtype == cdb.DT_BOOL:
        buf = bytearray((n + 7) // 8)
        for i, v in enumerate(values):
            if v:
                buf[i >> 3] |= 1 << (i & 7)
        return bytes(buf), None
    if dtype == cdb.DT_STRING:
        blob = bytearray(4)  # reserve prefix
        lens = []
        for s in values:
            b = s.encode("utf-8", "surrogateescape") + b"\x00"
            lens.append(len(b))
            blob += b
        struct.pack_into("<I", blob, 0, len(blob) - 4)
        blob += b"\x00" * ((4 - (len(blob) & 3)) & 3)  # pad to 4
        return struct.pack("<%dI" % n, *lens), bytes(blob)
    if dtype in (cdb.DT_FLOAT_LIST, cdb.DT_INT_LIST):
        fmt = "<f" if dtype == cdb.DT_FLOAT_LIST else "<i"
        blob = bytearray(4)
        counts = []
        for items in values:
            counts.append(len(items))
            for it in items:
                blob += struct.pack(fmt, it)
        struct.pack_into("<I", blob, 0, len(blob) - 4)
        blob += b"\x00" * ((4 - (len(blob) & 3)) & 3)
        return struct.pack("<%dI" % n, *counts), bytes(blob)
    raise ValueError("cannot encode dtype %d" % dtype)


class Table:
    def __init__(self, chunk):
        self.chunk = chunk
        self.name = chunk.desc
        self.id = struct.unpack("<i", chunk.find(cdb.TABLE_ID).raw)[0]
        self.nrow = struct.unpack("<I", chunk.find(cdb.ROW_COUNT).raw)[0]
        defs = chunk.find(cdb.COLUMN_DEFINITIONS)
        self.cols = defs.children if defs else []
        self.colnames = [c.desc for c in self.cols]

    def coltype(self, col):
        return struct.unpack("<I", col.find(cdb.COLUMN_DATA_TYPE).raw)[0]

    def column(self, name):
        for c in self.cols:
            if c.desc == name:
                return _decode_column(c, self.nrow)
        raise KeyError(name)

    def set_column(self, name, values):
        """Write a full column back into the chunk tree (in place)."""
        if len(values) != self.nrow:
            raise ValueError("expected %d values, got %d" % (self.nrow, len(values)))
        col = next(c for c in self.cols if c.desc == name)
        dtype = self.coltype(col)
        vbytes, bbytes = _encode_column(dtype, values)
        col.find(cdb.COLUMN_VALUES).raw = vbytes
        blob = col.find(cdb.COLUMN_BLOB)
        if bbytes is not None:
            if blob is None:
                raise ValueError("string/list column %r has no blob chunk" % name)
            blob.raw = bbytes

    def set_nrow(self, n):
        """Change the row count (updates the ROW_COUNT chunk)."""
        self.nrow = n
        self.chunk.find(cdb.ROW_COUNT).raw = struct.pack("<I", n)

    def set_data(self, columns):
        """Replace the whole table body. `columns` maps every column name to a
        list of values (all lists the same length -> the new row count)."""
        lengths = {len(v) for v in columns.values()}
        if len(lengths) != 1:
            raise ValueError("all columns must have equal length")
        self.set_nrow(lengths.pop())
        for c in self.cols:
            self.set_column(c.desc, columns[c.desc])

    def rows(self, limit=None):
        n = self.nrow if limit is None else min(limit, self.nrow)
        data = {c.desc: _decode_column(c, self.nrow) for c in self.cols}
        for i in range(n):
            yield {k: v[i] for k, v in data.items()}


class Database:
    def __init__(self, root):
        self.root = root
        tables_arr = root.find(cdb.DATABASE_TABLES)
        self.tables = {}
        for t in tables_arr.children:
            if t.type == cdb.TABLE:
                tb = Table(t)
                self.tables[tb.name] = tb

    @classmethod
    def load(cls, path):
        root, _ = cdb.load(path)
        return cls(root)

    def __getitem__(self, name):
        return self.tables[name]
