import { afterEach, describe, expect, it, vi } from 'vitest'
import { computed, nextTick, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'
import type { ChartPoint } from '../../charts'
import type { FlowNode, FlowPair } from './pairs'
import type { Route } from './useTransits'

const fetchSeries = vi.hoisted(() => vi.fn())
vi.mock('../shared/series', async (original) => ({
  ...(await original<typeof import('../shared/series')>()),
  fetchSeries,
}))

const { MAX_DETAIL_ROUTES, detailRequests, routeDetail, toMinutes, useRouteDetails, weightedMean } = await import(
  './routeDetails'
)

const node = (id: string): FlowNode => ({ id, label: id, lat: 43.5, lon: -5.6 })
const route = (from: string, to: string, total = 10): Route => {
  const pair: FlowPair = {
    key: `${from}>${to}`,
    urn: `urn:ngsi-ld:Flow:${from}:${to}`,
    ref: { urn: `urn:ngsi-ld:Flow:${from}`, tenant: 'demo_platform', scope: '/' },
    origin: node(from),
    target: node(to),
    label: `${from} → ${to}`,
  }
  return { pair, points: [], total }
}
const at = (hour: number, v: number | null): ChartPoint => ({ t: `2026-11-04T${String(hour).padStart(2, '0')}:00:00Z`, v })

afterEach(() => fetchSeries.mockReset())

describe('weightedMean', () => {
  it('pesa cada hora por sus tránsitos', () => {
    // 10 min con 90 tránsitos y 30 min con 10: la media de verdad son 12 min, no 20.
    expect(weightedMean([at(9, 600), at(10, 1800)], [at(9, 90), at(10, 10)])).toBe(720)
  })

  it('ignora las horas sin tránsitos o sin duración', () => {
    expect(weightedMean([at(9, 600), at(10, null), at(11, 999)], [at(9, 5), at(10, 8), at(11, 0)])).toBe(600)
  })

  it('sin pesos, la media simple; sin valores, nada', () => {
    expect(weightedMean([at(9, 600), at(10, 1200)], [])).toBe(900)
    expect(weightedMean([], [])).toBeNull()
  })
})

describe('un recorrido', () => {
  it('pide cada medida con su agregación, y los tipos de visitante solo si se piden', () => {
    const simple = detailRequests(route('A', 'B'), false)
    expect(simple.map((r) => [r.measureId, r.fn])).toEqual([
      ['count', 'sum'],
      ['averageTransitDuration', 'mean'],
      ['maximumTransitDuration', 'max'],
    ])
    expect(simple[0]).toMatchObject({ key: 'A>B|count', urn: 'urn:ngsi-ld:Flow:A:B', ref: { tenant: 'demo_platform' } })
    expect(detailRequests(route('A', 'B'), true).map((r) => r.measureId).slice(3)).toEqual([
      'touristCount',
      'residentCount',
      'shortTermVisitorCount',
    ])
  })

  it('da la duración en minutos y los tránsitos de cada tipo en el periodo', () => {
    const detail = routeDetail(
      route('A', 'B'),
      new Map([
        ['count', [at(9, 90), at(10, 10)]],
        ['averageTransitDuration', [at(9, 600), at(10, 1800)]],
        ['maximumTransitDuration', [at(9, 1500), at(10, 3300)]],
        ['touristCount', [at(9, 30), at(10, 2)]],
        ['residentCount', []],
      ]),
    )
    expect(detail).toEqual({
      key: 'A>B',
      label: 'A → B',
      averageMinutes: 12,
      maximumMinutes: 55,
      // Sin pedir corta estancia no hay dato; pedido y vacío, tampoco.
      visitors: { tourist: 32, resident: null, shortTerm: null },
    })
  })

  it('los minutos se redondean a una décima', () => {
    expect(toMinutes(100)).toBe(1.7)
    expect(toMinutes(null)).toBeNull()
  })
})

describe('useRouteDetails', () => {
  const week = { start: '2026-10-28T00:00:00Z', end: '2026-11-04T00:00:00Z' }

  it('pide los detalles de los diez recorridos principales en una carga', async () => {
    fetchSeries.mockImplementation(async (requests: { key: string }[]) => new Map(requests.map((r) => [r.key, [at(9, 60)]])))
    const routes = Array.from({ length: 12 }, (_, i) => route(`N${i}`, `N${i + 1}`, 100 - i))
    const { details } = useRouteDetails(computed(() => routes), ref(week), false)
    await flushPromises()

    expect(fetchSeries).toHaveBeenCalledTimes(1)
    const [requests, range] = fetchSeries.mock.calls[0]
    expect(requests).toHaveLength(MAX_DETAIL_ROUTES * 3)
    expect(range).toEqual(week)
    expect(details.value.map((d) => d.key)).toEqual(routes.slice(0, MAX_DETAIL_ROUTES).map((r) => r.pair.key))
    expect(details.value[0].averageMinutes).toBe(1)
  })

  it('vuelve a pedir al cambiar el rango, y sin recorridos no pide nada', async () => {
    fetchSeries.mockResolvedValue(new Map())
    const routes = ref<Route[]>([route('A', 'B')])
    const range = ref(week)
    useRouteDetails(computed(() => routes.value), range, true)
    await flushPromises()
    range.value = { start: '2026-10-05T00:00:00Z', end: '2026-11-04T00:00:00Z' }
    await nextTick()
    await flushPromises()
    expect(fetchSeries).toHaveBeenCalledTimes(2)

    routes.value = []
    await nextTick()
    await flushPromises()
    expect(fetchSeries).toHaveBeenCalledTimes(2)
  })

  it('si la carga falla, lo dice y no deja detalles viejos', async () => {
    fetchSeries.mockRejectedValue(new Error('caído'))
    const { details, error } = useRouteDetails(computed(() => [route('A', 'B')]), ref(week), false)
    await flushPromises()
    expect(error.value).toBeTruthy()
    expect(details.value).toEqual([])
  })
})
