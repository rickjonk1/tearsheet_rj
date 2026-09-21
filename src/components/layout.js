import { path, pathInOtherLang } from '../router.js'

/** Maakt tekst veilig om in HTML te zetten. */
export function esc(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Kop van de site: naam, taalschakelaar en (optioneel) een terugknop. */
export function header(t, route) {
  const otherLang = t.meta.otherLangCode
  const isHome = route.name === 'home'
  return `
    <header class="site-header">
      <div class="bar">
        <a class="brand" href="${path(route.lang, 'home')}">
          <span class="brand-mark" aria-hidden="true">✓</span>
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
      <p class="disclaimer"><strong>${esc(t.footer.disclaimer)}</strong></p>
      <p>${esc(t.footer.project)}</p>
      <p>${esc(t.footer.privacy)}</p>
    </footer>`
}

/** Blok "Kom je er niet uit?" met verwijzingen naar officiele bronnen. */
export function helpBlock(t, extra = '') {
  const links = t.help.links
    .map(
      (l) => `<li>
        <a href="${esc(l.url)}" rel="noopener noreferrer" target="_blank">
          ${esc(l.label)}<span class="visually-hidden"> (${esc(t.common.openInNewTab)})</span>
        </a>
        ${l.note ? `<span class="todo">${esc(l.note)}</span>` : ''}
      </li>`
    )
    .join('')
  return `
    <section class="card help" aria-labelledby="help-title">
      <h2 id="help-title">${esc(t.common.helpTitle)}</h2>
      <p>${esc(t.help.text)}</p>
      ${extra ? `<p class="todo">${esc(extra)}</p>` : ''}
      <p class="todo">${esc(t.help.servicePoint)}</p>
      <h3>${esc(t.common.sourcesTitle)}</h3>
      <ul class="link-list">${links}</ul>
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
