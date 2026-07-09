# pcm-planner

Toolkit om **Pro Cycling Manager `.cdb`-databases** te lezen en te bewerken, met
als eerste doel een véél betere **seizoensplanner** dan die in PCM 2026 — en als
fundament voor verdere gameplay-features (hoogtestages/vorm, fietsmodellen).

Ontstaan omdat [davydepuydt.com](https://davydepuydt.com/) sinds PCM2025 gestopt is.

## Status

Het **fundament is af en bewezen** op een echte PCM26-career (25 MB, 145 tabellen):

- ✅ `.cdb` uitpakken (zlib) en weer inpakken zodat de game 'm inleest
- ✅ **Byte-exacte** round-trip van de volledige chunk-boom (5344 chunks)
- ✅ Getypeerd lezen van alle 8 datatypes (int, float, string, bool, byte, short, int-list, float-list)
- ✅ Getypeerd **schrijven** — de encoder is een perfecte inverse: een edit raakt
     alléén wat je wijzigt, de rest blijft byte-identiek
- ✅ Planner-datamodel gejoind (kalender + teamprogramma + toegewezen renners)

Voorbeeld — het volledige seizoensprogramma van een team met data en renners:

```
$ python cli.py program career.cdb --team 16
UAE Emirates — 105 races

  20 Jan  Santos Tour Down Under               [7] Jan Tratnik, ... , Brandon McNulty
  24 Jan  Gran Premio Castellón                [7] Tim Wellens, ... , Tadej Pogacar
  ...
```

## Structuur

```
pcmdb/
  cdb.py       binaire engine — zlib-container + recursieve chunk-boom (read/write)
  schema.py    getypeerde laag — Database / Table / kolom decode+encode
  planner.py   domeinmodel — teams, seizoensprogramma, renners toewijzen/verwijderen
cli.py         command-line inspectie & bewerking
tests/         round-trip- en encoder-inverse-tests (zet PCM_CDB naar een career .cdb)
docs/
  CDB_FORMAT.md  geverifieerde specificatie van het .cdb-formaat
```

## Gebruik

```bash
python cli.py info     career.cdb            # tel tabellen/renners/teams
python cli.py teams    career.cdb            # lijst teams + id's
python cli.py program  career.cdb --team 16  # seizoensprogramma van een team
python cli.py tables   career.cdb            # alle 145 tabellen
python cli.py table    career.cdb STA_race   # ruwe tabelinhoud

PCM_CDB=/pad/naar/Career.cdb python -m pytest tests/ -v
```

Als Python-library:

```python
from pcmdb.planner import Planner
p = Planner.load("career.cdb")
for e in p.season_program(16):
    print(e.day, e.month, e.name, [p.rider_label(c) for c in e.roster])

row = p.season_program(16)[0].team_race_row
p.add_rider(row, 12345)      # renner toevoegen aan die koers
p.save("career_edited.cdb")  # terugschrijven — game leest dit in
```

## Roadmap

De engine is generiek: elke tabel is leesbaar én schrijfbaar. De drie beoogde
features hangen elk aan concrete tabellen die al in kaart zijn gebracht:

1. **Seizoensplanner** (nu in opbouw) — `DYN_team_race.gene_ilist_roster`,
   `STA_race`, `STA_stage`, `DYN_cyclist_objective`, `STA_program_cyclist`.
   Doel: renners slim over koersen verdelen met kalenderoverzicht en doelen.
2. **Hoogtestages + vorm** — `STA_training_stages(_massifs/_type/_state)`,
   `DYN_training_stage_*`, en de vorm-/conditietabellen `DYN_cyclist_fitness`,
   `DYN_cyclist_fitpeak_history`, `DYN_cyclist_peak_detail`, `STA_condition_type`.
3. **Fietsmodellen** — `STA_equipment_model`, `STA_equipment_template`,
   `DYN_equipment_selection`, `DYN_equipment_techno`.

De uiteindelijke vorm wordt een **desktop-applicatie** die direct de
savegame-/databasebestanden bewerkt; de `pcmdb`-kern hierboven is de herbruikbare
motor daaronder.

## Let op

Maak altijd een back-up van je career-bestand voordat je het bewerkt. Dit is
onofficiële, community-gedreven tooling en niet verbonden aan Cyanide/Nacon.
