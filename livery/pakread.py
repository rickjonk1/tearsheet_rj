"""Lezer voor Unreal PAK v11 (ongecomprimeerd, onversleuteld)."""
import struct, hashlib

MAGIC = 0x5A6F12E1
# guid16 + encrypted1 + magic4 + versie4 + idxoff8 + idxsize8 + sha20 + 5*32 methodes
FOOTER = 16 + 1 + 4 + 4 + 8 + 8 + 20 + 160    # 221


def _cstr(buf, o):
    n = struct.unpack_from("<i", buf, o)[0]; o += 4
    if n < 0:                       # UTF-16LE, lengte in tekens (negatief)
        b = buf[o:o - n * 2]; o += -n * 2
        return b.decode("utf-16-le").rstrip("\x00"), o
    b = buf[o:o + n]; o += n
    return b.decode("utf-8").rstrip("\x00"), o


def read(path):
    raw = open(path, "rb").read()
    f = raw[-FOOTER:]
    magic, ver = struct.unpack_from("<II", f, 17)
    assert magic == MAGIC, hex(magic)
    idx_off, idx_size = struct.unpack_from("<QQ", f, 25)
    idx_sha = f[41:61]
    idx = raw[idx_off:idx_off + idx_size]
    assert hashlib.sha1(idx).digest() == idx_sha, "index sha mismatch"

    o = 0
    mount, o = _cstr(idx, o)
    nfile = struct.unpack_from("<I", idx, o)[0]; o += 4
    seed = struct.unpack_from("<Q", idx, o)[0]; o += 8

    has_ph = struct.unpack_from("<I", idx, o)[0]; o += 4
    ph_off = ph_size = 0; ph_sha = b""
    if has_ph:
        ph_off, ph_size = struct.unpack_from("<QQ", idx, o); o += 16
        ph_sha = idx[o:o + 20]; o += 20

    has_fd = struct.unpack_from("<I", idx, o)[0]; o += 4
    fd_off = fd_size = 0; fd_sha = b""
    if has_fd:
        fd_off, fd_size = struct.unpack_from("<QQ", idx, o); o += 16
        fd_sha = idx[o:o + 20]; o += 20

    enc_size = struct.unpack_from("<I", idx, o)[0]; o += 4
    enc = idx[o:o + enc_size]; o += enc_size
    nfull = struct.unpack_from("<I", idx, o)[0]; o += 4

    ph = raw[ph_off:ph_off + ph_size]
    fd = raw[fd_off:fd_off + fd_size]
    assert not has_ph or hashlib.sha1(ph).digest() == ph_sha, "path-hash sha mismatch"
    assert not has_fd or hashlib.sha1(fd).digest() == fd_sha, "dir-index sha mismatch"

    # path hash index: u32 count, dan count * (u64 hash, u32 encoded-offset)
    n = struct.unpack_from("<I", ph, 0)[0]
    hashes = [struct.unpack_from("<QI", ph, 4 + i * 12) for i in range(n)]

    # full directory index: u32 ndirs, per dir: naam, u32 nfiles, per file: naam, u32 off
    o2 = 0
    ndir = struct.unpack_from("<I", fd, o2)[0]; o2 += 4
    tree = {}
    for _ in range(ndir):
        d, o2 = _cstr(fd, o2)
        nf = struct.unpack_from("<I", fd, o2)[0]; o2 += 4
        ents = {}
        for _ in range(nf):
            fn, o2 = _cstr(fd, o2)
            ents[fn] = struct.unpack_from("<I", fd, o2)[0]; o2 += 4
        tree[d] = ents

    return dict(raw=raw, ver=ver, mount=mount, nfile=nfile, seed=seed,
                enc=enc, nfull=nfull, hashes=hashes, tree=tree,
                idx_off=idx_off, idx=idx, ph=ph, fd=fd,
                ph_off=ph_off, fd_off=fd_off)


if __name__ == "__main__":
    import sys
    p = read(sys.argv[1])
    print("versie", p["ver"], "mount", repr(p["mount"]))
    print("bestanden", p["nfile"], "seed", hex(p["seed"]), "nfull", p["nfull"])
    print("encoded entries", len(p["enc"]), "bytes =", len(p["enc"]) / 12, "stuks")
    for d, ents in sorted(p["tree"].items()):
        print(" dir", repr(d))
        for fn, off in sorted(ents.items()):
            print("   ", fn, "-> enc@", off)
    print("path hashes:")
    for h, off in p["hashes"]:
        print("   %016x -> %d" % (h, off))
