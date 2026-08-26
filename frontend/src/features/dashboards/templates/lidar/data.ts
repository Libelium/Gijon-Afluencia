import { DateTime } from 'luxon'
import { http } from '@/api/http'
import { listEntities } from '@/features/entities/api/entities'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import type { Aggregation, Entity, EntityRef, Measure } from '@/types'
import type { ChartPoint } from '../../charts'
import { autoAggregation, type DateRange } from '../../lib/range'
import { HIDDEN_IDS, matchRole, normalizeId, type RoleKey } from './roles'

/**
 * Nombres de modelo de datos en base64, por el mismo motivo que en `contract.ts`: contienen
 * la marca de un producto comercial ajeno y este repositorio es publico. El valor que viaja
 * por la red es el original.
 */
const MODELS = {
  zone: 'Q3Jvd2RGbG93TGlkYXJab25l',
  prediction: 'Q3Jvd2RGbG93UHJlZGljdGlvbg==',
} as const

const PRED_SUFFIX = '_pred'
const MAX_POINTS = 2000
/** Tope de puntos para una consulta forzada a hora, reutilizado por las vistas. */
export const MATRIX_POINTS = 2400

function decode(value: string): string {
  return atob(value)
}

export function zoneModel(): string {
  return decode(MODELS.zone)
}

export function predictionModel(): string {
  return decode(MODELS.prediction)
}

// --- utilidades de valor y fecha -------------------------------------------------------

/** Normaliza el `timestamp` de realtime (usa espacio) al ISO que espera Luxon. Null si no es fecha. */
export function isoOf(raw?: string | null): string | null {
  if (!raw) return null
  const text = String(raw).trim().replace(' ', 'T')
  return DateTime.fromISO(text, { zone: 'utc' }).isValid ? text : null
}

export function numericValue(raw: unknown): number | null {
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : null
  if (typeof raw === 'string' && raw.trim() !== '' && Number.isFinite(Number(raw))) return Number(raw)
  return null
}

const NUMERIC_VALUE_TYPES = ['double', 'integer', 'number', 'float', 'long', 'int']

export function isNumericMeasure(m: Measure): boolean {
  const type = String(m.value_type ?? '').toLowerCase()
  if (typeof m.value === 'boolean' || type === 'bool' || type === 'boolean') return false
  return NUMERIC_VALUE_TYPES.includes(type) || numericValue(m.value) !== null
}

export function isTextAttribute(m: Measure): boolean {
  return !HIDDEN_IDS.includes(normalizeId(m.id)) && !isNumericMeasure(m)
}

// --- perfil de la zona -------------------------------------------------------------------

export interface ZoneProfile {
  /** Medidas numericas visibles, ordenadas por nombre (es). */
  numeric: Measure[]
  /** Atributos de texto y booleanos visibles, ordenados por nombre (es). */
  text: Measure[]
  roles: Partial<Record<RoleKey, Measure>>
  /** Medida usada como ocupacion, o null si no hay ninguna numerica. */
  occupancy: Measure | null
  /** True cuando `occupancy` no viene de un candidato reconocido, sino de la reserva. */
  occupancyIsFallback: boolean
  /** Aforo maximo en personas, o null si la zona no lo publica. */
  capacity: number | null
  /** Ocupacion actual en personas, o null si no hay lectura numerica. */
  current: number | null
  /** Proporcion 0..n de `current` sobre `capacity`, o null si falta alguno. */
  ratio: number | null
  /** Marca ISO de la lectura mas reciente de la entidad, o null. */
  updatedAt: string | null
}

const NUMERIC_POOL_ROLES: RoleKey[] = [
  'occupancy',
  'ratio',
  'capacity',
  'dwell',
  'density',
  'inflow',
  'outflow',
  'predicted',
  'predLower',
  'predUpper',
]
const VISIBLE_POOL_ROLES: RoleKey[] = ['confidence', 'case', 'sensor']

