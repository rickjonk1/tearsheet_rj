// Kleine router op basis van de hash in de URL (#/nl/s/S1).
// Met een hash werkt de site ook als statisch bestand, zonder server-instellingen.

export const LANGS = ['nl', 'en']
export const DEFAULT_LANG = 'nl'

/**
 * Leest de huidige hash en geeft een simpel route-object terug.
 * Voorbeelden:
 *   #/nl/            -> { lang: 'nl', name: 'home' }
 *   #/en/s/S1        -> { lang: 'en', name: 'situation', id: 'S1' }
 *   #/nl/s/S5/ing    -> { lang: 'nl', name: 'situation', id: 'S5', bank: 'ing' }
 *   #/nl/checkin     -> { lang: 'nl', name: 'checkin' }
 */
export function parseRoute(hash = window.location.hash) {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  const lang = LANGS.includes(parts[0]) ? parts[0] : DEFAULT_LANG
  const rest = LANGS.includes(parts[0]) ? parts.slice(1) : parts

  if (rest.length === 0) return { lang, name: 'home' }
  if (rest[0] === 's' && rest[1]) {
    return { lang, name: 'situation', id: rest[1].toUpperCase(), bank: rest[2] || null }
  }
  if (rest[0] === 'checkin') return { lang, name: 'checkin' }
  return { lang, name: 'notfound' }
}

/** Bouwt een link (href) voor een pagina in een bepaalde taal. */
export function path(lang, name, id = null, bank = null) {
  if (name === 'home') return `#/${lang}/`
  if (name === 'checkin') return `#/${lang}/checkin`
  if (name === 'situation') return `#/${lang}/s/${id}${bank ? '/' + bank : ''}`
  return `#/${lang}/`
}

/** Zelfde pagina, andere taal. Zo blijft de gebruiker waar hij is. */
export function pathInOtherLang(route, otherLang) {
  return path(otherLang, route.name, route.id, route.bank)
}
