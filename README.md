# Piepcheck

Een simpele hulpsite voor reizigers die vastlopen bij het in- of uitchecken met
OVpay. De site legt per situatie in gewone taal uit wat er misging en welke
stappen je kunt zetten.

> **Dit is een studentenproject en geen officiële website van OVpay, GVB of NS.**
> Gemaakt voor de studio Public Lab, Hogeschool van Amsterdam.

**Onderzoeksvraag:** Hoe kan een simpele website reizigers helpen om zelf
problemen met in- en uitchecken via OVpay op te lossen?

## Wat de site doet

- Start met de vraag **"Wat is er gebeurd?"** en vijf grote knoppen (S1 t/m S5)
- Per situatie: korte uitleg, genummerde stappen en een blok "Kom je er niet uit?"
- Bij S5 kun je optioneel je bank kiezen voor stappen die bij jouw app passen
- Een pagina **"Zo check je goed in"** met drie stappen
- Taalschakelaar **NL/EN** op elke pagina
- Geen inlog, geen accounts, geen koppeling met OVpay of banken, geen cookies,
  geen tracking en geen externe fonts of scripts

## Technische keuze

**Vite met vanilla JavaScript.** Geen framework, dus geen extra begrippen om te
leren en een heel kleine bundel (snel op mobiel internet). De site heeft maar
een paar pagina's en geen ingewikkelde interactie, dus React zou hier vooral
extra gewicht en extra code zijn. Vite geeft ons wel het gemak van een dev-server
met hot reload, JSON-imports en een geoptimaliseerde build.

De routing gebruikt de **hash** in de URL (`#/nl/s/S1`). Daardoor werkt de site
als losse statische bestanden, zonder server-instellingen, ook in een submap op
GitHub Pages. De taal staat in de URL, dus je blijft in dezelfde taal als je
doorklikt en je kunt een link in de juiste taal delen.

## Installeren en starten

Je hebt Node.js 18 of hoger nodig.

```bash
npm install     # pakketten installeren (eenmalig)
npm run dev     # dev-server starten, meestal op http://localhost:5173
npm run build   # productiebestanden bouwen naar dist/
npm run preview # de gebouwde site lokaal bekijken
```

## Teksten aanpassen

**Alle teksten staan in JSON-bestanden, niet in de code.** Je hoeft dus geen
JavaScript aan te raken om iets te veranderen.

- Nederlands: `src/content/nl.json`
- Engels: `src/content/en.json`

Beide bestanden hebben **dezelfde structuur en dezelfde sleutels**. Pas je iets
aan in het ene bestand, doe dat dan ook in het andere.

Belangrijke onderdelen:

| Sleutel | Wat het is |
|---|---|
| `home.title`, `home.intro` | De vraag en de introtekst op de homepage |
| `home.order` | De volgorde van de knoppen, bijvoorbeeld `["S1","S2","S3","S4","S5"]` |
| `situations.S1.button` | De tekst op de knop op de homepage |
| `situations.S1.title` | De kop op de situatiepagina |
| `situations.S1.intro` | Korte uitleg (1 tot 3 zinnen) |
| `situations.S1.steps` | De genummerde stappen (een lijst met zinnen) |
| `situations.S1.helpExtra` | Extra regel in het blok "Kom je er niet uit?" |
| `banks.items` | De banken bij S5, elk met `id`, `name` en `steps` |
| `checkin.steps` | De drie stappen van "Zo check je goed in" |
| `help.links` | Links naar officiële bronnen (OVpay, GVB, NS) |
| `footer.disclaimer` | De disclaimer onderaan elke pagina |

Regels die met `TODO` beginnen, krijgen automatisch een gele markering op de
site. Zo zie je meteen wat er nog gecontroleerd moet worden. Zodra je de tekst
vervangt door een gecontroleerde zin, verdwijnt de markering.

Na het aanpassen van een JSON-bestand ververst de dev-server vanzelf. Krijg je
een witte pagina? Dan zit er waarschijnlijk een komma te veel of te weinig in de
JSON. Controleer het met:

```bash
node -e "JSON.parse(require('fs').readFileSync('src/content/nl.json','utf8'))"
```

## Een situatie toevoegen

1. Voeg in `nl.json` en `en.json` een blok toe onder `situations`, bijvoorbeeld `S6`.
2. Zet `"S6"` in `home.order` op de plek waar de knop moet staan.
3. Voeg eventueel een pictogram toe in `src/icons.js` onder de sleutel `S6`.
   Doe je dat niet, dan werkt de knop gewoon zonder pictogram.

## Mappenstructuur

```
index.html              startbestand
src/
  main.js               start de site en kiest de juiste pagina
  router.js             leest de URL (#/nl/s/S1) en maakt links
  styles.css            alle stijlen, mobile first
  icons.js              pictogrammen als inline SVG
  components/layout.js  kop, voet, hulpblok en de paginaomlijsting
  pages/home.js         "Wat is er gebeurd?"
  pages/situation.js    uitleg en stappen per situatie (S1 t/m S5)
  pages/checkin.js      "Zo check je goed in"
  pages/notFound.js     onbekende pagina
  content/nl.json       alle Nederlandse teksten
  content/en.json       alle Engelse teksten
TODO.md                 lijst met teksten die nog gecontroleerd moeten worden
```

## Toegankelijkheid

Richtlijn is WCAG 2.1 niveau AA. Wat er in de code voor gedaan is:

- Mobile first, getest vanaf 360px breed zonder horizontaal scrollen
- Knoppen en links zijn minimaal 48x48px, tekst is minimaal 16px
- Echte links en knoppen, dus alles werkt met het toetsenbord
- Een "ga direct naar de inhoud"-link als eerste tabstop
- Na het navigeren gaat de focus naar de inhoud en springt de pagina naar boven
- Zichtbare focusrand op alles wat je kunt bedienen
- Koppen in de juiste volgorde (h1, dan h2, dan h3)
- `lang` van de pagina verandert mee met de taalkeuze
- Pictogrammen zijn decoratief (`aria-hidden`); de tekst ernaast vertelt alles

Controleer na een grote wijziging met Lighthouse (mobiel) of Accessibility en
Performance nog minimaal 90 scoren.

## Deployen

De site is statisch. Na `npm run build` staat alles in `dist/`.

- **Netlify:** build command `npm run build`, publish directory `dist`.
- **GitHub Pages:** upload de inhoud van `dist/` naar de branch of map die je
  voor Pages gebruikt. `vite.config.js` gebruikt `base: './'`, dus de site werkt
  ook in een submap.

## Inhoud en bronnen

In de content staat bewust **geen verzonnen feitelijke informatie** over OVpay,
tarieven, termijnen of hoe bank-apps werken. Overal waar een feit nodig is, staat
een `TODO` die wij zelf controleren en invullen. Zie `TODO.md` voor het complete
overzicht.