export function describeZone(measures: Measure[]): ZoneProfile {
  const visible = measures.filter((m) => !HIDDEN_IDS.includes(normalizeId(m.id)))
  const numeric = [...visible.filter(isNumericMeasure)].sort((a, b) => a.name.localeCompare(b.name, 'es'))
  const text = [...visible.filter(isTextAttribute)].sort((a, b) => a.name.localeCompare(b.name, 'es'))

  const roles: Partial<Record<RoleKey, Measure>> = {}
  for (const role of NUMERIC_POOL_ROLES) {
    const found = matchRole(
      numeric.map((m) => m.id),
      role,
    )
    const measure = found ? numeric.find((m) => m.id === found) : undefined
    if (measure) roles[role] = measure
  }
  for (const role of VISIBLE_POOL_ROLES) {
    const found = matchRole(
      visible.map((m) => m.id),
      role,
    )
    const measure = found ? visible.find((m) => m.id === found) : undefined
    if (measure) roles[role] = measure
  }

  const capacityRaw = numericValue(roles.capacity?.value)
  const capacity = capacityRaw !== null && capacityRaw > 0 ? capacityRaw : null

  let occupancy: Measure | null = roles.occupancy ?? null
  let occupancyIsFallback = false
  if (!occupancy && numeric.length > 0) {
    const takenIds = new Set(Object.values(roles).map((m) => m?.id))
    occupancy = numeric.find((m) => !takenIds.has(m.id)) ?? numeric[0]
    occupancyIsFallback = true
  }

  const current = numericValue(occupancy?.value)

  let ratio: number | null = null
  if (current !== null && capacity) {
    ratio = current / capacity
  } else {
    const r = numericValue(roles.ratio?.value)
    if (r !== null) ratio = r > 1 ? r / 100 : r
  }

  let updatedAt: string | null = null
  for (const m of measures) {
    const iso = isoOf(m.timestamp)
    if (iso && (!updatedAt || iso > updatedAt)) updatedAt = iso
  }

  return { numeric, text, roles, occupancy, occupancyIsFallback, capacity, current, ratio, updatedAt }
}

// --- entidades del panel -----------------------------------------------------------------

interface RawEntityRow {
  id?: number | string
  name?: string
  urn?: string
  datamodel?: string
  tenant?: string
  scope?: string | null
  scope_id?: number
  tenant_id?: number
  geolocation?: Entity['geolocation']
  time_last_data?: string
}

export function refOf(entity: Entity): EntityRef {
  return { urn: entity.urn, tenant: entity.tenant, scope: entity.scope }
}

export async function fetchTemplateEntities(dashboardId: number): Promise<Entity[]> {
  const { data } = await http.get<{ entities?: unknown }>(`/dashboards/${dashboardId}`)
  const rows = Array.isArray(data?.entities) ? (data.entities as RawEntityRow[]) : []

  const entities: Entity[] = rows
    .filter((row) => !!row.urn && !!row.tenant && row.scope !== undefined && row.scope !== null)
    .map((row) => ({
      id: Number(row.id ?? 0),
      name: row.name?.trim() || urnTail(row.urn),
      urn: String(row.urn),
      datamodel: row.datamodel ?? '',
      tenant: String(row.tenant),
      scope: String(row.scope),
      scope_id: row.scope_id,
      tenant_id: row.tenant_id,
      geolocation: row.geolocation,
      time_last_data: row.time_last_data,
    }))

  return entities.sort((a, b) => a.name.localeCompare(b.name, 'es'))
}

export function zoneEntities(entities: Entity[]): { zones: Entity[]; usedFallback: boolean } {
  const zones = entities.filter((e) => e.datamodel === zoneModel())
  if (zones.length > 0) return { zones, usedFallback: false }
  return { zones: entities, usedFallback: entities.length > 0 }
}

// --- series temporales ---------------------------------------------------------------

export interface SeriesSpec {
  /** Clave con la que se devuelve la serie. */
  key: string
  measureId: string
  /** Funcion de agregacion. Por defecto 'mean'. */
  fn?: Aggregation
}

export interface FetchSeriesOptions {
  /** Fuerza el intervalo ISO en lugar del automatico (p. ej. 'PT1H'). */
  forceInterval?: string
  limit?: number
}

interface RawValue {
  timestamp?: string
  value?: unknown
}
interface RawSeries {
  device_id?: string
  measure_id?: string
  values?: RawValue[]
}
interface RawEnvelope {
  time_series?: RawSeries[]
}

function readPoints(envelope: RawEnvelope | undefined, measureId: string): ChartPoint[] {
  const list = envelope?.time_series ?? []
  const match =
    list.find((s) => s.measure_id === measureId || s.measure_id?.endsWith(`:${measureId}`)) ?? list[0]
  return (match?.values ?? [])
    .map((v) => ({ t: isoOf(v.timestamp), v: numericValue(v.value) }))
    .filter((p): p is ChartPoint => p.t !== null)
    .sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : 0))
}

