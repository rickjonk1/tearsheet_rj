import { esc, helpBlock } from '../components/layout.js'
import { path } from '../router.js'
import { icon } from '../icons.js'

const STEP_ICONS = ['wallet', 'reader', 'checkout']

// Pagina "Zo check je goed in" met drie vaste stappen.
export function checkinPage(t, route) {
  const steps = t.checkin.steps
    .map(
      (step, i) => `
      <li>
        <span class="step-number" aria-hidden="true">${i + 1}</span>
        <div class="step-body">
          ${icon(STEP_ICONS[i])}
          <h2>${esc(step.title)}</h2>
          <p>${esc(step.text)}</p>
        </div>
      </li>`
    )
    .join('')

  return `
    <h1>${esc(t.checkin.title)}</h1>
    <p class="lead">${esc(t.checkin.intro)}</p>
    <ol class="steps steps-big">${steps}</ol>
    <p class="todo">${esc(t.checkin.note)}</p>
    ${helpBlock(t)}
    <p><a class="button-secondary" href="${path(route.lang, 'home')}">${esc(t.checkin.backLink)}</a></p>`
}
