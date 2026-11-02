import { describe, expect, it } from 'vitest'
import type { EntityRef } from '@/types'
import { datamodelOf } from '../contract'
import type { Point } from '../shared/types'
import { buildPairs, flowEntityUrns, nodeIdOf } from './pairs'
import { pairSeriesOptions } from './useTransits'

const FLOW = datamodelOf('flowEvent')
const OBSERVED = datamodelOf('flowObserved')

/** Espacio de los sensores y espacio donde la plataforma publica los tránsitos. */
const SENSORS = { tenant: 'sensores', scope: '/' }
const PLATFORM = { tenant: 'plataforma', scope: '/' }

let nextId = 1

function point(
  datamodel: string,
  tail: string,
  { space = SENSORS, label = tail, lat = null, lon = null }: { space?: typeof SENSORS; label?: string; lat?: number | null; lon?: number | null } = {},
): Point {
  const urn = `urn:ngsi-ld:${datamodel}:${tail}`
  const ref: EntityRef = { urn, ...space }
  return {
    key: urn,
    entity: { id: nextId++, name: label, urn, datamodel, ...space },
    ref,
    label,
    lat,
    lon,
  }
}

const pairUrn = (origin: string, target: string) => `urn:ngsi-ld:${FLOW}:${origin}:${target}`

describe('nodeIdOf', () => {
  it('reduce todas las entidades de un mismo sensor al extremo con el que se nombran los pares', () => {
    for (const suffix of ['CFO', 'CFE', 'DEV', 'DHO']) {
      expect(nodeIdOf(`urn:ngsi-ld:X:S1_${suffix}`)).toBe('S1_CFE')
    }
  })

  it('deja intacto lo que no es de un sensor', () => {
    expect(nodeIdOf(`urn:ngsi-ld:${datamodelOf('zone')}:P13`)).toBe('P13')
  })
})

describe('buildPairs en modo derivado', () => {
  it('con los conteos de dos sensores compone los pares con el nombre que publica la plataforma', () => {
    const set = buildPairs([point(OBSERVED, 'A_CFO'), point(OBSERVED, 'B_CFO')])
    expect(set.mode).toBe('derived')
    expect(set.pairs.map((p) => p.urn).sort()).toEqual([pairUrn('A_CFE', 'B_CFE'), pairUrn('B_CFE', 'A_CFE')])
  })

  it('pide cada par en el espacio de la entidad de tránsitos de su origen, no en el del sensor', () => {
    const refs = new Map<string, EntityRef>([
      ['A_CFE', { urn: `urn:ngsi-ld:${FLOW}:A_CFE`, ...PLATFORM }],
      ['B_CFE', { urn: `urn:ngsi-ld:${FLOW}:B_CFE`, ...PLATFORM }],
    ])
    const set = buildPairs([point(OBSERVED, 'A_CFO'), point(OBSERVED, 'B_CFO')], refs)
    expect(set.pairs.every((p) => p.ref.tenant === 'plataforma')).toBe(true)
  })

  it('sin ese dato cae en el espacio del sensor de origen, como antes', () => {
    const set = buildPairs([point(OBSERVED, 'A_CFO'), point(OBSERVED, 'B_CFO')])
    expect(set.pairs.every((p) => p.ref.tenant === 'sensores')).toBe(true)
  })

  it('la entidad de tránsitos de un sensor asignada al panel es un punto y presta su espacio a los pares', () => {
    const set = buildPairs([
      point(FLOW, 'A_CFE', { space: PLATFORM }),
      point(FLOW, 'B_CFE', { space: PLATFORM }),
    ])
    expect(set.mode).toBe('derived')
    expect(set.pairs).toHaveLength(2)
    expect(set.pairs.every((p) => p.ref.tenant === 'plataforma')).toBe(true)
  })

  it('varias entidades del mismo sensor cuentan como un solo extremo, el que tiene ubicación', () => {
    const set = buildPairs([
      point(FLOW, 'A_CFE', { space: PLATFORM }),
      point(OBSERVED, 'A_CFO', { label: 'Plaza', lat: 43.5, lon: -5.6 }),
      point(OBSERVED, 'A_DEV'),
      point(OBSERVED, 'B_CFO', { label: 'Muelle', lat: 43.6, lon: -5.7 }),
    ])
    expect(set.sources).toBe(2)
    expect(set.nodes.map((n) => [n.id, n.label, n.lat])).toEqual([
      ['B_CFE', 'Muelle', 43.6],
      ['A_CFE', 'Plaza', 43.5],
    ])
    // El extremo se dibuja con el punto ubicado, pero el par sigue en el espacio de los tránsitos.
    expect(set.pairs.find((p) => p.origin.id === 'A_CFE')?.ref.tenant).toBe('plataforma')
  })
})

describe('buildPairs en modo explícito', () => {
  it('un par publicado asignado al panel manda, y sus extremos toman nombre y ubicación de los sensores', () => {
    const set = buildPairs([
      point(FLOW, 'A_CFE:B_CFE', { space: PLATFORM }),
      point(OBSERVED, 'A_CFO', { label: 'Plaza', lat: 43.5, lon: -5.6 }),
      point(OBSERVED, 'B_CFO', { label: 'Muelle', lat: 43.6, lon: -5.7 }),
    ])
    expect(set.mode).toBe('explicit')
    expect(set.pairs).toHaveLength(1)
    expect(set.pairs[0]).toMatchObject({
      urn: pairUrn('A_CFE', 'B_CFE'),
      origin: { label: 'Plaza', lat: 43.5 },
      target: { label: 'Muelle', lat: 43.6 },
    })
    expect(set.pairs[0].ref.tenant).toBe('plataforma')
  })

  it('descarta el par de un sensor consigo mismo', () => {
    const set = buildPairs([point(FLOW, 'A_CFE:A_CFE', { space: PLATFORM })])
    expect(set.mode).toBe('explicit')
    expect(set.pairs).toEqual([])
  })
})

describe('flowEntityUrns', () => {
  it('pide la entidad de tránsitos de cada sensor una sola vez y no la de los pares', () => {
    expect(
      flowEntityUrns([
        point(OBSERVED, 'A_CFO'),
        point(OBSERVED, 'A_DHO'),
        point(OBSERVED, 'B_CFO'),
        point(FLOW, 'A_CFE:B_CFE'),
      ]),
    ).toEqual([`urn:ngsi-ld:${FLOW}:A_CFE`, `urn:ngsi-ld:${FLOW}:B_CFE`])
  })
})

describe('pairSeriesOptions', () => {
  const week = { start: '2026-10-20T00:00:00Z', end: '2026-10-27T00:00:00Z' }
  const day = { start: '2026-10-26T00:00:00Z', end: '2026-10-27T00:00:00Z' }

  it('el volumen de los pares se suma al agregar, no se promedia', () => {
    expect(pairSeriesOptions('count', false, week)).toEqual({ aggregation: { type: 'sum', interval: 'PT1H' } })
  })

  it('en un día se lee sin agregar: ya viene por horas', () => {
    expect(pairSeriesOptions('count', false, day)).toEqual({ aggregation: null })
  })

  it('el resto de medidas siguen la regla general', () => {
    expect(pairSeriesOptions('averageTransitDuration', false, week)).toBeUndefined()
    expect(pairSeriesOptions('count', true, week)).toBeUndefined()
  })
})
