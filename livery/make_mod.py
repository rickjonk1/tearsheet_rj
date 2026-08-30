"""Maak van een bewerkte texture een PCM-mod .pak.

    python3 livery/make_mod.py nieuw.png Frm_Cervel_TVL001_25_diff VDK_Frame_P.pak

Verwacht naast elkaar in dezelfde map: <naam>.uasset, <naam>.uexp en <naam>.ubulk
zoals uit FModel komen. De .uasset en .uexp gaan ongewijzigd mee; alleen de .ubulk
wordt opnieuw opgebouwd uit jouw PNG (met het originele alfakanaal, zie ubulk.py).

Het pad binnen de pak wordt uit de .uasset zelf gelezen: daar staat de package-naam
in, bv. /Mod/Equipment/Frame/Frm_Cervel_XXX001_25/Frm_Cervel_TVL001_25_diff. De /Mod/
mount is de plugin pcm25_mod1/Plugins/Mod, dus /Mod/X wordt Content/X in de pak.
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pakbuild, ubulk

MOUNT = "../../../pcm25_mod1/Plugins/Mod/"


def package_path(uasset_bytes):
    """Haal /Mod/... uit de naamtabel van de .uasset."""
    hits = re.findall(rb"/Mod/[\x20-\x7e]+", uasset_bytes)
    if not hits:
        raise ValueError("geen /Mod/-package gevonden in de .uasset — is dit wel een "
                         "asset uit de Mod-plugin?")
    return max(hits, key=len).decode()


def make(png, stem, out_pak):
    base = os.path.splitext(stem)[0]
    uasset = open(base + ".uasset", "rb").read()
    uexp = open(base + ".uexp", "rb").read()
    pkg = package_path(uasset)
    inner = "Content/" + pkg[len("/Mod/"):]
    print("package %s\n   -> %s.{uasset,uexp,ubulk}" % (pkg, inner))

    tmp = base + ".new.ubulk"
    ubulk.build(png, base + ".ubulk", tmp)
    data = open(tmp, "rb").read()
    os.remove(tmp)
    print("ubulk %d bytes" % len(data))

    pak = pakbuild.build(MOUNT, [(inner + ".uasset", uasset),
                                 (inner + ".uexp", uexp),
                                 (inner + ".ubulk", data)])
    open(out_pak, "wb").write(pak)
    print("geschreven %s (%d bytes)" % (out_pak, len(pak)))
    return out_pak


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    make(sys.argv[1], sys.argv[2], sys.argv[3])