export async function fetchZoneSeries(
  ref: EntityRef,
  specs: SeriesSpec[],
  range: DateRange,
  options?: FetchSeriesOptions,
): Promise<Record<string, ChartPoint[]>> {
  if (!specs.length) return {}
  const interval = options?.forceInterval ?? autoAggregation(range)?.interval ?? null
  const body = specs.map((spec) => ({
    device_ids: [ref.urn],
    measure_ids: [spec.measureId],
    options: {
      start_date: range.start,
      end_date: range.end,
      // El limite se aplica sobre el orden pedido: descendente conserva lo mas reciente.
      order: 'desc' as const,
      limit: options?.limit ?? MAX_POINTS,
      tenant: ref.tenant,
      scope: ref.scope,
      ...(interval ? { aggregation: { type: spec.fn ?? 'mean', interval } } : {}),
    },
  }))
  const { data } = await http.post<RawEnvelope[]>('/timeseries', body)
  const out: Record<string, ChartPoint[]> = {}
  specs.forEach((spec, index) => {
    out[spec.key] = readPoints(data?.[index], spec.measureId)
  })
  return out
}

// --- gemelo de prediccion -----------------------------------------------------------------

export async function findPredictionTwin(zone: Entity): Promise<Entity | null> {
  const target = `${urnTail(zone.urn)}${PRED_SUFFIX}`

  if (zone.datamodel && zone.urn.includes(`:${zone.datamodel}:`)) {
    try {
      const guess = zone.urn.replace(`:${zone.datamodel}:`, `:${predictionModel()}:`) + PRED_SUFFIX
      const { rows } = await listEntities({
        page: 1,
        paginationSize: 5,
        urn: guess,
        tenant: zone.tenant,
        scope: zone.scope,
      })
      if (rows.length) return rows[0]
    } catch {
      // se ignora y se pasa a la siguiente estrategia
    }
  }

  try {
    const { rows } = await listEntities({
      page: 1,
      paginationSize: 20,
      search: target,
      types: predictionModel(),
      tenant: zone.tenant,
      scope: zone.scope,
    })
    if (rows.length) {
      const exact = rows.find((row) => urnTail(row.urn).toLowerCase() === target.toLowerCase())
      return exact ?? rows[0]
    }
  } catch {
    // se ignora y se pasa a la siguiente estrategia
  }

  const { rows } = await listEntities({
    page: 1,
    paginationSize: 20,
    search: target,
    tenant: zone.tenant,
    scope: zone.scope,
  })
  const match = rows.find((row) => row.urn.toLowerCase().endsWith(PRED_SUFFIX) && row.urn !== zone.urn)
  return match ?? null
}

// --- agregados y forma de los datos ---------------------------------------------------

export interface Summary {
  count: number
  min: number | null
  max: number | null
  /** Marca ISO del punto donde se alcanza `max`. */
  maxAt: string | null
  mean: number | null
  last: number | null
  lastAt: string | null
}

export function summarise(points: ChartPoint[]): Summary {
  const valid = points.filter((p): p is { t: string; v: number } => p.v !== null)
  if (!valid.length) {
    return { count: 0, min: null, max: null, maxAt: null, mean: null, last: null, lastAt: null }
  }

  let min = valid[0].v
  let max = valid[0].v
  let maxAt = valid[0].t
  let sum = 0
  for (const p of valid) {
    if (p.v < min) min = p.v
    if (p.v > max) {
      max = p.v
      maxAt = p.t
    }
    sum += p.v
  }
  const last = valid[valid.length - 1]

  return { count: valid.length, min, max, maxAt, mean: sum / valid.length, last: last.v, lastAt: last.t }
}

export interface MatrixCell {
  /** 0..23 en la zona horaria del usuario. */
  hour: number
  /** 1 = lunes … 7 = domingo. */
  weekday: number
  value: number | null
  samples: number
}

