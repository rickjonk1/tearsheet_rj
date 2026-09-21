// Zoekt alle TODO-teksten in de contentbestanden en print ze als Markdown.
// Gebruik: npm run todo > TODO.md
import { readFileSync } from 'node:fs'

const FILES = [
  ['Nederlands', 'src/content/nl.json'],
  ['Engels', 'src/content/en.json']
]

/** Loopt door het JSON-object heen en verzamelt elke tekst met TODO erin. */
function findTodos(value, path = '') {
  if (typeof value === 'string') {
    return value.includes('TODO') ? [{ path, text: value }] : []
  }
  if (Array.isArray(value)) {
    return value.flatMap((v, i) => findTodos(v, `${path}[${i}]`))
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([k, v]) => findTodos(v, path ? `${path}.${k}` : k))
  }
  return []
}

let out = '# TODO: teksten die nog gecontroleerd moeten worden\n\n'
out += 'Dit bestand is gegenereerd met `npm run todo`. Pas de teksten aan in\n'
out += '`src/content/nl.json` en `src/content/en.json` en draai het commando opnieuw.\n'

let total = 0
for (const [label, file] of FILES) {
  const todos = findTodos(JSON.parse(readFileSync(file, 'utf8')))
  total += todos.length
  out += `\n## ${label} (\`${file}\`) - ${todos.length} regels\n\n`
  out += '| Plek in het bestand | Tekst |\n|---|---|\n'
  for (const t of todos) {
    out += `| \`${t.path}\` | ${t.text.replace(/\|/g, '\\|')} |\n`
  }
}
out += `\n**Totaal: ${total} regels.**\n`
process.stdout.write(out)
