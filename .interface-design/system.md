# Roadbook — design system

The product is a directeur sportif's **season roadbook**: the printed race bible on
the passenger seat. Not a dashboard. Every decision follows from that.

## Direction & feel
Paper and print ink. Quiet, dense, document-like — something you fill in, not a
control panel. Warm throughout: the paper is warm off-white, the ink is warm
near-black, never `#000`.

## Depth strategy — BORDERS ONLY
Hairline warm rules. **No shadows** anywhere except a single soft lift on
popovers. Print has no drop shadows. Do not mix in shadow elevation.

## Colour — a legend, never decoration
~60/30/10: paper dominates, ink builds structure, colour only *classifies*.
- `--maillot #f0c000` grand tours / GC
- `--pois #c8102e` mountains
- `--vert #00843d` sprint
- `--pave #54636f` cobbled classics
- `--azzurro #2f6fb0` time trial / camps

The primary action colour is **ink itself** (black button). Jersey colours are
reserved for race classification and must never be used for buttons or emphasis.

## Typography — three families, three jobs
- `--serif` Georgia — identity: rider names, race names, headings. Weight 400.
- `--mono` — every number, date, label, kicker. All numerics `tabular-nums`.
- `--sans` — controls only.
All ship with the OS, so the app works offline.

Hierarchy comes from weight + colour + family, not size alone. Kickers are
10px mono, `.16em` tracking, uppercase, `--ink-3`.

## Text hierarchy — four levels
`--ink` primary · `--ink-2` supporting · `--ink-3` metadata · `--ink-4` disabled.

## Spacing & density
Base unit 4px. Roadbook row height 42px. Panel padding 16–24px. Rail 264px,
editor 340px (the rail serves, the editor is a peer of the calendar).

## Radius scale
`--r-mark 2px` (dossards) · `--r-ctl 3px` (buttons/inputs) · `--r-card 6px`
(panels) · `--r-sheet 10px` (overlays). Never large radius on small elements.

## Signature elements (must appear)
1. **Dossard** — a rider's race number in a bordered mono box; the leader carries 1.
   Replaces avatars/initials entirely.
2. **Jersey edge** — a 3px left rule on every race, coloured by classification.
3. **Elevation sawtooth** — inline SVG profile drawn from the race's own climbing
   weights (`Career.race_profile`). Appears in the calendar and editor header.
4. **Roadbook abbreviation** — races shorten to how people actually say them
   (Roubaix, Vlaanderen, Sanremo, Luik). Never truncate mid-word with an ellipsis.
5. **Team-sheet marks** — short mono abbreviations for actions (HOOG, VERK, DOEL)
   instead of icons.

## Banned
- Emoji as iconography. Star ratings (★) for camps are allowed — they are a real
  roadbook notation.
- Neon accents, gradients, glows, radial background washes.
- Multiple accent colours for emphasis.
- `transition: all`; animate only transform/opacity.

## Component measurements
- `Button` — 32px h · 0 12px pad · 3px radius · 13px/500 · 1px `--rule-2` border.
  `.primary` is ink-on-paper. `.ghost` has a transparent border until hover.
- `Dossard` — 24×22px min · 1px `--rule-3` · 2px radius · 11.5px mono 600.
  `.lead` uses a 1.5px ink border.
- `Race row (calendar)` — grid `52px 42px 1fr auto auto`, 42px min height,
  jersey edge inset 6px. `.major` (popularity ≥ 70) gets a 17px name and 4px edge.
- `Planner cell chip` — 11.5px serif name + 9.5px mono day, 2.5px jersey edge.
- `Popover` — 292px wide, 6px padding, `--card` background, one soft lift.

## Motion
Enter `cubic-bezier(.23,1,.32,1)`, 120–200ms. Press `scale(.98)`.
`prefers-reduced-motion` drops movement.
