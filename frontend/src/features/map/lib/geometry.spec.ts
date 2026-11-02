import { describe, expect, it } from 'vitest'
import type { Entity } from '@/types'
import { mergePlaced, type LatLng, type PlacedEntity } from './geometry'

const placed = (id: number, latLng: LatLng): PlacedEntity => ({
  entity: { id, name: `E${id}`, urn: `urn:ngsi-ld:Thing:E${id}` } as Entity,
  latLng,
})

describe('mergePlaced', () => {
  it('una entidad que no se ha movido conserva sus coordenadas de antes, no unas iguales', () => {
    const before = placed(1, [43.54, -5.66])
    const [after] = mergePlaced([before], [placed(1, [43.54, -5.66])])
    expect(after.latLng).toBe(before.latLng)
  })

  it('los datos de la entidad son los de la carga nueva', () => {
    const fresh = placed(1, [43.54, -5.66])
    fresh.entity.name = 'renombrada'
    const [after] = mergePlaced([placed(1, [43.54, -5.66])], [fresh])
    expect(after.entity.name).toBe('renombrada')
  })

  it('una entidad que se ha movido lleva sus coordenadas nuevas', () => {
    const moved = placed(1, [43.55, -5.66])
    const [after] = mergePlaced([placed(1, [43.54, -5.66])], [moved])
    expect(after.latLng).toBe(moved.latLng)
  })

  it('las que salen del area visible se quedan y las nuevas se suman detras', () => {
    const gone = placed(1, [43.54, -5.66])
    const fresh = placed(2, [43.5, -5.6])
    expect(mergePlaced([gone], [fresh])).toEqual([gone, fresh])
  })

  it('sin nada pintado, el resultado es la carga nueva', () => {
    const fresh = [placed(1, [43.54, -5.66]), placed(2, [43.5, -5.6])]
    expect(mergePlaced([], fresh)).toEqual(fresh)
  })
})
