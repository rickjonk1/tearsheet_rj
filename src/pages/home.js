import { esc } from '../components/layout.js'
import { path } from '../router.js'
import { icon } from '../icons.js'

// Homepage: meteen de vraag "Wat is er gebeurd?" met grote knoppen.
export function homePage(t, route) {
  const buttons = t.home.order
    .map((id) => {
      const s = t.situations[id]
      if (!s) return ''
      return `
        <li>
          <a class="choice" href="${path(route.lang, 'situation', id)}">
            ${icon(id)}
            <span class="choice-text">${esc(s.button)}</span>
            <span class="choice-arrow" aria-hidden="true">→</span>
          </a>
        </li>`
    })
    .join('')

  return `
    <h1>${esc(t.home.title)}</h1>
    <p class="lead">${esc(t.home.intro)}</p>
    <ul class="choice-list">${buttons}</ul>
    <section class="card tip" aria-labelledby="tip-title">
      <h2 id="tip-title">${esc(t.home.checkinCardTitle)}</h2>
      <p>${esc(t.home.checkinCardText)}</p>
      <a class="button-secondary" href="${path(route.lang, 'checkin')}">${esc(t.home.checkinCardLink)}</a>
    </section>`
}
