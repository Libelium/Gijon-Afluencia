import { describe, expect, it } from 'vitest'
import data from '../data/segittur.json'
import { ancestors, buildIndex, effectiveProperties, normalize, searchClasses } from './ontology'
import { DESTINATION, PIT_PROPERTIES, PITS, SITE, mappedClassIds, pitsByClass } from './mapping'
import type { Ontology } from './types'

const ontology = data as Ontology
const index = buildIndex(ontology)

describe('buildIndex', () => {
  it('carga las 272 clases de la version publicada', () => {
    expect(index.classes.size).toBe(272)
    expect(ontology.meta.version).toBe('1.2.0')
  })

  it('cuelga cada clase de sus padres', () => {
    expect(index.children.get('HistoricalOrCulturalResource')).toContain('Square')
    expect(index.children.get('HistoricalOrCulturalResource')).toContain('Church')
  })

  it('las raices no tienen padre dentro de la ontologia', () => {
    for (const id of index.roots) {
      const c = index.classes.get(id)!
      expect(c.parents.some((p) => index.classes.has(p))).toBe(false)
    }
  })
})

describe('ancestors', () => {
  it('recorre la jerarquia hasta la raiz', () => {
    const path = ancestors(index, 'Square')
    expect(path.at(-1)).toBe('HistoricalOrCulturalResource')
    expect(path.length).toBeGreaterThanOrEqual(1)
  })
})

describe('effectiveProperties', () => {
  it('una plaza hereda el aforo de su clase padre', () => {
    const props = effectiveProperties(index, 'Square')
    const capacity = props.find((p) => p.property.id === 'capacity')
    expect(capacity?.from).toBe('HistoricalOrCulturalResource')
  })

  it('no repite propiedades con herencia multiple', () => {
    const ids = effectiveProperties(index, 'BullRing').map((p) => p.property.id)
    expect(new Set(ids).size).toBe(ids.length)
  })
})

describe('searchClasses', () => {
  it('encuentra sin tildes ni mayusculas, en castellano o en ingles', () => {
    expect(searchClasses(index, 'IGLESIA').map((c) => c.id)).toContain('Church')
    expect(searchClasses(index, 'square').map((c) => c.id)).toContain('Square')
    expect(searchClasses(index, 'informacion turistica').map((c) => c.id)).toContain(
      'TemporaryTouristInformationPoint',
    )
  })

  it('una busqueda vacia no devuelve nada', () => {
    expect(searchClasses(index, '  ')).toEqual([])
    expect(normalize('  Plazá ')).toBe('plaza')
  })
})

describe('correspondencia con la plataforma', () => {
  it('todas las clases usadas existen en la ontologia', () => {
    for (const id of mappedClassIds()) expect(index.classes.has(id), id).toBe(true)
  })

  it('todas las propiedades usadas existen en la ontologia', () => {
    const used = [...PIT_PROPERTIES, ...(DESTINATION.properties ?? []), ...(SITE.properties ?? [])]
    for (const { property } of used) expect(index.properties.has(property), property).toBe(true)
  })

  it('el aforo es aplicable a todos los PIT', () => {
    for (const pit of PITS) {
      const ids = effectiveProperties(index, pit.classId).map((p) => p.property.id)
      expect(ids, pit.zoneId).toContain('capacity')
    }
  })

  it('cubre los 14 PIT sin repetir zona', () => {
    expect(PITS).toHaveLength(14)
    expect(new Set(PITS.map((p) => p.zoneId)).size).toBe(14)
    expect([...pitsByClass().values()].reduce((a, b) => a + b, 0)).toBe(14)
  })
})
