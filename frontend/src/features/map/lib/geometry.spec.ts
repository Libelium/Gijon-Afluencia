import { describe, expect, it } from 'vitest'
import type { Entity } from '@/types'
import { mergePlaced, placeEntities, type LatLng, type PlacedEntity } from './geometry'

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

describe('placeEntities', () => {
  const entity = (id: number, geolocation?: unknown): Entity =>
    ({ id, name: `E${id}`, urn: `urn:ngsi-ld:Thing:E${id}`, geolocation }) as Entity

  it('un punto se pinta en [latitud, longitud], al reves que en GeoJSON', () => {
    const { placed: rows } = placeEntities([entity(1, { type: 'Point', coordinates: [-5.66, 43.54] })])
    expect(rows[0].latLng).toEqual([43.54, -5.66])
  })

  it('un recinto se pinta en su centroide', () => {
    const square = [
      [-5.0, 43.0],
      [-4.0, 43.0],
      [-4.0, 44.0],
      [-5.0, 44.0],
      [-5.0, 43.0],
    ]
    const { placed: rows } = placeEntities([entity(1, { type: 'Polygon', coordinates: [square] })])
    expect(rows[0].latLng[0]).toBeCloseTo(43.5)
    expect(rows[0].latLng[1]).toBeCloseTo(-4.5)
  })

  it('un recinto sin area se pinta en la media de sus vertices', () => {
    const line = [
      [-5.0, 43.0],
      [-4.0, 43.0],
    ]
    const { placed: rows } = placeEntities([entity(1, { type: 'Polygon', coordinates: [line] })])
    expect(rows[0].latLng).toEqual([43, -4.5])
  })

  it('cuenta aparte las que no tienen una ubicacion utilizable', () => {
    const result = placeEntities([
      entity(1),
      entity(2, { type: 'Point', coordinates: [-5.66, 95] }),
      entity(3, { type: 'Point', coordinates: ['x', 43.5] }),
      entity(4, { type: 'Polygon', coordinates: [] }),
      entity(5, { type: 'Polygon', coordinates: [[['a', 'b']]] }),
      entity(6, { type: 'LineString', coordinates: [] }),
      entity(7, { type: 'Point', coordinates: [-5.66, 43.54] }),
    ])
    expect(result.placed.map((item) => item.entity.id)).toEqual([7])
    expect(result.withoutLocation).toBe(6)
  })
})
