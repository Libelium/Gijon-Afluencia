import { http } from '@/api/http'
import { urnTail } from '@/lib/format'
import type { Panel, PanelSeries } from '@/types'
import { resolveChartKind, type ChartData, type ChartKind } from '../charts'
import { resolveAggregation, resolveRange, type AggregationOption, type RangeInput } from '../lib/range'
import { numericValue, type RawTimeSeriesResponse, type RawValue } from '../lib/timeseries'

/**
 * Consulta de datos de un panel al servicio de series temporales. Traduce las series del panel a
 * peticiones `/timeseries`, decide la agregacion y el limite segun el tipo de grafico, y da forma
 * al resultado que consumen los graficos.
 */

/** Graficos de ultimo valor: solo necesitan la lectura mas reciente. */
const LAST_VALUE_KINDS: ChartKind[] = ['kpi', 'gauge']

/**
 * Tope de puntos por serie. El servicio de datos no impone ninguno: una consulta sin limite
 * sobre una entidad con historico largo devuelve millones de filas y lo tumba.
 */
const MAX_POINTS = 2000

interface TimeSeriesRequest {
  device_ids: string[]
  measure_ids: string[]
  options: {
    start_date: string
    end_date: string
    order: 'asc' | 'desc'
    limit: number
    tenant: string
    scope: string
    aggregation?: AggregationOption
  }
}

interface QueryableSeries {
  serie: PanelSeries
  urn: string
  measure: string
  tenant: string
  scope: string
}

/**
 * Solo las series de medida se pueden consultar: las calculadas o multidimensionales
 * dependen de una formula que resolvia la herramienta de origen.
 */
export function queryableSeries(series: PanelSeries[] | undefined): QueryableSeries[] {
  return (series ?? []).flatMap((serie) => {
    const urn = serie.entity?.urn
    const measure = serie.measure?.id
    const tenant = serie.entity?.tenant
    const scope = serie.entity?.scope
    if (!urn || !measure || !tenant || !scope) return []
    return [{ serie, urn, measure, tenant, scope }]
  })
}

function seriesName(item: QueryableSeries, withEntity: boolean): string {
  if (item.serie.alias) return item.serie.alias
  const measure = item.serie.measure?.name || item.measure
  if (!withEntity) return measure
  const entity = item.serie.entity?.name || urnTail(item.urn)
  return `${entity} · ${measure}`
}

function readPoints(response: RawTimeSeriesResponse | undefined, item: QueryableSeries) {
  const list = response?.time_series ?? []
  const match = list.find((s) => s.device_id === item.urn && s.measure_id === item.measure) ?? list[0]

  return (match?.values ?? [])
    .filter((value): value is RawValue & { timestamp: string } => typeof value.timestamp === 'string')
    .map((value) => ({ t: value.timestamp, v: numericValue(value.value) }))
    // La consulta va en orden descendente para quedarse con lo mas reciente; el grafico lo pinta al contrario.
    .sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : 0))
}

export async function fetchPanelData(
  panel: Panel,
  range: RangeInput,
  timeZone?: string,
): Promise<ChartData> {
  const items = queryableSeries(panel.series)
  if (!items.length) return { series: [] }

  const resolved = resolveRange(range, timeZone)
  const lastValueOnly = LAST_VALUE_KINDS.includes(resolveChartKind(panel))

  const body: TimeSeriesRequest[] = items.map((item) => {
    const aggregation = lastValueOnly
      ? null
      : resolveAggregation(resolved, item.serie.grouping_function, item.serie.grouping_interval)
    return {
      device_ids: [item.urn],
      measure_ids: [item.measure],
      options: {
        start_date: resolved.start,
        end_date: resolved.end,
        // El limite se aplica sobre el orden pedido, de modo que descendente conserva lo ultimo.
        order: 'desc',
        limit: lastValueOnly ? 1 : MAX_POINTS,
        tenant: item.tenant,
        scope: item.scope,
        ...(aggregation ? { aggregation } : {}),
      },
    }
  })

  const { data } = await http.post<RawTimeSeriesResponse[]>('/timeseries', body)
  const responses = Array.isArray(data) ? data : []
  const withEntity = new Set(items.map((item) => item.urn)).size > 1

  return {
    series: items.map((item, index) => ({
      name: seriesName(item, withEntity),
      units: item.serie.measure?.units || undefined,
      points: readPoints(responses[index], item),
    })),
  }
}
