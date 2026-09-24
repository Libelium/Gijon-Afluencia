/**
 * Markdown minimo para las descripciones de la especificacion: parrafos, listas, negrita,
 * cursiva y codigo en linea. El texto se escapa ANTES de dar formato, asi que ninguna etiqueta
 * del origen llega al HTML; aun asi la vista vuelve a sanear con DOMPurify antes de `v-html`.
 */

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function inline(text: string): string {
  // El codigo va primero y se aparta, para que un `**` dentro de el no se lea como negrita.
  const codes: string[] = []
  let out = escapeHtml(text).replace(/`([^`]+)`/g, (_, code: string) => {
    codes.push(code)
    return `\uE000${codes.length - 1}\uE000`
  })
  out = out
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>')
  return out.replace(/\uE000(\d+)\uE000/g, (_, i: string) => `<code>${codes[Number(i)]}</code>`)
}

const ORDERED = /^\s*\d+\.\s+/
const UNORDERED = /^\s*[-*]\s+/

export function renderMarkdown(source: string): string {
  const blocks = source.replace(/\r\n/g, '\n').trim().split(/\n\s*\n/)
  return blocks
    .filter((block) => block.trim())
    .map((block) => {
      const lines = block.split('\n')
      if (lines.every((line) => ORDERED.test(line))) {
        return `<ol>${lines.map((l) => `<li>${inline(l.replace(ORDERED, ''))}</li>`).join('')}</ol>`
      }
      if (lines.every((line) => UNORDERED.test(line))) {
        return `<ul>${lines.map((l) => `<li>${inline(l.replace(UNORDERED, ''))}</li>`).join('')}</ul>`
      }
      return `<p>${inline(lines.join(' ').trim())}</p>`
    })
    .join('')
}