/** Siempre 168 celdas (7 x 24), en orden weekday asc, hour asc. */
export function hourWeekdayMatrix(points: ChartPoint[], timeZone: string): MatrixCell[] {
  const sums: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0))
  const counts: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0))

  for (const p of points) {
    if (p.v === null) continue
    const dt = DateTime.fromISO(p.t, { zone: 'utc' }).setZone(timeZone)
    if (!dt.isValid) continue
    const weekdayIndex = dt.weekday - 1
    sums[weekdayIndex][dt.hour] += p.v
    counts[weekdayIndex][dt.hour] += 1
  }

  const cells: MatrixCell[] = []
  for (let weekday = 1; weekday <= 7; weekday++) {
    for (let hour = 0; hour < 24; hour++) {
      const samples = counts[weekday - 1][hour]
      cells.push({ hour, weekday, value: samples ? sums[weekday - 1][hour] / samples : null, samples })
    }
  }
  return cells
}

export interface Bucket {
  label: string
  value: number | null
  samples: number
}

/** 24 cubos, etiqueta '00 h' … '23 h'. */
export function meanByHour(points: ChartPoint[], timeZone: string): Bucket[] {
  const sums = Array(24).fill(0)
  const counts = Array(24).fill(0)

  for (const p of points) {
    if (p.v === null) continue
    const dt = DateTime.fromISO(p.t, { zone: 'utc' }).setZone(timeZone)
    if (!dt.isValid) continue
    sums[dt.hour] += p.v
    counts[dt.hour] += 1
  }

  return Array.from({ length: 24 }, (_, hour) => ({
    label: `${String(hour).padStart(2, '0')} h`,
    value: counts[hour] ? sums[hour] / counts[hour] : null,
    samples: counts[hour],
  }))
}

/** 7 cubos, etiqueta con el nombre largo del dia (lunes primero). */
export function meanByWeekday(points: ChartPoint[], timeZone: string): Bucket[] {
  const sums = Array(7).fill(0)
  const counts = Array(7).fill(0)

  for (const p of points) {
    if (p.v === null) continue
    const dt = DateTime.fromISO(p.t, { zone: 'utc' }).setZone(timeZone)
    if (!dt.isValid) continue
    const index = dt.weekday - 1
    sums[index] += p.v
    counts[index] += 1
  }

  return Array.from({ length: 7 }, (_, index) => {
    const weekday = index + 1
    return {
      label: t(`dashboards.lidar.weekday.${weekday}`),
      value: counts[index] ? sums[index] / counts[index] : null,
      samples: counts[index],
    }
  })
}

/**
 * Incrementos entre intervalos para contadores acumulativos. Un descenso significa reinicio
 * del contador, no un valor negativo: se devuelve null.
 */
export function incrementsOf(points: ChartPoint[]): ChartPoint[] {
  const out: ChartPoint[] = []
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1]
    const b = points[i]
    const v = b.v !== null && a.v !== null && b.v >= a.v ? b.v - a.v : null
    out.push({ t: b.t, v })
  }
  return out
}

export interface Aligned {
  times: string[]
  values: Record<string, (number | null)[]>
}

/** Rejilla comun: union ordenada de marcas, y cada serie proyectada sobre ella. */
export function alignSeries(series: Record<string, ChartPoint[]>): Aligned {
  const timesSet = new Set<string>()
  for (const points of Object.values(series)) {
    for (const p of points) timesSet.add(p.t)
  }
  const times = [...timesSet].sort()

  const values: Record<string, (number | null)[]> = {}
  for (const [key, points] of Object.entries(series)) {
    const byTime = new Map(points.map((p) => [p.t, p.v]))
    values[key] = times.map((time) => byTime.get(time) ?? null)
  }

  return { times, values }
}

export function occupancyRatio(value: number | null, capacity: number | null): number | null {
  return capacity && capacity > 0 && value !== null ? value / capacity : null
}

/** 0..4, el mismo indice que usa `occupancyColor`. */
export function levelIndex(ratio: number | null): number {
  return Math.round(Math.min(1, Math.max(0, ratio ?? 0)) * 4)
}

const LEVEL_SUFFIXES = ['veryLow', 'low', 'medium', 'high', 'veryHigh']

/** Clave i18n del nivel: 'dashboards.lidar.level.veryLow' … '.veryHigh'. */
export function levelKey(ratio: number | null): string {
  return `dashboards.lidar.level.${LEVEL_SUFFIXES[levelIndex(ratio)]}`
}

/** Amplia la ventana hacia el futuro, para pedir la parte prevista. */
export function extendRange(range: DateRange, hours: number): DateRange {
  const end = DateTime.fromISO(range.end, { zone: 'utc' }).plus({ hours })
  return { start: range.start, end: end.toISO({ suppressMilliseconds: true }) ?? range.end }
}
