import type { Ontology, OntologyClass, OntologyProperty } from './types'

/**
 * Indices y consultas sobre la ontologia. Todo es puro para poder probarlo sin la vista.
 */

export interface OntologyIndex {
  classes: Map<string, OntologyClass>
  properties: Map<string, OntologyProperty>
  children: Map<string, string[]>
  roots: string[]
}

export function buildIndex(ontology: Ontology): OntologyIndex {
  const classes = new Map(ontology.classes.map((c) => [c.id, c]))
  const properties = new Map(ontology.properties.map((p) => [p.id, p]))
  const children = new Map<string, string[]>()

  for (const c of ontology.classes) {
    for (const parent of c.parents) {
      if (!classes.has(parent)) continue
      const list = children.get(parent) ?? []
      list.push(c.id)
      children.set(parent, list)
    }
  }

  const byLabel = (a: string, b: string) =>
    (classes.get(a)?.label ?? a).localeCompare(classes.get(b)?.label ?? b, 'es')
  for (const list of children.values()) list.sort(byLabel)

  // Raiz: sin padre dentro de la ontologia. Una clase con varios padres aparece bajo cada uno.
  const roots = ontology.classes
    .filter((c) => !c.parents.some((p) => classes.has(p)))
    .map((c) => c.id)
    .sort(byLabel)

  return { classes, properties, children, roots }
}

/** Cadena de antecesores de la clase hasta una raiz, siguiendo siempre el primer padre. */
export function ancestors(index: OntologyIndex, id: string): string[] {
  const path: string[] = []
  const seen = new Set<string>([id])
  let current = index.classes.get(id)
  while (current) {
    const parent = current.parents.find((p) => index.classes.has(p) && !seen.has(p))
    if (!parent) break
    path.unshift(parent)
    seen.add(parent)
    current = index.classes.get(parent)
  }
  return path
}

/**
 * Propiedades aplicables a la clase: las suyas y las de todos sus antecesores, cada una con la
 * clase de la que viene. Se recorre por anchura y sin repetir, porque hay herencia multiple.
 */
export function effectiveProperties(
  index: OntologyIndex,
  id: string,
): { property: OntologyProperty; from: string }[] {
  const result: { property: OntologyProperty; from: string }[] = []
  const seenProps = new Set<string>()
  const seenClasses = new Set<string>()
  const queue = [id]

  while (queue.length) {
    const classId = queue.shift() as string
    if (seenClasses.has(classId)) continue
    seenClasses.add(classId)
    const c = index.classes.get(classId)
    if (!c) continue
    for (const propId of c.properties) {
      const property = index.properties.get(propId)
      if (!property || seenProps.has(propId)) continue
      seenProps.add(propId)
      result.push({ property, from: classId })
    }
    queue.push(...c.parents)
  }

  return result
}

export function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

/** Clases que casan con el texto por nombre en castellano, en ingles o identificador. */
export function searchClasses(index: OntologyIndex, query: string): OntologyClass[] {
  const q = normalize(query)
  if (!q) return []
  return [...index.classes.values()]
    .filter((c) => [c.label, c.labelEn, c.id].some((v) => normalize(v).includes(q)))
    .sort((a, b) => a.label.localeCompare(b.label, 'es'))
}
