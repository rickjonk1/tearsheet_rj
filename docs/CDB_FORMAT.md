# Cyanide `.cdb` binary format (verified)

Reverse-engineered and **byte-exactly round-tripped** against a PCM 2026 career
database (25 MB payload, 5344 chunks, 145 tables). Everything below is confirmed
against real bytes, not guessed.

## 1. File container

```
offset  size  field
0x00    4     magic 0xFFFFFFFF
0x04    4     uncompressed payload size (uint32 LE)
0x08    4     compressed payload size   (uint32 LE)
0x0C    ..    zlib stream  (header 0x78 0x01)
```

`zlib.decompress(data[12:])` yields the payload; `zlib.compress(payload, 1)`
re-packs it (the game re-reads any valid zlib stream — the compressed size need
not match the original).

## 2. Chunk tree

The payload is a tree of chunks. Every chunk:

```
0xAAAAAAAA                      CHUNK_BEGIN
uint32   size                   total bytes, from this AA up to & incl. trailing CC
uint32   type                   chunk type id (see below)
uint32   flags                  always 0
uint32   descPresent            1 if a description/name string follows
[ uint32 strLen                 length incl. NUL terminator
  bytes  string                 UTF-8
  pad    -> 4-byte alignment ]
0xBBBBBBBB                      CHUNK_SEPARATOR (metadata -> body)
<body>
0xCCCCCCCC                      CHUNK_END
```

**Body** is one of:
- child chunks (container) — read chunks while the next word is `0xAAAAAAAA`;
- an **array**: `0xDDDDDDDD  uint32 count  <count child chunks>  0xEEEEEEEE`;
- raw leaf bytes (everything up to the trailing `CC`).

## 3. Chunk type ids

| id   | name               | role                                  |
|------|--------------------|---------------------------------------|
| 0x00 | WRAPPER            | root container                        |
| 0x01 | DATABASE_TABLES    | array of tables                       |
| 0x02 | DATABASE_FLAGS     | db metadata                           |
| 0x10 | TABLE              | table container (desc = table name)   |
| 0x11 | ROW_COUNT          | uint32 row count                      |
| 0x12 | COLUMN_DEFINITIONS | array of columns                      |
| 0x15 | TABLE_ID           | int32 table id                        |
| 0x16 | TABLE_FLAGS        | int32                                 |
| 0x20 | COLUMN             | column container (desc = column name) |
| 0x21 | COLUMN_DATA_TYPE   | uint32 data-type id                   |
| 0x22 | COLUMN_VALUES      | fixed-width values / lengths / counts |
| 0x23 | COLUMN_BLOB        | variable-length payload (strings/lists)|
| 0x24 | COLUMN_INDEX       | int32 column position                 |

## 4. Column-wise storage

Storage is **columnar**: a column holds all rows' values contiguously.

| data type       | id | `0x22` COLUMN_VALUES                | `0x23` COLUMN_BLOB                     |
|-----------------|----|------------------------------------|---------------------------------------|
| INTEGER         | 0  | `nrow × int32`                     | —                                     |
| FLOAT           | 1  | `nrow × float32`                   | —                                     |
| STRING          | 2  | `nrow × uint32` byte-lengths (incl NUL) | `uint32 total` + concatenated NUL-terminated strings + pad-to-4 |
| BOOLEAN         | 3  | bit-packed, 8 per byte             | —                                     |
| INTEGER_BYTE    | 4  | `nrow × int8`                      | —                                     |
| INTEGER_SHORT   | 5  | `nrow × uint16`                    | —                                     |
| FLOAT_LIST      | 10 | `nrow × uint32` element counts     | `uint32 total` + `float32` elements + pad-to-4 |
| INTEGER_LIST    | 11 | `nrow × uint32` element counts     | `uint32 total` + `int32` elements + pad-to-4 |

The **`0x23` blob prefix** is a `uint32` equal to the sum of the entries that
follow (bytes for strings, element-bytes for lists); the blob is then padded to a
4-byte boundary. This prefix is verified: `sum(lengths) == prefix` on real data.

## 5. Invariants the editor relies on

1. `dump(parse(payload)) == payload` — the chunk engine is lossless.
2. `encode(decode(column)) == column bytes` — editing a value regenerates only
   that column's `0x22`/`0x23` leaves; every other byte is untouched.
3. On write, each container's `size` field is recomputed from its serialized
   length (writer patches `size` after emitting the body).

Both (1) and (2) are covered by `tests/test_roundtrip.py`.
