import { esc, helpBlock } from '../components/layout.js'
import { path } from '../router.js'
import { icon } from '../icons.js'

/** Zet een lijst met stappen om in genummerde stappen. TODO-regels krijgen een eigen stijl. */
function stepList(steps) {
  const items = steps
    .map((step, i) => {
      const isTodo = step.trim().startsWith('TODO')
      return `<li${isTodo ? ' class="todo-step"' : ''}>
        <span class="step-number" aria-hidden="true">${i + 1}</span>
        <span class="step-text">${esc(step)}</span>
      </li>`
    })
    .join('')
  return `<ol class="steps">${items}</ol>`
}

/** Extra blok bij S5: optioneel je bank kiezen voor specifieke stappen. */
function bankBlock(t, route) {
  const chosen = t.banks.items.find((b) => b.id === route.bank)
  const options = t.banks.items
    .map(
      (b) => `<li>
        <a class="bank ${b.id === route.bank ? 'is-active' : ''}"
           href="${path(route.lang, 'situation', route.id, b.id)}"
           ${b.id === route.bank ? 'aria-current="true"' : ''}>${esc(b.name)}</a>
      </li>`
    )
    .join('')

  return `
    <section class="card banks" aria-labelledby="banks-title">
      <h2 id="banks-title">${esc(t.banks.title)}</h2>
      <p>${esc(t.banks.intro)}</p>
      <ul class="bank-list">${options}</ul>
      ${
        chosen
          ? `<div class="bank-steps">
               <h3>${esc(t.banks.stepsTitle)}: ${esc(chosen.name)}</h3>
               ${stepList(chosen.steps)}
               <a class="linkish" href="${path(route.lang, 'situation', route.id)}">${esc(t.banks.backToGeneral)}</a>
             </div>`
          : ''
      }
    </section>`
}

/** Onderaan: door naar een andere situatie, zonder terug naar home te hoeven. */
function otherSituations(t, route) {
  const items = t.home.order
    .filter((id) => id !== route.id)
    .map(
      (id) => `<li><a class="linkish" href="${path(route.lang, 'situation', id)}">${esc(t.situations[id].button)}</a></li>`
    )
    .join('')
  return `
    <section class="others" aria-labelledby="others-title">
      <h2 id="others-title">${esc(t.common.situationsTitle)}</h2>
      <ul class="other-list">${items}</ul>
    </section>`
}

export function situationPage(t, route) {
  const s = t.situations[route.id]
  if (!s) return null

  return `
    <div class="situation-head">
      ${icon(route.id)}
      <h1>${esc(s.title)}</h1>
    </div>
    <p class="lead">${esc(s.intro)}</p>
    <h2>${esc(t.common.stepsTitle)}</h2>
    ${stepList(s.steps)}
    ${route.id === 'S5' ? bankBlock(t, route) : ''}
    ${helpBlock(t, s.helpExtra)}
    ${otherSituations(t, route)}`
}
