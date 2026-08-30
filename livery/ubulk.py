"""Bouw een PCM-fietslivery .ubulk (DXT5/BC3, 6 mips) uit een bewerkte PNG.

De .ubulk is niets anders dan de ruwe BC3-blokken van alle mipmaps achter elkaar,
van KLEIN naar GROOT: 128, 256, 512, 1024, 2048, 4096. Samen 22.364.160 bytes.
Er staat geen header, geen checksum en geen lengte in — de .uasset/.uexp beschrijven
het formaat. Daarom mag je de .ubulk vervangen zolang de lengte exact gelijk blijft.

Het alfakanaal is géén doorzichtigheid maar een metaalmasker (cassette, kettingbladen,
remschijven, kabels). Dat halen we per mip uit het origineel, zodat een bewerking die
alleen RGB verandert de aandrijflijn niet sloopt.
"""
import io, struct, sys
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

SIZES = [128, 256, 512, 1024, 2048, 4096]      # volgorde in het bestand
TOTAL = sum(s * s for s in SIZES)              # 22_364_160, 1 byte per pixel bij BC3


def _dds_header(w, h):
    return (b"DDS " + struct.pack("<IIIIII", 124, 0x000A1007, h, w,
                                  max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 16, 0)
            + struct.pack("<I", 1) + b"\x00" * 44
            + struct.pack("<II", 32, 0x4) + b"DXT5" + b"\x00" * 20
            + struct.pack("<IIIII", 0x1000, 0, 0, 0, 0))


def decode_mips(ubulk_path):
    """Geeft de 6 mips terug als RGBA-afbeeldingen, klein -> groot."""
    raw = open(ubulk_path, "rb").read()
    if len(raw) != TOTAL:
        raise ValueError("verwacht %d bytes, kreeg %d" % (TOTAL, len(raw)))
    out, o = [], 0
    for s in SIZES:
        n = s * s
        out.append(Image.open(io.BytesIO(_dds_header(s, s) + raw[o:o + n])).convert("RGBA"))
        o += n
    return out


def encode(rgb_top, alpha_mips):
    """rgb_top: RGB-afbeelding 4096x4096. alpha_mips: 6 L-afbeeldingen, klein -> groot.
    Geeft de complete .ubulk terug."""
    if rgb_top.size != (4096, 4096):
        raise ValueError("de bovenste mip moet 4096x4096 zijn, is %dx%d" % rgb_top.size)
    parts = []
    for s, a in zip(SIZES, alpha_mips):
        rgb = rgb_top if s == 4096 else rgb_top.resize((s, s), Image.LANCZOS)
        if a.size != (s, s):
            a = a.resize((s, s), Image.LANCZOS)
        img = rgb.convert("RGBA")
        img.putalpha(a)
        buf = io.BytesIO()
        img.save(buf, format="dds", pixel_format="DXT5")
        blocks = buf.getvalue()[128:]
        if len(blocks) != s * s:
            raise ValueError("mip %d gaf %d bytes, verwacht %d" % (s, len(blocks), s * s))
        parts.append(blocks)
    out = b"".join(parts)
    assert len(out) == TOTAL, len(out)
    return out


def build(png_path, original_ubulk, out_path):
    """Hoofdroute: PNG erin (elke vierkante maat), nieuwe .ubulk eruit."""
    orig = decode_mips(original_ubulk)
    alpha = [m.getchannel("A") for m in orig]
    src = Image.open(png_path).convert("RGB")
    if src.size[0] != src.size[1]:
        raise ValueError("de texture moet vierkant zijn, is %dx%d" % src.size)
    if src.size != (4096, 4096):
        print("let op: %dx%d wordt opgeschaald naar 4096x4096" % src.size, file=sys.stderr)
        src = src.resize((4096, 4096), Image.LANCZOS)
    data = encode(src, alpha)
    open(out_path, "wb").write(data)
    return out_path


if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2], sys.argv[3]))
