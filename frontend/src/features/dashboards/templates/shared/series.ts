import { http } from '@/api/http'
import type { ChartPoint } from '../../charts'
import { autoAggregation, type AggregationOption, type DateRange } from '../../lib/range'
import type { EntityRef } from '@/types'
import { toIncrements } from './aggregate'

/** Tope de puntos por serie. El servicio de datos no impone ninguno y sin limite lo tumbamos. */
export const MAX_SERIES_POINTS = 2000

/** Peticiones por POST. Un array de 30 objetos ya hace que el backend tarde de mas. */
export const REQUEST_BATCH = 25

export interface SeriesRequest {
  /** Clave con la que la plantilla recupera el resultado. Debe ser unica en la lista. */
  key: string
  ref: EntityRef
  /** URN alternativo al de `ref` (pares de transito con URN compuesto). */
  urn?: string
  measureId: string
  /** Contador acumulativo: se pide por maximo y se devuelve por incrementos. */
  cumulative?: boolean
}

export interface FetchSeriesOptions {
  /** Fuerza la agregacion. Si se omite, la decide `autoAggregation` a partir del rango. */
  aggregation?: AggregationOption | null
  /** Fuerza el limite. Por defecto MAX_SERIES_POINTS; los indicadores de ultimo valor piden 1. */
  limit?: number
}

interface TimeSeriesRequestBody {
  device_ids: string[]
  measure_ids: string[]
  options: {
    start_date: string
    end_date: string
    order: 'desc'
    limit: number
    tenant: string
    scope: string
    aggregation?: AggregationOption
  }
}

interface RawValue {
  timestamp?: string
  value?: unknown
}

interface RawTimeSeries {
  device_id?: string
  measure_id?: string
  values?: RawValue[]
}

interface RawTimeSeriesResponse {
  time_series?: RawTimeSeries[]
}

function numeric(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'boolean') return value ? 1 : 0
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

function requestUrn(request: SeriesRequest): string {
  return request.urn ?? request.ref.urn
}

function resolveAggregation(
  request: SeriesRequest,
  range: DateRange,
  options?: FetchSeriesOptions,
): AggregationOption | null {
  if (options?.aggregation !== undefined) return options.aggregation
  return request.cumulative ? autoAggregation(range, 'max') : autoAggregation(range, 'mean')
}

function readPoints(
  response: RawTimeSeriesResponse | undefined,
  urn: string,
  measureId: string,
): ChartPoint[] {
  const list = response?.time_series ?? []
  const match =
    list.find((s) => s.device_id === urn && s.measure_id === measureId) ??
    list.find((s) => s.measure_id?.endsWith(`:${measureId}`)) ??
    list[0]

  return (match?.values ?? [])
    .filter((v): v is RawValue & { timestamp: string } => typeof v.timestamp === 'string')
    .map((v) => ({ t: v.timestamp, v: numeric(v.value) }))
    .sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : 0))
}

function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = []
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size))
  return out
}

/**
 * Pide todas las series en lotes y devuelve un mapa clave → puntos, ordenados por tiempo
 * ascendente. Una clave sin datos aparece en el mapa con array vacio: la ausencia de dato es
 * informacion, y omitirla obligaria a cada plantilla a distinguir «no pedido» de «sin datos».
 */
export async function fetchSeries(
  requests: SeriesRequest[],
  range: DateRange,
  options?: FetchSeriesOptions,
): Promise<Map<string, ChartPoint[]>> {
  const result = new Map<string, ChartPoint[]>()
  for (const request of requests) result.set(request.key, [])
  if (!requests.length) return result

  const limit = options?.limit ?? MAX_SERIES_POINTS

  for (const batch of chunk(requests, REQUEST_BATCH)) {
    const body: TimeSeriesRequestBody[] = batch.map((request) => {
      const aggregation = resolveAggregation(request, range, options)
      return {
        device_ids: [requestUrn(request)],
        measure_ids: [request.measureId],
        options: {
          start_date: range.start,
          end_date: range.end,
          // El limite se aplica sobre el orden pedido: descendente conserva lo mas reciente.
          order: 'desc',
          limit,
          tenant: request.ref.tenant,
          scope: request.ref.scope,
          ...(aggregation ? { aggregation } : {}),
        },
      }
    })

    const { data } = await http.post<RawTimeSeriesResponse[]>('/timeseries', body)
    const responses = Array.isArray(data) ? data : []

    batch.forEach((request, index) => {
      const points = readPoints(responses[index], requestUrn(request), request.measureId)
      result.set(request.key, request.cumulative ? toIncrements(points) : points)
    })
  }

  return result
}

/** Ultimo valor de cada peticion. Pide limit 1 y sin agregacion, como exige la regla de producto. */
export async function fetchLatest(
  requests: SeriesRequest[],
  range: DateRange,
): Promise<Map<string, ChartPoint | null>> {
  const series = await fetchSeries(requests, range, { aggregation: null, limit: 1 })
  const result = new Map<string, ChartPoint | null>()
  for (const [key, points] of series) result.set(key, points.length ? points[points.length - 1] : null)
  return result
}
