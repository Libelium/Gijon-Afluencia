import { describe, expect, it } from 'vitest'
import type { Entity, Measure } from '@/types'
import { resolveEntityLocation } from './location'

const square = {
  type: 'Polygon',
  coordinates: [
    [
      [-5.664, 43.544],
      [-5.662, 43.544],
      [-5.662, 43.546],
      [-5.664, 43.546],
      [-5.664, 43.544],
    ],
  ],
}

describe('resolveEntityLocation', () => {
  it('una zona con contorno da su centro y conserva el contorno para dibujarlo', () => {
    const measures: Measure[] = [{ id: 'location', name: 'Ubicación', value: JSON.stringify(square) }]
    const location = resolveEntityLocation({ id: 1 } as Entity, measures)
    expect(location?.lat).toBeCloseTo(43.545)
    expect(location?.lon).toBeCloseTo(-5.663)
    expect(location?.polygon?.[0]).toEqual([43.544, -5.664])
    expect(location?.source).toBe('measure')
  })

  it('un punto no lleva contorno', () => {
    const location = resolveEntityLocation({
      id: 1,
      geolocation: { type: 'Point', coordinates: [-5.66, 43.54] },
    } as Entity)
    expect(location).toEqual({ lat: 43.54, lon: -5.66, source: 'entity' })
  })
})
