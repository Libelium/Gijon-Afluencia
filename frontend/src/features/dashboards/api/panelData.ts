import { http } from '@/api/http'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import type { Panel, PanelSeries } from '@/types'
import { resolveChartKind, type ChartData, type ChartKind, type ChartSeries } from '../charts'
import {
  FORECAST_HORIZON_HOURS,
  extendRange,
  resolveAggregation,
  resolveRange,
  type AggregationOption,
  type RangeInput,
} from '../lib/range'
import { numericValue, type RawTimeSeriesResponse, type RawValue } from '../lib/timeseries'
import { isPredictionEntity, isZoneEntity } from '../templates/contract'
import { anomalyMarkers } from '../templates/lidar/data'
import { matchRole } from '../templates/lidar/roles'

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

/**
 * Medida que publica en cada zona la deteccion diaria de anomalias: 1 en las horas que se salen de
 * lo normal, 0 en el resto.
 */
export const ANOMALY_MEASURE_ID = 'isOutlier'

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

/**
 * Series de linea con la ocupacion de una zona: las unicas que llevan encima sus horas anomalas,
 * porque la deteccion solo puntua las zonas. Una por zona, aunque el panel la pinte dos veces
 * (media y maximo, por ejemplo): repetir las marcas no dice nada nuevo.
 */
function zoneOccupancyItems(items: QueryableSeries[]): QueryableSeries[] {
  const seen = new Set<string>()
  return items.filter((item) => {
    if (seen.has(item.urn) || !isZoneEntity(item.serie.entity)) return false
    const occupancy = matchRole([item.measure], 'occupancy') ?? matchRole([item.measure], 'ratio')
    if (!occupancy) return false
    seen.add(item.urn)
    return true
  })
}

/**
 * Las horas anomalas de cada zona, con la misma ventana e intervalo que su linea y por maximo: un
 * intervalo agregado (un dia) cuenta como anomalo si lo es alguna de sus horas. Si la peticion
 * falla, el panel se pinta igual, sin marcas: no se pueden saber de antemano las zonas que publican
 * la deteccion, y una que no la publique no debe dejar el grafico en error.
 */
async function fetchAnomalies(requests: TimeSeriesRequest[]): Promise<RawTimeSeriesResponse[]> {
  if (!requests.length) return []
  const body = requests.map((request) => ({
    ...request,
    measure_ids: [ANOMALY_MEASURE_ID],
    options: {
      ...request.options,
      ...(request.options.aggregation
        ? { aggregation: { ...request.options.aggregation, type: 'max' as const } }
        : {}),
    },
  }))
  try {
    const { data } = await http.post<RawTimeSeriesResponse[]>('/timeseries', body)
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

export async function fetchPanelData(
  panel: Panel,
  range: RangeInput,
  timeZone?: string,
): Promise<ChartData> {
  const items = queryableSeries(panel.series)
  if (!items.length) return { series: [] }

  const resolved = resolveRange(range, timeZone)
  const kind = resolveChartKind(panel)
  const lastValueOnly = LAST_VALUE_KINDS.includes(kind)

  const body: TimeSeriesRequest[] = items.map((item) => {
    // Una prevision llega hasta horas futuras. Los graficos de ultimo valor se quedan en «ahora»:
    // con el orden descendente, lo que muestran es la prevision de la hora en curso.
    const window =
      !lastValueOnly && isPredictionEntity(item.serie.entity)
        ? extendRange(resolved, FORECAST_HORIZON_HOURS)
        : resolved
    const aggregation = lastValueOnly
      ? null
      : resolveAggregation(window, item.serie.grouping_function, item.serie.grouping_interval)
    return {
      device_ids: [item.urn],
      measure_ids: [item.measure],
      options: {
        start_date: window.start,
        end_date: window.end,
        // El limite se aplica sobre el orden pedido, de modo que descendente conserva lo ultimo.
        order: 'desc',
        limit: lastValueOnly ? 1 : MAX_POINTS,
        tenant: item.tenant,
        scope: item.scope,
        ...(aggregation ? { aggregation } : {}),
      },
    }
  })

  // Solo en las lineas: las marcas son puntos sueltos sobre la linea de la ocupacion.
  const zones = kind === 'line' ? zoneOccupancyItems(items) : []
  const [{ data }, anomalies] = await Promise.all([
    http.post<RawTimeSeriesResponse[]>('/timeseries', body),
    fetchAnomalies(zones.map((item) => body[items.indexOf(item)])),
  ])
  const responses = Array.isArray(data) ? data : []
  const withEntity = new Set(items.map((item) => item.urn)).size > 1

  const series: ChartSeries[] = items.map((item, index) => ({
    name: seriesName(item, withEntity),
    units: item.serie.measure?.units || undefined,
    points: readPoints(responses[index], item),
  }))

  zones.forEach((item, index) => {
    const line = series[items.indexOf(item)]
    const flags = readPoints(anomalies[index], { ...item, measure: ANOMALY_MEASURE_ID })
    const points = anomalyMarkers(line.points, flags)
    // Solo si hay alguna: una leyenda con una serie vacia haria buscar algo que no esta.
    if (!points.some((point) => point.v !== null)) return
    const label = t('dashboards.chart.anomalies')
    const entity = item.serie.entity?.name || urnTail(item.urn)
    series.push({
      name: withEntity ? `${entity} · ${label}` : label,
      units: line.units,
      points,
      markers: true,
    })
  })

  return { series }
}
