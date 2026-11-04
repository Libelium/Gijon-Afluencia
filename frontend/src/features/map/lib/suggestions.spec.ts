import { describe, expect, it } from 'vitest'
import type { Entity } from '@/types'
import { MAX_SUGGESTIONS, canSuggest, suggestionsFrom } from './suggestions'

const located = (id: number): Entity =>
  ({
    id,
    name: `E${id}`,
    urn: `urn:ngsi-ld:Thing:E${id}`,
    geolocation: { type: 'Point', coordinates: [-5.66, 43.54] },
  }) as Entity

const unlocated = (id: number): Entity => ({ id, name: `E${id}`, urn: `urn:ngsi-ld:Thing:E${id}` }) as Entity

describe('canSuggest', () => {
  it('sugiere a partir de dos letras', () => {
    expect(canSuggest('pl')).toBe(true)
    expect(canSuggest('p')).toBe(false)
  })

  it('no cuenta los espacios de los extremos', () => {
    expect(canSuggest('  p  ')).toBe(false)
    expect(canSuggest(' pl ')).toBe(true)
  })

  it('sin texto no sugiere', () => {
    expect(canSuggest('')).toBe(false)
    expect(canSuggest(null)).toBe(false)
    expect(canSuggest(undefined)).toBe(false)
  })
})

describe('suggestionsFrom', () => {
  it('descarta las entidades sin ubicacion: no se pueden señalar en el mapa', () => {
    const result = suggestionsFrom([unlocated(1), located(2)])
    expect(result.map((s) => s.entity.id)).toEqual([2])
    expect(result[0].latLng).toEqual([43.54, -5.66])
  })

  it('se queda con las primeras, en el orden en que llegan', () => {
    const rows = Array.from({ length: MAX_SUGGESTIONS + 3 }, (_, i) => located(i + 1))
    const result = suggestionsFrom(rows)
    expect(result).toHaveLength(MAX_SUGGESTIONS)
    expect(result.map((s) => s.entity.id)).toEqual(rows.slice(0, MAX_SUGGESTIONS).map((r) => r.id))
  })

  it('sin coincidencias con ubicacion, no hay sugerencias', () => {
    expect(suggestionsFrom([unlocated(1)])).toEqual([])
    expect(suggestionsFrom([])).toEqual([])
  })
})
