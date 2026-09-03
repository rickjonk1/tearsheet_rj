"""Bouw een PCM-livery .ubulk uit een bewerkte PNG.

De .ubulk is niets anders dan de ruwe blokken van alle grote mipmaps achter elkaar,
van KLEIN naar GROOT. Er staat geen header, geen lengteveld en geen checksum in — de
.uasset/.uexp beschrijven het formaat. Daarom mag je hem vervangen zolang de lengte
exact gelijk blijft.

Niets daarvan wordt hier hardgecodeerd. Het pixelformaat komt uit de naamtabel van de
.uasset (`PF_DXT5`, `PF_DXT1`, ...) en de mipketen wordt teruggerekend uit de lengte
van de .ubulk zelf: er is maar één reeks halverende vierkanten die precies op dat
aantal bytes uitkomt. Het frame is 4096² DXT5 met zes mips (22.364.160 bytes), maar
een wiel of helm is kleiner en soms DXT1, en dat werkt zo vanzelf mee.

Het alfakanaal is bij deze texturen géén doorzichtigheid maar een masker voor de
metalen onderdelen — bij het frame ligt 99,1% op alfa 0 en de rest precies op cassette,
kettingbladen, remschijven en kabels. We halen het per mip uit het origineel, zodat een
bewerking die alleen RGB verandert de aandrijflijn niet sloopt.
"""
import io
import struct
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# bytes per pixel, en de FourCC waarmee Pillow het leest en schrijft
FORMATS = {
    "PF_DXT1": (0.5, "DXT1"),
    "PF_DXT5": (1.0, "DXT5"),
    "PF_BC5": (1.0, "DXT5"),        # tweekanaals; alleen lezen is zinvol
}

MAX_DIM = 8192


def pixel_format(uasset_path):
    """Lees het pixelformaat uit de naamtabel van de .uasset."""
    import uename
    data = open(uasset_path, "rb").read()
    names = [n for _, n, _, _ in uename.name_table(data) if n.startswith("PF_")]
    if not names:
        raise ValueError("geen PF_-formaat gevonden in %s" % uasset_path)
    if names[0] not in FORMATS:
        raise ValueError("formaat %s wordt niet ondersteund (wel: %s)"
                         % (names[0], ", ".join(sorted(FORMATS))))
    return names[0]


def mip_chain(nbytes, fmt="PF_DXT5"):
    """Welke vierkante mips passen precies in `nbytes`? Klein -> groot.

    Een blokformaat kost een vast aantal bytes per pixel, dus voor een gegeven
    bovenmaat en aantal mips ligt de totale lengte vast. Andersom is de oplossing
    uniek: geen twee ketens komen op hetzelfde aantal bytes uit.
    """
    bpp = FORMATS[fmt][0]
    top = MAX_DIM
    while top >= 4:
        sizes = []
        s = top
        while s >= 4:
            sizes.insert(0, s)
            if sum(int(x * x * bpp) for x in sizes) == nbytes:
                return sizes
            if sum(int(x * x * bpp) for x in sizes) > nbytes:
                break
            s //= 2
        top //= 2
    raise ValueError("geen mipketen van %s past op %d bytes" % (fmt, nbytes))


def _dds_header(w, h, fourcc):
    block = 8 if fourcc == "DXT1" else 16
    return (b"DDS " + struct.pack("<IIIIII", 124, 0x000A1007, h, w,
                                  max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block, 0)
            + struct.pack("<I", 1) + b"\x00" * 44
            + struct.pack("<II", 32, 0x4) + fourcc.encode() + b"\x00" * 20
            + struct.pack("<IIIII", 0x1000, 0, 0, 0, 0))


def decode_mips(ubulk_path, fmt="PF_DXT5"):
    """Geeft de mips terug als RGBA-afbeeldingen, klein -> groot."""
    raw = open(ubulk_path, "rb").read()
    bpp, fourcc = FORMATS[fmt]
    sizes = mip_chain(len(raw), fmt)
    out, o = [], 0
    for s in sizes:
        n = int(s * s * bpp)
        out.append(Image.open(io.BytesIO(_dds_header(s, s, fourcc) + raw[o:o + n])).convert("RGBA"))
        o += n
    return out


def encode(rgb_top, alpha_mips, fmt="PF_DXT5"):
    """rgb_top: RGB op de bovenste mipmaat. alpha_mips: L-afbeeldingen, klein -> groot.
    Geeft de complete .ubulk terug."""
    bpp, fourcc = FORMATS[fmt]
    sizes = [a.size[0] for a in alpha_mips]
    top = sizes[-1]
    if rgb_top.size != (top, top):
        raise ValueError("de bovenste mip moet %dx%d zijn, is %dx%d"
                         % (top, top, rgb_top.size[0], rgb_top.size[1]))
    parts = []
    for s, a in zip(sizes, alpha_mips):
        rgb = rgb_top if s == top else rgb_top.resize((s, s), Image.LANCZOS)
        if a.size != (s, s):
            a = a.resize((s, s), Image.LANCZOS)
        img = rgb.convert("RGBA")
        img.putalpha(a)
        buf = io.BytesIO()
        img.save(buf, format="dds", pixel_format=fourcc)
        blocks = buf.getvalue()[128:]
        want = int(s * s * bpp)
        if len(blocks) != want:
            raise ValueError("mip %d gaf %d bytes, verwacht %d" % (s, len(blocks), want))
        parts.append(blocks)
    return b"".join(parts)


def build(png_path, original_ubulk, out_path, uasset_path=None):
    """Hoofdroute: PNG erin, nieuwe .ubulk eruit — even lang als het origineel."""
    fmt = pixel_format(uasset_path) if uasset_path else "PF_DXT5"
    orig = decode_mips(original_ubulk, fmt)
    alpha = [m.getchannel("A") for m in orig]
    top = orig[-1].size[0]

    src = Image.open(png_path).convert("RGB")
    if src.size[0] != src.size[1]:
        raise ValueError("de texture moet vierkant zijn, is %dx%d" % src.size)
    if src.size != (top, top):
        print("let op: %dx%d wordt geschaald naar %dx%d" % (src.size + (top, top)),
              file=sys.stderr)
        src = src.resize((top, top), Image.LANCZOS)

    data = encode(src, alpha, fmt)
    expect = len(open(original_ubulk, "rb").read())
    if len(data) != expect:
        raise ValueError("nieuwe .ubulk is %d bytes, origineel %d" % (len(data), expect))
    open(out_path, "wb").write(data)
    return out_path


if __name__ == "__main__":
    print(build(*sys.argv[1:]))
