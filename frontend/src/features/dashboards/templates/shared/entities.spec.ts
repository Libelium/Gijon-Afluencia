import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Entity } from '@/types'
import { datamodelOf } from '../contract'

const post = vi.hoisted(() => vi.fn())

vi.mock('@/api/http', () => ({ http: { post, get: vi.fn() } }))

const { locateEventEntities } = await import('./entities')

const etl = datamodelOf('flowEvent')
const raw = datamodelOf('rawEvent')
const point = { type: 'Point', coordinates: [-5.66, 43.54] }

const entity = (tail: string, datamodel: string, geolocation?: unknown): Entity =>
  ({ id: 1, name: tail, urn: `urn:ngsi-ld:${datamodel}:${tail}`, datamodel, tenant: 't', scope: '/', geolocation }) as Entity

afterEach(() => {
  post.mockReset()
})

describe('locateEventEntities', () => {
  it('a la entidad de la ETL sin ubicación le pone la de los eventos en bruto de su sensor', async () => {
    post.mockResolvedValue({ data: { rows: [entity('S1_CFE', raw, point), entity('S2_CFE', raw, point)] } })
    const [located] = await locateEventEntities([entity('S1_CFE', etl)])
    expect(located.geolocation).toEqual(point)
    expect(post).toHaveBeenCalledWith('/entities/paginate', expect.objectContaining({ types: raw }))
  })

  it('no toca las que ya tienen ubicación ni las de otros modelos', async () => {
    post.mockResolvedValue({ data: { rows: [entity('S1_CFE', raw, point)] } })
    const own = { type: 'Point', coordinates: [-5.6, 43.5] }
    const counts = datamodelOf('flowObserved')
    const [withOwn, other] = await locateEventEntities([entity('S1_CFE', etl, own), entity('S1_CFE', counts)])
    expect(withOwn.geolocation).toEqual(own)
    expect(other.geolocation).toBeUndefined()
    expect(post).not.toHaveBeenCalled()
  })

  it('solo toma la ubicación de entidades de eventos en bruto con ubicación', async () => {
    post.mockResolvedValue({ data: { rows: [entity('S1_CFE', etl, point), entity('S2_CFE', raw)] } })
    const result = await locateEventEntities([entity('S1_CFE', etl), entity('S2_CFE', etl)])
    expect(result.map((e) => e.geolocation)).toEqual([undefined, undefined])
  })

  it('si la consulta falla, devuelve las entidades como estaban', async () => {
    post.mockRejectedValue(new Error('caído'))
    const list = [entity('S1_CFE', etl)]
    expect(await locateEventEntities(list)).toBe(list)
  })
})
