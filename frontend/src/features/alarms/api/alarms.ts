import { ApiError, http } from '@/api/http'
import { DATA_SCOPE_PREFERENCE_KEY, alarmStateUrn } from '@/api/platform-contract'
import { listDataScopes, type DataScope } from '@/api/scopes'
import type { LogLine, PageQuery, Paginated, SeriesPoint, UserPreferences } from '@/types'
import { toNaiveUtc } from '../lib/display'
import type {
  AlarmAction,
  AlarmDetail,
  AlarmRow,
  DateRange,
  EventLevel,
  InactivityCondition,
  StatusSeries,
  ThresholdCondition,
} from '../types'

/** Medida bajo la que el backend publica el estado historico de una alarma (0 / 1). */
const STATUS_MEASURE = 'status'

export type AlarmsQuery = Pick<PageQuery, 'page' | 'paginationSize' | 'search'>

/**
 * El backend exige orderBy y orderDirection en la validacion aunque despues no los aplique
 * (ordena siempre por id): se envian para no recibir un 422, pero la tabla no ofrece ordenacion.
 */
export async function listAlarms(query: AlarmsQuery): Promise<Paginated<AlarmRow>> {
  const { data } = await http.post<Paginated<AlarmRow>>('/alarms/paginate', {
    page: query.page,
    paginationSize: query.paginationSize,
    search: query.search?.trim() || null,
    orderBy: 'id',
    orderDirection: 0,
  })

  return {
    count: Number(data?.count) || 0,
    rows: Array.isArray(data?.rows) ? data.rows : [],
  }
}

export async function getAlarm(id: number): Promise<AlarmDetail> {
  const { data } = await http.get<AlarmDetail>(`/alarms/${id}`)
  return data
}

export async function getConditions(id: number): Promise<ThresholdCondition[]> {
  const { data } = await http.get<ThresholdCondition[]>(`/alarms/${id}/conditions`)
  return Array.isArray(data) ? data : []
}

export async function getInactivityConditions(id: number): Promise<InactivityCondition[]> {
  const { data } = await http.get<InactivityCondition[]>(`/alarms/${id}/inactivityConditions`)
  return Array.isArray(data) ? data : []
}

export async function getActions(id: number): Promise<AlarmAction[]> {
  const { data } = await http.get<{ actions?: AlarmAction[] }>(`/alarms/${id}/actions`)
  return Array.isArray(data?.actions) ? data.actions : []
}

export async function listAlarmEvents(
  id: number,
  range: DateRange,
  level: EventLevel,
  page: number,
  paginationSize = 10,
): Promise<Paginated<LogLine>> {
  const { data } = await http.post<Paginated<LogLine>>('/logs/paginate', {
    resource_type: 'alarms',
    resource_id: [id],
    start_date: toNaiveUtc(range.start),
    end_date: toNaiveUtc(range.end),
    level: level === 'ALL' ? null : level,
    page,
    paginationSize,
    orderBy: 'id',
    // 0 se traduce en orden descendente: la primera pagina trae los eventos mas recientes.
    orderDirection: 0,
  })

  return {
    count: Number(data?.count) || 0,
    rows: Array.isArray(data?.rows) ? data.rows : [],
  }
}

/** Identificador del ambito de datos donde vive la entidad de estado de las alarmas. */
export function dataScopeId(preferences: UserPreferences): string | null {
  if (!DATA_SCOPE_PREFERENCE_KEY) return null
  const value = preferences[DATA_SCOPE_PREFERENCE_KEY]
  return value ? String(value) : null
}

async function resolveDataScope(scopeId: string): Promise<{ tenant: string; scope: string } | null> {
  let scopes: DataScope[]
  try {
    scopes = await listDataScopes()
  } catch (error) {
    // Sin permiso sobre los ambitos no se puede resolver, pero tampoco es un fallo que reportar.
    if (error instanceof ApiError && ['forbidden', 'notFound', 'validation'].includes(error.kind)) {
      return null
    }
    throw error
  }

  const match = scopes.find((row) => row.id === scopeId)
  return match ? { tenant: match.tenant, scope: match.scope } : null
}

interface RawSeriesValue {
  timestamp?: string
  value?: unknown
}

interface RawSeries {
  device_id?: string
  measure_id?: string
  values?: RawSeriesValue[]
}

interface TimeSeriesEnvelope {
  time_series?: RawSeries[]
}

function statusValue(raw: unknown): number | null {
  if (typeof raw === 'boolean') return raw ? 1 : 0
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : null
  if (typeof raw === 'string') {
    const trimmed = raw.trim().toLowerCase()
    if (trimmed === 'true') return 1
    if (trimmed === 'false') return 0
    const numeric = Number(trimmed)
    return Number.isFinite(numeric) ? numeric : null
  }
  return null
}

function extractStatusPoints(payload: unknown): SeriesPoint[] {
  const envelopes: unknown[] = Array.isArray(payload) ? payload : [payload]
  const series: RawSeries[] = []

  for (const envelope of envelopes) {
    const list = (envelope as TimeSeriesEnvelope | null)?.time_series
    if (Array.isArray(list)) series.push(...list)
  }

  const measured = series.find((entry) => {
    const id = entry.measure_id ?? ''
    return id === STATUS_MEASURE || id.endsWith(`:${STATUS_MEASURE}`)
  })

  const values = (measured ?? series[0])?.values
  if (!Array.isArray(values)) return []

  return values
    .filter((point): point is RawSeriesValue & { timestamp: string } => Boolean(point?.timestamp))
    .map((point) => ({ timestamp: point.timestamp, value: statusValue(point.value) }))
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
}

export interface StatusSeriesOptions {
  range: DateRange
  scopeId?: string | null
  limit?: number
}

/**
 * Historico de estado de la alarma. Depende de identificadores propios del despliegue:
 * cuando no estan configurados o no se puede resolver el ambito, se dice explicitamente
 * en lugar de devolver una serie vacia indistinguible de "no hay datos".
 */
export async function getAlarmStatusSeries(
  alarm: Pick<AlarmDetail, 'id'>,
  options: StatusSeriesOptions,
): Promise<StatusSeries> {
  const urn = alarmStateUrn(alarm.id)
  if (!urn) return { state: 'unconfigured' }

  const scopeId = options.scopeId?.trim()
  if (!scopeId) return { state: 'unresolved' }

  const target = await resolveDataScope(scopeId)
  if (!target) return { state: 'unresolved' }

  const { data } = await http.post<TimeSeriesEnvelope[]>('/timeseries', [
    {
      device_ids: [urn],
      measure_ids: [STATUS_MEASURE],
      options: {
        start_date: options.range.start,
        end_date: options.range.end,
        order: 'asc',
        limit: options.limit ?? 2000,
        tenant: target.tenant,
        scope: target.scope,
      },
    },
  ])

  return { state: 'ok', points: extractStatusPoints(data) }
}
