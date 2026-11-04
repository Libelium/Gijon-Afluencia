import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
import { errorMessage } from '@/api/http'
import type { ChartPoint } from '../../charts'
import type { DateRange } from '../../lib/range'
import { kpisOf } from '../shared/aggregate'
import { fetchSeries, type SeriesRequest } from '../shared/series'
import type { Route } from './useTransits'

/**
 * Lo que cuenta cada recorrido ademas de su volumen. La ETL de tránsitos publica en cada par, por
 * hora, la duracion media y maxima del recorrido (segundos entre la deteccion en el origen y en el
 * destino) y cuantos tránsitos son de turistas, de residentes y de visitas de corta estancia. Se
 * leen solo para los recorridos principales: son cinco medidas mas por recorrido.
 */

/** Recorridos de los que se leen los detalles, los de mas volumen. */
export const MAX_DETAIL_ROUTES = 10

const COUNT = 'count'
const AVERAGE_DURATION = 'averageTransitDuration'
const MAXIMUM_DURATION = 'maximumTransitDuration'

export type VisitorType = 'tourist' | 'resident' | 'shortTerm'

/** En el orden del reparto de la plantilla de clasificacion, para que cada tipo conserve su sitio. */
export const VISITOR_TYPES: readonly { key: VisitorType; measureId: string }[] = [
  { key: 'tourist', measureId: 'touristCount' },
  { key: 'resident', measureId: 'residentCount' },
  { key: 'shortTerm', measureId: 'shortTermVisitorCount' },
]

export interface RouteDetail {
  key: string
  label: string
  /** Duracion media del periodo en minutos, ponderada por los tránsitos de cada intervalo. */
  averageMinutes: number | null
  /** La mayor de las duraciones maximas del periodo, en minutos. */
  maximumMinutes: number | null
  /** Tránsitos de cada tipo de visitante en el periodo. */
  visitors: Record<VisitorType, number | null>
}

export const toMinutes = (seconds: number | null): number | null =>
  seconds === null ? null : Math.round((seconds / 60) * 10) / 10

const isValue = (value: number | null | undefined): value is number =>
  value !== null && value !== undefined && Number.isFinite(value)

/**
 * Media de `values` ponderada por `weights`, emparejados por instante: una hora con cien tránsitos
 * pesa mas que una con dos. Si ningun instante tiene peso, la media simple de los valores.
 */
export function weightedMean(values: ChartPoint[], weights: ChartPoint[]): number | null {
  const weightAt = new Map(weights.map((point) => [point.t, point.v]))
  let sum = 0
  let weight = 0
  for (const point of values) {
    const w = weightAt.get(point.t)
    if (!isValue(point.v) || !isValue(w) || w <= 0) continue
    sum += point.v * w
    weight += w
  }
  return weight > 0 ? sum / weight : kpisOf(values).mean
}

/** Las series leidas de un recorrido, por medida. */
export type RouteSeries = Map<string, ChartPoint[]>

export function routeDetail(route: Route, series: RouteSeries): RouteDetail {
  const points = (measureId: string) => series.get(measureId) ?? []
  const visitors = Object.fromEntries(
    VISITOR_TYPES.map(({ key, measureId }) => [key, series.has(measureId) ? kpisOf(points(measureId)).total : null]),
  ) as Record<VisitorType, number | null>
  return {
    key: route.pair.key,
    label: route.pair.label,
    averageMinutes: toMinutes(weightedMean(points(AVERAGE_DURATION), points(COUNT))),
    maximumMinutes: toMinutes(kpisOf(points(MAXIMUM_DURATION)).max),
    visitors,
  }
}

/** Las peticiones de un recorrido: cada medida con la agregacion que le corresponde. */
export function detailRequests(route: Route, withVisitors: boolean): SeriesRequest[] {
  const measures: { measureId: string; fn: string }[] = [
    { measureId: COUNT, fn: 'sum' },
    { measureId: AVERAGE_DURATION, fn: 'mean' },
    { measureId: MAXIMUM_DURATION, fn: 'max' },
    ...(withVisitors ? VISITOR_TYPES.map(({ measureId }) => ({ measureId, fn: 'sum' })) : []),
  ]
  return measures.map(({ measureId, fn }) => ({
    key: `${route.pair.key}|${measureId}`,
    ref: route.pair.ref,
    urn: route.pair.urn,
    measureId,
    fn,
  }))
}

export interface UseRouteDetails {
  details: ComputedRef<RouteDetail[]>
  busy: Ref<boolean>
  error: Ref<string | null>
}

/**
 * Los detalles de los recorridos principales, que se vuelven a pedir al cambiar los recorridos o
 * el rango. Con un rango de mas de un mes las series llegan por dias: la media ponderada lo es
 * entonces por dia, que es la mejor aproximacion que da una serie diaria.
 */
export function useRouteDetails(
  routes: ComputedRef<Route[]>,
  range: ComputedRef<DateRange> | Ref<DateRange>,
  withVisitors: boolean,
): UseRouteDetails {
  const busy = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref<RouteDetail[]>([])
  let request = 0

  const top = computed(() => routes.value.slice(0, MAX_DETAIL_ROUTES))
  const signature = computed(
    () => `${range.value.start}|${range.value.end}|${top.value.map((route) => route.pair.key).join(',')}`,
  )

  async function load() {
    const current = ++request
    const selected = top.value
    if (!selected.length) {
      loaded.value = []
      return
    }
    busy.value = true
    error.value = null
    try {
      const series = await fetchSeries(
        selected.flatMap((route) => detailRequests(route, withVisitors)),
        range.value,
      )
      if (current !== request) return
      loaded.value = selected.map((route) => {
        const byMeasure: RouteSeries = new Map()
        for (const [key, points] of series) {
          const cut = key.lastIndexOf('|')
          if (key.slice(0, cut) === route.pair.key) byMeasure.set(key.slice(cut + 1), points)
        }
        return routeDetail(route, byMeasure)
      })
    } catch (e) {
      if (current !== request) return
      error.value = errorMessage(e)
      loaded.value = []
    } finally {
      if (current === request) busy.value = false
    }
  }

  watch(signature, () => void load(), { immediate: true })

  return { details: computed(() => loaded.value), busy, error }
}
