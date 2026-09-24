import type { FaqEntry, HelpSection } from './content'

/** Busqueda de la ayuda: sin distinguir mayusculas ni tildes y exigiendo todos los terminos. */
export function normalize(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

function terms(query: string): string[] {
  return normalize(query).split(/\s+/).filter(Boolean)
}

function matches(haystack: string, words: string[]): boolean {
  const text = normalize(haystack)
  return words.every((word) => text.includes(word))
}

export function sectionText(section: HelpSection): string {
  return [
    section.title,
    ...section.paragraphs,
    ...(section.items ?? []).flatMap((item) => [item.term, item.text]),
    ...(section.links ?? []).map((link) => link.label),
  ].join(' ')
}

export function filterSections(sections: HelpSection[], query: string): HelpSection[] {
  const words = terms(query)
  return words.length ? sections.filter((s) => matches(sectionText(s), words)) : sections
}

export function filterFaq(entries: FaqEntry[], query: string): FaqEntry[] {
  const words = terms(query)
  return words.length ? entries.filter((e) => matches(`${e.question} ${e.answer}`, words)) : entries
}
