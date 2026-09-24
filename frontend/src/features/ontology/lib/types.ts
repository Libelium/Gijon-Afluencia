/** Forma de `data/segittur.json`, generado por `frontend/scripts/segittur-to-json.py`. */

export interface OntologyMeta {
  title: string
  description: string
  version: string
  versionIri: string
  issued: string
  rights: string
  namespace: string
  source: string
}

export interface OntologyClass {
  id: string
  uri: string
  label: string
  labelEn: string
  comment: string
  parents: string[]
  /** Propiedades cuyo dominio declara esta clase (no incluye las heredadas). */
  properties: string[]
}

export interface OntologyProperty {
  id: string
  uri: string
  kind: 'datatype' | 'object'
  label: string
  comment: string
  domain: string[]
  range: string[]
}

export interface SkosConcept {
  uri: string
  label: string
}

export interface SkosScheme {
  id: string
  uri: string
  label: string
  concepts: SkosConcept[]
}

export interface Ontology {
  meta: OntologyMeta
  classes: OntologyClass[]
  properties: OntologyProperty[]
  schemes: SkosScheme[]
}
