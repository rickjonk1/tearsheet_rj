# Fietsliveries aanpassen

PCM Assets doet dit voor shirts. Voor frames bestaat geen tool, maar het mechanisme
is hetzelfde: een `.pak` in de mods-map die één asset uit `pakchunk9-Windows.pak`
overschrijft.

## Hoe het in elkaar zit

Een livery is één Texture2D, bv.
`/Mod/Equipment/Frame/Frm_Cervel_XXX001_25/Frm_Cervel_TVL001_25_diff`, en bestaat
uit drie bestanden:

| bestand   | inhoud                                                    |
|-----------|-----------------------------------------------------------|
| `.uasset` | package-header, naamtabel, `PF_DXT5`                       |
| `.uexp`   | de kleinste mipmaps, inline                                |
| `.ubulk`  | de grote mipmaps, ruwe BC3-blokken, verder niets           |

De `.ubulk` heeft **geen header, geen lengteveld en geen checksum**: in de `.uasset`
en `.uexp` staat nergens een hash van de bulkdata. Daarom mag je hem vervangen zolang
de lengte exact klopt. Voor een frame is dat 22.364.160 bytes — zes vierkante mips van
klein naar groot (128, 256, 512, 1024, 2048, 4096) bij één byte per pixel:

    128² + 256² + 512² + 1024² + 2048² + 4096² = 22.364.160

Niets daarvan staat hardgecodeerd in de tool. Het pixelformaat komt uit de naamtabel
van de `.uasset` (`PF_DXT5`, `PF_DXT1`) en de mipketen wordt teruggerekend uit de
lengte van de `.ubulk`: er is maar één reeks halverende vierkanten die precies op dat
aantal bytes uitkomt. Een wiel of helm is kleiner dan een frame en soms DXT1 in plaats
van DXT5, en dat werkt zo vanzelf mee.

De `XXX` in de mapnaam is het generieke frame; `TVL` is de teamvariant. Elk team heeft
zijn eigen `_diff`.

### Het alfakanaal is een metaalmasker

Bij `Frm_Cervel_TVL001_25_diff` is 99,1% van de texture alfa ≈ 0 en zit de rest precies
op cassette, kettingbladen, remschijven en kabels. Het is dus geen doorzichtigheid maar
een masker voor de metalen onderdelen. `ubulk.py` haalt het alfakanaal per mip uit het
origineel, zodat een bewerking die alleen RGB verandert de aandrijflijn niet sloopt.

### De teamsleutel komt van de hoofdsponsor, niet van de ploeg

`TVL` in de bestandsnaam is de sleutel van Visma. Welke sleutel het spel opvraagt
hangt aan de **hoofdsponsor** van dat seizoen, niet aan de naam die je de ploeg geeft.
Bij een sponsorwissel schrijft het spel de sleutel van de nieuwe sponsor over in
`DYN_team.jersey_sz_abbreviation` — dus een save waarin de sponsor per 2031 wisselt
naar een fictieve sponsor (`x-voo`, `vdk`) vraagt vanaf dat jaar om
`Frm_Cervel_X-VOO001_25_diff` of `Frm_Cervel_VDK001_25_diff`, en die bestaan niet.

Het gevolg is een fiets zonder texture: frame én wielen, want de wielen gaan langs
dezelfde sleutel. Dat lijkt op een kapotte mod maar staat er los van. Twee manieren
om het op te lossen:

- zet `DYN_sponsor.jersey_sz_abbreviation` van de nieuwe sponsor op een sleutel die
  wél bestaat (`tvl`), dan gebruikt de ploeg die liveries — één cel, geen pak nodig;
- of lever met `uename.rename()` een complete set assets onder de nieuwe sleutel.
  Dat betekent frame, wielen, helm en shirts, niet alleen het frame.

### De LOD-kopieën

De onderste derde van de texture is geen decoratie: dat zijn dezelfde UV-eilanden op
halve en kwart schaal, voor de LOD-modellen. Wie alleen de grote versie bewerkt, krijgt
een fiets die van verandert zodra de camera terugtrekt.

## Gebruik

Trek met FModel de drie bestanden uit `pakchunk9-Windows.pak`, zet ze naast elkaar en:

    python3 livery/make_mod.py nieuw.png pad/naar/Frm_Cervel_TVL001_25_diff VDK_Frame_P.pak

`nieuw.png` is je bewerkte texture (4096×4096; kleiner wordt opgeschaald, met een
waarschuwing). De `.pak` gaat in dezelfde mods-map waar PCM Assets zijn paks neerzet.
Het pad binnen de pak wordt uit de `.uasset` gelezen, dus je hoeft niets in te typen.

## De pak-schrijver

`pakbuild.py` schrijft Unreal PAK v11, ongecomprimeerd en onversleuteld. Gevalideerd
door een echte PCM Assets-pak van 24 MB opnieuw op te bouwen uit zijn eigen inhoud:
identieke lengte, en van de 24.176.527 bytes verschilden er 183 — alleen de
path-hash-waarden en de twee SHA1's die daarover gaan. Het bestandsgedeelte, alle
record-headers, de encoded entries, de directory-index en de footer zijn byte-identiek.

Die 183 bytes zijn geen fout van ons: PCM Assets schrijft in de path-hash-index geen
echte CityHash64, en sorteert de tabel niet eens — terwijl UnrealPak dat wel doet en
Unreal er binair in zoekt. Hun paks werken omdat het spel op de directory-index
terugvalt. `uecity.py` implementeert de echte `FPakFile::HashPath` (pad kleingemaakt,
UTF-16LE, CityHash64WithSeed) en `pakbuild.py` sorteert wel, dus onze pak is op dat punt
strikt correcter dan een pak die al werkt.

## Wat nog niet in de game getest is

Alles hierboven is op bestandsniveau geverifieerd, niet in PCM zelf. Onbekend blijft of
het spel een pak accepteert die niet door UnrealPak is gemaakt.
