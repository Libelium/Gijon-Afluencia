import { beforeEach, describe, expect, it, vi } from 'vitest'

const post = vi.hoisted(() => vi.fn())
vi.mock('@/api/http', () => ({ http: { post } }))

const { fetchSeries } = await import('./series')

const ref = { urn: 'urn:ngsi-ld:Thing:A', tenant: 'demo', scope: '/' }
const week = { start: '2026-11-01T00:00:00Z', end: '2026-11-08T00:00:00Z' }

beforeEach(() => post.mockReset().mockResolvedValue({ data: [] }))

const aggregationsSent = () => post.mock.calls[0][1].map((body: { options: { aggregation?: unknown } }) => body.options.aggregation)

describe('fetchSeries, agregación por serie', () => {
  it('cada serie se agrega con su función, en la misma petición', async () => {
    await fetchSeries(
      [
        { key: 'a', ref, measureId: 'count', fn: 'sum' },
        { key: 'b', ref, measureId: 'maximumTransitDuration', fn: 'max' },
        { key: 'c', ref, measureId: 'averageTransitDuration' },
      ],
      week,
    )
    expect(post).toHaveBeenCalledTimes(1)
    expect(aggregationsSent()).toEqual([
      { type: 'sum', interval: 'PT1H' },
      { type: 'max', interval: 'PT1H' },
      { type: 'mean', interval: 'PT1H' },
    ])
  })

  it('una agregación forzada para toda la carga sigue mandando', async () => {
    await fetchSeries([{ key: 'a', ref, measureId: 'count', fn: 'sum' }], week, { aggregation: null })
    expect(aggregationsSent()).toEqual([undefined])
  })
})
