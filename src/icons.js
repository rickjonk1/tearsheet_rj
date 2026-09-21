// Eenvoudige pictogrammen als inline SVG. Ze zijn decoratief:
// de tekst ernaast vertelt al wat de knop doet, dus aria-hidden="true".

const wrap = (inner) =>
  `<svg class="icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">${inner}</svg>`

export const icons = {
  // Twee passen tegen elkaar: dubbel betaald
  S1: wrap(`<rect x="5" y="12" width="26" height="17" rx="3"/><rect x="17" y="19" width="26" height="17" rx="3"/><path d="M17 25h26"/>`),
  // Klok met pijl: vergeten uit te checken
  S2: wrap(`<circle cx="24" cy="24" r="17"/><path d="M24 14v10l7 5"/>`),
  // Poortje met kruis
  S3: wrap(`<path d="M10 8v32M38 8v32"/><path d="M18 18l12 12M30 18L18 30"/>`),
  // Pas met vraagteken
  S4: wrap(`<rect x="6" y="12" width="36" height="24" rx="3"/><path d="M6 20h36"/><path d="M21 29c0-3 5-3 5-6a2.6 2.6 0 0 0-5-.6"/><path d="M23.5 33.2h.02"/>`),
  // Telefoon met bonnetje: reis controleren
  S5: wrap(`<rect x="13" y="5" width="22" height="38" rx="4"/><path d="M19 15h10M19 22h10M19 29h6"/>`),
  // Stappen op de "zo check je goed in"-pagina
  wallet: wrap(`<rect x="5" y="12" width="38" height="26" rx="4"/><path d="M5 20h38"/><circle cx="35" cy="29" r="2.5"/>`),
  reader: wrap(`<rect x="9" y="6" width="30" height="36" rx="4"/><circle cx="24" cy="22" r="7"/><path d="M24 12v3M24 29v3"/>`),
  checkout: wrap(`<path d="M8 25l10 10L40 13"/>`)
}

export function icon(name) {
  return icons[name] || ''
}
