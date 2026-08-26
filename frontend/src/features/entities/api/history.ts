import { http } from '@/api/http'
import type { ChartPoint } from '@/features/dashboards/charts'
import { resolveAggregation, type AggregationOption, type DateRange } from '@/features/dashboards/lib/range'
import { parseApiDateTime } from '@/lib/format'
import type { EntityRef } from '@/types'

/** Tope de puntos por consulta: el servicio de datos no impone ninguno y sin limite lo tumbamos. */
const MAX_POINTS = 2000

/**
 * El cuerpo es un array de sub-peticiones y la respuesta llega en el mismo orden. Enviar un
 * objeto suelto, aunque solo se pida una serie, lo rechaza con un 422.
 */
interface TimeSeriesRequest {
  device_ids: string[]
  measure_ids: string[]
  options: {
    start_date: string
    end_date: string
    order: 'desc'
    limit: number
    /** El espacio de datos y el ambito viajan en el cuerpo, no en cabeceras. */
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

export interface MeasureHistory {
  points: ChartPoint[]
  /** Agregacion aplicada, para poder advertir de que no se dibujan lecturas crudas. */
  aggregation: AggregationOption | null
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

interface Reading {
  at: number
  point: ChartPoint
}

/**
 * El servidor emite la marca en UTC sin declararlo, asi que se normaliza por el unico punto
 * que interpreta fechas de la API y se reemite con desplazamiento explicito: quien la vuelva
 * a leer no puede equivocarse de instante.
 */
function toReading(raw: RawValue): Reading | null {
  const at = parseApiDateTime(raw.timestamp)
  const iso = at?.toISO()
  if (!at || !iso) return null
  return { at: at.toMillis(), point: { t: iso, v: numeric(raw.value) } }
}

/**
 * Historico de una sola medida. Se ordena por instante y no por la cadena original porque un
 * cambio de hora deja dos desplazamientos distintos en la misma ventana.
 */
export async function getMeasureHistory(
  ref: EntityRef,
  measureId: string,
  range: DateRange,
): Promise<MeasureHistory> {
  const aggregation = resolveAggregation(range)

  const body: TimeSeriesRequest[] = [
    {
      device_ids: [ref.urn],
      measure_ids: [measureId],
      options: {
        start_date: range.start,
        end_date: range.end,
        // El limite se aplica sobre el orden pedido: descendente conserva lo mas reciente.
        order: 'desc',
        limit: MAX_POINTS,
        tenant: ref.tenant,
        scope: ref.scope,
        ...(aggregation ? { aggregation } : {}),
      },
    },
  ]

  const { data } = await http.post<RawTimeSeriesResponse[]>('/timeseries', body)
  const list = (Array.isArray(data) ? data[0] : undefined)?.time_series ?? []
  const match =
    list.find((serie) => serie.device_id === ref.urn && serie.measure_id === measureId) ?? list[0]

  const points = (match?.values ?? [])
    .map(toReading)
    .filter((reading): reading is Reading => reading !== null)
    .sort((a, b) => a.at - b.at)
    .map((reading) => reading.point)

  return { points, aggregation }
}
