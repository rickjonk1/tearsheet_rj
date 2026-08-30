"""CityHash64 / CityHash64WithSeed — de hash die Unreal gebruikt voor de
path-hash-index van een .pak (FPakFile::HashPath)."""
import struct

M = 0xFFFFFFFFFFFFFFFF
k0 = 0xc3a5c85c97cb3127
k1 = 0xb492b66fbe98f273
k2 = 0x9ae16a3b2f90404f


def _rot(v, s):
    return v if s == 0 else ((v >> s) | (v << (64 - s))) & M


def _shiftmix(v):
    return v ^ (v >> 47)


def _f64(s, o):
    return struct.unpack_from("<Q", s, o)[0]


def _f32(s, o):
    return struct.unpack_from("<I", s, o)[0]


def _bswap(v):
    return int.from_bytes(v.to_bytes(8, "little"), "big")


def _len16(u, v, mul=None):
    if mul is None:
        mul = 0x9ddfea08eb382d69
    a = ((u ^ v) * mul) & M
    a ^= a >> 47
    b = ((v ^ a) * mul) & M
    b ^= b >> 47
    return (b * mul) & M


def _len0to16(s, n):
    if n >= 8:
        mul = (k2 + n * 2) & M
        a = (_f64(s, 0) + k2) & M
        b = _f64(s, n - 8)
        c = (_rot(b, 37) * mul + a) & M
        d = ((_rot(a, 25) + b) * mul) & M
        return _len16(c, d, mul)
    if n >= 4:
        mul = (k2 + n * 2) & M
        a = _f32(s, 0)
        return _len16((n + (a << 3)) & M, _f32(s, n - 4), mul)
    if n > 0:
        a, b, c = s[0], s[n >> 1], s[n - 1]
        y = (a + (b << 8)) & 0xFFFFFFFF
        z = (n + (c << 2)) & 0xFFFFFFFF
        return (_shiftmix(((y * k2) & M) ^ ((z * k0) & M)) * k2) & M
    return k2


def _len17to32(s, n):
    mul = (k2 + n * 2) & M
    a = (_f64(s, 0) * k1) & M
    b = _f64(s, 8)
    c = (_f64(s, n - 8) * mul) & M
    d = (_f64(s, n - 16) * k2) & M
    return _len16((_rot((a + b) & M, 43) + _rot(c, 30) + d) & M,
                  (a + _rot((b + k2) & M, 18) + c) & M, mul)


def _weak(w, x, y, z, a, b):
    a = (a + w) & M
    b = _rot((b + a + z) & M, 21)
    c = a
    a = (a + x + y) & M
    b = (b + _rot(a, 44)) & M
    return (a + z) & M, (b + c) & M


def _weak_s(s, o, a, b):
    return _weak(_f64(s, o), _f64(s, o + 8), _f64(s, o + 16), _f64(s, o + 24), a, b)


def _len33to64(s, n):
    mul = (k2 + n * 2) & M
    a = (_f64(s, 0) * k2) & M
    b = _f64(s, 8)
    c = _f64(s, n - 24)
    d = _f64(s, n - 32)
    e = (_f64(s, 16) * k2) & M
    f = (_f64(s, 24) * 9) & M
    g = _f64(s, n - 8)
    h = (_f64(s, n - 16) * mul) & M
    u = (_rot((a + g) & M, 43) + ((_rot(b, 30) + c) * 9)) & M
    v = (((a + g) ^ d) + f + 1) & M
    w = (_bswap(((u + v) * mul) & M) + h) & M
    x = (_rot((e + f) & M, 42) + c) & M
    y = ((_bswap(((v + w) * mul) & M) + g) * mul) & M
    z = (e + f + c) & M
    a = (_bswap(((x + z) * mul + y) & M) + b) & M
    b = (_shiftmix(((z + a) * mul + d + h) & M) * mul) & M
    return (b + x) & M


def cityhash64(s):
    n = len(s)
    if n <= 32:
        return _len0to16(s, n) if n <= 16 else _len17to32(s, n)
    if n <= 64:
        return _len33to64(s, n)

    x = _f64(s, n - 40)
    y = (_f64(s, n - 16) + _f64(s, n - 56)) & M
    z = _len16((_f64(s, n - 48) + n) & M, _f64(s, n - 24))
    v = _weak_s(s, n - 64, n, z)
    w = _weak_s(s, n - 32, (y + k1) & M, x)
    x = (x * k1 + _f64(s, 0)) & M

    o = 0
    n = (n - 1) & ~63
    while True:
        x = (_rot((x + y + v[0] + _f64(s, o + 8)) & M, 37) * k1) & M
        y = (_rot((y + v[1] + _f64(s, o + 48)) & M, 42) * k1) & M
        x ^= w[1]
        y = (y + v[0] + _f64(s, o + 40)) & M
        z = (_rot((z + w[0]) & M, 33) * k1) & M
        v = _weak_s(s, o, (v[1] * k1) & M, (x + w[0]) & M)
        w = _weak_s(s, o + 32, (z + w[1]) & M, (y + _f64(s, o + 16)) & M)
        z, x = x, z
        o += 64
        n -= 64
        if n == 0:
            break
    return _len16((_len16(v[0], w[0]) + (_shiftmix(y) * k1) + z) & M,
                  (_len16(v[1], w[1]) + x) & M)


def cityhash64_with_seeds(s, seed0, seed1):
    return _len16((cityhash64(s) - seed0) & M, seed1)


def cityhash64_with_seed(s, seed):
    return cityhash64_with_seeds(s, k2, seed)


def hash_path(relative_path, seed=0):
    """FPakFile::HashPath — pad kleingemaakt, als UTF-16LE, CityHash64WithSeed."""
    return cityhash64_with_seed(relative_path.lower().encode("utf-16-le"), seed)
