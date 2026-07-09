# Peloton — Season Planner

Een moderne editor & toolkit voor **Pro Cycling Manager `.cdb`-databases**, met als
eerste feature een véél betere **seizoensplanner** dan die in PCM 2026 — en als
fundament voor een grotere wieler-applicatie (stats, hoogtestages/vorm,
fietsmodellen). Ontstaan omdat [davydepuydt.com](https://davydepuydt.com/) sinds
PCM2025 gestopt is.

De app draait lokaal als web-app (Python-backend + moderne SPA) en is bedoeld om
later als **desktop-applicatie** ingepakt te worden.

## De app draaien

```bash
python -m server.app /pad/naar/Career.cdb        # start op http://127.0.0.1:8765
# open die URL in je browser
```

Geen dependencies nodig — de backend draait op Python's standaardbibliotheek.

Wat de planner nu kan:
- **Seizoenskalender** per ploeg, met datums, prestige (WorldTour/Pro/Continental/NK)
  en populariteit.
- **Selectie samenstellen** per koers: huidige renners + gerangschikte suggesties
  met een **fit-score** (specialiteit × koerseisen) en niveau.
- **Automatisch aanvullen** op specialiteit.
- **Realistische kalender genereren** voor een ploeg: verdeelt renners over hun
  koersen op basis van specialiteit, niveau en belasting; seed + variatie zorgen
  dat elk seizoen anders is. Bewaart support-groepen en respecteert roster-limieten.
- **Opslaan** terug naar een game-leesbare `.cdb`.

## Structuur

```
pcmdb/               herbruikbare kern (engine + domeinmodel)
  cdb.py             binaire engine — zlib-container + recursieve chunk-boom (byte-exact)
  schema.py          getypeerde laag — Database/Table, decode+encode van alle 8 datatypes
  model.py           career-facade — renners (karakteristieken/specialiteit), koersen, teams
  calendar_gen.py    realistische, seed-gestuurde kalendergenerator voor AI-ploegen
  planner.py         seizoensprogramma-hulplaag
server/app.py        lokale API + statische server (stdlib, nul runtime-deps)
web/                 moderne SPA (index.html / style.css / app.js)
cli.py               command-line inspectie & bewerking
tests/               round-trip- + encoder-inverse-tests (zet PCM_CDB naar een career .cdb)
docs/CDB_FORMAT.md   geverifieerde specificatie van het .cdb-formaat
```

## Kern-engine (bewezen)

End-to-end getest op een echte PCM26-career (25 MB, 145 tabellen, 9810 renners):

- ✅ `.cdb` uitpakken (zlib) + weer inpakken zodat de game 'm inleest
- ✅ **Byte-exacte** round-trip van de volledige chunk-boom (5344 chunks)
- ✅ Alle 8 datatypes lezen én schrijven; de encoder is een perfecte inverse —
     een edit raakt alléén wat je wijzigt, de rest blijft byte-identiek
- ✅ `python -m pytest tests/` (3 tests groen, met `PCM_CDB` gezet)

## Roadmap

1. **Seizoensplanner** (nu werkend, wordt verder uitgebouwd)
2. **Stats & dashboards** — renner-/ploeg-/koersanalyses
3. **Hoogtestages + vorm** — `STA_training_stages(_massifs/_type)`, `DYN_training_stage_*`,
   `DYN_cyclist_fitness/fitpeak_history/peak_detail`, `STA_condition_type`
4. **Fietsmodellen** — `STA_equipment_model/template`, `DYN_equipment_selection/techno`
5. **Desktop-verpakking** (bv. pywebview) + distributie

## Let op

Maak altijd een back-up van je career-bestand voordat je het bewerkt. Onofficiële,
community-gedreven tooling; niet verbonden aan Cyanide/Nacon.
