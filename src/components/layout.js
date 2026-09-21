import { path, pathInOtherLang } from '../router.js'

/** Maakt tekst veilig om in HTML te zetten. */
export function esc(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Blok "Let op" met een korte extra mededeling. */
export function note(t, text) {
  if (!text) return ''
  return `
    <aside class="note">
      <h2 class="note-title">${esc(t.common.noteTitle)}</h2>
      <p>${esc(text)}</p>
    </aside>`
}

/** Knoppen naar de plek waar je iets echt regelt (bijvoorbeeld je reisoverzicht). */
export function actionLinks(t, links = []) {
  if (!links.length) return ''
  const items = links
    .map(
      (l) => `<li>
        <a class="button-primary" href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">
          ${esc(l.label)}
          <span class="visually-hidden"> (${esc(t.common.openInNewTab)})</span>
          <span class="external" aria-hidden="true">↗</span>
        </a>
      </li>`
    )
    .join('')
  return `<ul class="action-list">${items}</ul>`
}

/** Kop van de site: naam, taalschakelaar en (behalve op de homepage) een terugknop. */
export function header(t, route) {
  const otherLang = t.meta.otherLangCode
  const isHome = route.name === 'home'
  return `
    <header class="site-header">
      <div class="bar">
        <a class="brand" href="${path(route.lang, 'home')}">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" focusable="false"><path d="M8 17l5.5 5.5L24 11"/></svg>
          </span>
          <span class="brand-text">
            <span class="brand-name">${esc(t.site.name)}</span>
            <span class="brand-tagline">${esc(t.site.tagline)}</span>
          </span>
        </a>
        <a class="lang-switch" href="${pathInOtherLang(route, otherLang)}" lang="${otherLang}"
           hreflang="${otherLang}" title="${esc(t.meta.switchTo)}">
          <span class="visually-hidden">${esc(t.meta.switchTo)}</span>
          <span aria-hidden="true">${esc(t.meta.otherLangShort)}</span>
        </a>
      </div>
      ${isHome ? '' : `
      <nav class="subnav" aria-label="${esc(t.nav.home)}">
        <button type="button" class="linkish" data-action="back">
          <span aria-hidden="true">←</span> ${esc(t.nav.back)}
        </button>
        <a class="linkish" href="${path(route.lang, 'home')}">${esc(t.nav.home)}</a>
      </nav>`}
    </header>`
}

/** Voet van de site met de verplichte disclaimer. */
export function footer(t) {
  return `
    <footer class="site-footer">
      <p class="disclaimer">${esc(t.footer.disclaimer)}</p>
      <p>${esc(t.footer.project)}</p>
      <p>${esc(t.footer.privacy)}</p>
    </footer>`
}

/** Blok "Kom je er niet uit?" met telefoonnummer, servicepunt en officiele bronnen. */
export function helpBlock(t, extra = '') {
  const links = t.help.links
    .map(
      (l) => `<li>
        <a href="${esc(l.url)}" rel="noopener noreferrer" target="_blank">
          ${esc(l.label)}<span class="visually-hidden"> (${esc(t.common.openInNewTab)})</span>
          <span class="external" aria-hidden="true">↗</span>
        </a>
      </li>`
    )
    .join('')
  return `
    <section class="card help" aria-labelledby="help-title">
      <h2 id="help-title">${esc(t.common.helpTitle)}</h2>
      <p>${esc(t.help.text)}</p>
      ${extra ? `<p>${esc(extra)}</p>` : ''}
      <p>${esc(t.help.servicePoint)}</p>
      <h3>${esc(t.common.sourcesTitle)}</h3>
      <ul class="link-list">${links}</ul>
      <p class="source-note">${esc(t.common.sourceNote)}</p>
    </section>`
}

/** Zet de hele pagina in elkaar. */
export function page(t, route, main) {
  return `
    <a class="skip-link" href="#main">${esc(t.nav.skip)}</a>
    ${header(t, route)}
    <main id="main" class="content" tabindex="-1">${main}</main>
    ${footer(t)}`
}
