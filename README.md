# Peloton — Season Planner

Een moderne editor & toolkit voor **Pro Cycling Manager `.cdb`-databases**, met als
eerste feature een véél betere **seizoensplanner** dan die in PCM 2026 — en als
fundament voor een grotere wieler-applicatie (stats, hoogtestages/vorm,
fietsmodellen). Ontstaan omdat [davydepuydt.com](https://davydepuydt.com/) sinds
PCM2025 gestopt is.

De app draait lokaal als web-app (Python-backend + moderne SPA) en is bedoeld om
later als **desktop-applicatie** ingepakt te worden.

## De app draaien

**Als desktop-app** (native venster, met bestandskeuze):

```bash
pip install pywebview          # eenmalig, voor het native venster
python desktop.py              # opent een bestandskiezer, of:
python desktop.py Career.cdb
```

Zonder pywebview valt `desktop.py` terug op je browser.

**Of als web-app:**

```bash
python -m server.app /pad/naar/Career.cdb        # start op http://127.0.0.1:8765
# open die URL in je browser
```

De backend draait op Python's standaardbibliotheek (nul runtime-deps); `pywebview`
is alleen nodig voor het native desktop-venster.

Wat de planner nu kan:
- **Seizoenskalender** per ploeg, met datums, prestige (WorldTour/Pro/Continental/NK)
  en populariteit.
- **Selectie samenstellen** per koers: huidige renners + gerangschikte suggesties
  met een **fit-score** (specialiteit × koerseisen) en niveau.
- **Automatisch aanvullen** op specialiteit.
- **Realistische kalender genereren** voor één ploeg óf het **hele peloton**:
  verdeelt renners over hun koersen op basis van specialiteit, niveau en belasting;
  seed + variatie zorgen dat elk seizoen anders is. Support-groepen blijven bijeen,
  roster-limieten worden gerespecteerd.
- **Doelkoersen** per renner instellen (ster in de editor).
- **Belasting & conflicten**: koersdagen per renner, plus waarschuwingen bij dubbel
  geboekte of te dicht op elkaar geplande renners.
- **Onboarding-wizard** die je vanaf 1 januari door het seizoensbegin leidt.
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
desktop.py           native desktop-launcher (pywebview) met bestandskeuze
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
