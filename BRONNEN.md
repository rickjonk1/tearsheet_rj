# Bronnen en verantwoording

Alle feitelijke informatie in `src/content/nl.json` en `src/content/en.json` is
opgezocht bij de officiële websites van OVpay en de vervoerders.
**Laatst gecontroleerd: 21 september 2026.**

Regels, bedragen en openingstijden veranderen. Controleer ze opnieuw voordat je
de site oplevert of laat zien tijdens een test met gebruikers.

## Gebruikte bronnen

| # | Bron | URL |
|---|------|-----|
| B1 | OVpay - reisoverzicht (reis opzoeken met referentienummer) | https://reisoverzicht.ovpay.nl/ |
| B2 | OVpay - service en contact | https://www.ovpay.nl/service-contact |
| B3 | OVpay - storingen | https://www.ovpay.nl/storingen |
| B4 | NS - inchecken of uitchecken vergeten | https://www.ns.nl/service-en-contact/geld-terug/inchecken-of-uitchecken-vergeten |
| B5 | NS - afschrijving met NLOV (Engelstalig) | https://www.ns.nl/en/service-and-contact/refund/withdrawal-nlov |
| B6 | GVB - in- of uitcheck gemist | https://www.gvb.nl/klantenservice/uitcheck-gemist |
| B7 | GVB - service- en ticketlocaties | https://www.gvb.nl/klantenservice/service-en-tickets-locaties |
| B8 | HTM - OVpay veelgestelde vragen | https://www.htm.nl/reisproducten/ovpay/ovpay-veelgestelde-vragen/ |
| B9 | HTM - OVpay geld terugvragen | https://www.htm.nl/reisproducten/ovpay/ovpay-geld-terug/ |
| B10 | SeniorWeb - reiskosten bekijken na inchecken met betaalpas | https://www.seniorweb.nl/artikel/reiskosten-bekijken-na-inchecken-met-betaalpas |

## Feiten en waar ze vandaan komen

| Feit in de content | Bron |
|---|---|
| Het referentienummer (betalingskenmerk) begint met NLOV en staat bij de afschrijving in je bank-app | B5, B10 |
| Je zoekt je reis op met het referentienummer en het afgeschreven bedrag, via "Reis zoeken" | B1, B4, B10 |
| Een reis staat meestal een dag na het uitchecken op je bankafschrift | B10 |
| Je kunt tot 6 uur na het inchecken alsnog uitchecken bij een poortje of paaltje | B4 |
| Een gemiste in- of uitcheck aanpassen kan vanaf 6 uur na de reis | B4, B6, B8 |
| Aanpassen kan tot 60 dagen na de rit | B6, B8 |
| Bij de trein mag dit maximaal 3 keer per kalenderjaar | B4 |
| Bij bus, tram en metro maximaal 3 keer per half jaar | B6 |
| Te veel betaald geld staat binnen 5 dagen op je rekening | B4, B6 |
| Bij een gemiste check bij GVB geldt €4,00 (voltarief); in de trein een hoger correctie- of instaptarief | B4, B6, B8 |
| GVB-reizen pas je aan via ovpay.gvb.nl/mijn-gvb/reishistorie, andere vervoerders via het OVpay-reisoverzicht | B6 |
| Je hele portemonnee tegen de lezer houden kan meerdere passen tegelijk laten inchecken | B8, B9 |
| Klantenservice OVpay: 0900-1433, werkdagen 07:00-17:00, vanuit het buitenland +31 10 892 5063 | B5 |
| Je kunt binnen 100 seconden opnieuw scannen om te controleren of je incheck is gelukt | B4 |
| In de OVpay-app zie je je reizen tot 18 maanden terug | B10 |
| Een openstaand bedrag kan je pas blokkeren voor het OV | B2 |
| GVB Tickets & Info Amsterdam Centraal: ma-vr 08:00-20:00, za-zo 08:30-19:00, tegenover de hoofdingang | B7 |

## Aannames (nog niet met een bron bevestigd)

Deze teksten zijn geschreven op basis van hoe het in de praktijk werkt, maar
staan niet letterlijk zo op een officiële site. Controleer ze zelf, of pas ze aan
na een test met gebruikers.

1. **Stappen per bank-app** (`banks.items` in de contentbestanden). De
   schermnamen per bank (Omschrijving, Mededeling, Details) zijn aannemelijk,
   maar niet per app geverifieerd. Onder de stappen staat daarom een zin dat
   bank-apps regelmatig veranderen.
2. **"Wacht tot je een piep hoort en een groen teken ziet"** op de pagina
   "Zo check je goed in". Het signaal verschilt per type kaartlezer.
3. **NS Tickets & Service in de stationshal** van Amsterdam Centraal. Dat er een
   balie is, klopt; de openingstijden noemen we bewust niet omdat die per dag
   verschillen.
4. **"Reken op een paar dagen"** bij het terugkrijgen van een dubbele
   afschrijving. Voor een gemiste uitcheck noemen de bronnen 5 dagen; voor een
   dubbele afschrijving is geen officiële termijn gevonden.
