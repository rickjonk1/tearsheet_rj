import './styles.css'
import nl from './content/nl.json'
import en from './content/en.json'
import { parseRoute, path } from './router.js'
import { page } from './components/layout.js'
import { homePage } from './pages/home.js'
import { situationPage } from './pages/situation.js'
import { checkinPage } from './pages/checkin.js'
import { notFoundPage } from './pages/notFound.js'

const CONTENT = { nl, en }
const app = document.querySelector('#app')

// Onthoudt of we al eens gerenderd hebben. Bij de eerste keer verplaatsen we
// de focus niet, anders springt de pagina meteen naar beneden.
let firstRender = true

function render() {
  const route = parseRoute()
  const t = CONTENT[route.lang] || CONTENT.nl

  let main
  if (route.name === 'home') main = homePage(t, route)
  else if (route.name === 'checkin') main = checkinPage(t, route)
  else if (route.name === 'situation') main = situationPage(t, route)
  if (!main) main = notFoundPage(t, route)

  app.innerHTML = page(t, route, main)

  // Taal en titel van het document bijwerken, zodat screenreaders
  // de juiste uitspraak gebruiken.
  document.documentElement.lang = t.meta.htmlLang
  const h1 = app.querySelector('h1')
  document.title = h1 ? `${h1.textContent.trim()} – ${t.meta.title}` : t.meta.title

  if (!firstRender) {
    // Na navigatie naar boven en de focus in de inhoud zetten.
    window.scrollTo(0, 0)
    app.querySelector('#main')?.focus()
  }
  firstRender = false
}

// De terugknop gebruikt de geschiedenis van de browser.
// Is die er niet (iemand opent de pagina direct), dan gaan we naar home.
app.addEventListener('click', (event) => {
  const back = event.target.closest('[data-action="back"]')
  if (!back) return
  if (window.history.length > 1) window.history.back()
  else window.location.hash = path(parseRoute().lang, 'home')
})

window.addEventListener('hashchange', render)

// Zonder hash beginnen we op de Nederlandse homepage.
if (!window.location.hash) window.location.replace(`#/nl/`)
render()
