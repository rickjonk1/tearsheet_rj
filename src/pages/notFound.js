import { esc } from '../components/layout.js'
import { path } from '../router.js'

export function notFoundPage(t, route) {
  return `
    <h1>${esc(t.notFound.title)}</h1>
    <p class="lead">${esc(t.notFound.text)}</p>
    <p><a class="button-secondary" href="${path(route.lang, 'home')}">${esc(t.notFound.link)}</a></p>`
}
