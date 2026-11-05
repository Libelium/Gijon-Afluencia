import { DateTime } from 'luxon'
import type { Aggregation } from '@/types'

export type RangePresetId = '1h' | '6h' | '12h' | '24h' | '7d' | '15d' | '30d' | '90d' | '365d'

export interface DateRange {
  /** Instante ISO 8601 en UTC. */
  start: string
  end: string
}

/** El rango se puede pedir ya resuelto o como preajuste relativo a «ahora». */
export type RangeInput = RangePresetId | DateRange

export interface RangePreset {
  id: RangePresetId
  hours: number
  labelKey: string
}

const HOURS_PER_DAY = 24

export const RANGE_PRESETS: RangePreset[] = [
  { id: '1h', hours: 1, labelKey: 'dashboards.range.1h' },
  { id: '6h', hours: 6, labelKey: 'dashboards.range.6h' },
  { id: '12h', hours: 12, labelKey: 'dashboards.range.12h' },
  { id: '24h', hours: HOURS_PER_DAY, labelKey: 'dashboards.range.24h' },
  { id: '7d', hours: HOURS_PER_DAY * 7, labelKey: 'dashboards.range.7d' },
  { id: '15d', hours: HOURS_PER_DAY * 15, labelKey: 'dashboards.range.15d' },
  { id: '30d', hours: HOURS_PER_DAY * 30, labelKey: 'dashboards.range.30d' },
  { id: '90d', hours: HOURS_PER_DAY * 90, labelKey: 'dashboards.range.90d' },
  { id: '365d', hours: HOURS_PER_DAY * 365, labelKey: 'dashboards.range.365d' },
]

export const DEFAULT_RANGE: RangePresetId = '24h'

const FALLBACK_ZONE = 'Europe/Madrid'

const toUtcIso = (dt: DateTime): string => dt.toUTC().toISO({ suppressMilliseconds: true }) ?? ''

export function resolveRange(input: RangeInput, timeZone?: string): DateRange {
  if (typeof input !== 'string') return input
  const preset =
    RANGE_PRESETS.find((p) => p.id === input) ?? RANGE_PRESETS.find((p) => p.id === DEFAULT_RANGE)!
  const end = DateTime.now().setZone(timeZone || FALLBACK_ZONE)
  return { start: toUtcIso(end.minus({ hours: preset.hours })), end: toUtcIso(end) }
}

/**
 * Horas por delante de «ahora» que publica el componente de prevision
 * (`PREDICTION_HORIZON_HOURS` en predictions). Si se cambia alli hay que cambiarlo aqui: es
 * hasta donde piden las graficas, y sin ampliar la ventana la parte prevista no se veria.
 */
export const FORECAST_HORIZON_HOURS = 24

/** Lo que abarca el simulador de escenarios: una semana, para poder poner una semana de mercado. */
export const SCENARIO_HORIZON_HOURS = 7 * 24

/** Amplia la ventana hacia el futuro, para pedir la parte prevista. */
export function extendRange(range: DateRange, hours: number): DateRange {
  const end = toUtcIso(DateTime.fromISO(range.end, { zone: 'utc' }).plus({ hours }))
  return { start: range.start, end: end || range.end }
}

export function rangeHours(range: DateRange): number {
  const start = DateTime.fromISO(range.start)
  const end = DateTime.fromISO(range.end)
  if (!start.isValid || !end.isValid) return 0
  return Math.max(0, end.diff(start, 'hours').hours)
}

export interface AggregationOption {
  type: Aggregation
  interval: string
}

/**
 * aether-link exige duraciones ISO 8601 y rechaza anos y meses, asi que los intervalos
 * se expresan siempre en horas.
 */
const INTERVAL_HOUR = 'PT1H'
const INTERVAL_DAY = 'PT24H'
const INTERVAL_WEEK = 'PT168H'

/** Funciones que acepta el servicio de datos; el resto degrada a la media. */
const SUPPORTED_FUNCTIONS: Aggregation[] = ['mean', 'max', 'min', 'sum']

function aggregationFunction(requested?: string): Aggregation {
  const found = SUPPORTED_FUNCTIONS.find((fn) => fn === requested)
  return found ?? 'mean'
}

/**
 * Un rango amplio sin agregar devuelve mas puntos de los que un grafico puede dibujar
 * y castiga al servicio de datos: el intervalo crece con la ventana solicitada.
 */
export function autoAggregation(range: DateRange, requestedFunction?: string): AggregationOption | null {
  const hours = rangeHours(range)
  if (hours <= HOURS_PER_DAY) return null

  const type = aggregationFunction(requestedFunction)
  if (hours <= HOURS_PER_DAY * 31) return { type, interval: INTERVAL_HOUR }
  if (hours <= HOURS_PER_DAY * 366) return { type, interval: INTERVAL_DAY }
  return { type, interval: INTERVAL_WEEK }
}

/** Solo se entienden duraciones en horas: es lo unico que acepta el servicio de datos. */
const INTERVAL_PATTERN = /^PT(\d+)H$/i

export function intervalHours(interval?: string | null): number | null {
  const match = INTERVAL_PATTERN.exec((interval ?? '').trim())
  if (!match) return null
  const hours = Number(match[1])
  return Number.isFinite(hours) && hours > 0 ? hours : null
}

/**
 * Agregacion efectiva de una serie: se respeta el intervalo guardado cuando es igual o mas
 * grueso que el automatico. Uno mas fino devuelve mas puntos de los que deja pasar el limite y
 * dibujaria solo el final del rango, que es peor que agregar mas.
 */
export function resolveAggregation(
  range: DateRange,
  requestedFunction?: string,
  requestedInterval?: string | null,
): AggregationOption | null {
  const auto = autoAggregation(range, requestedFunction)
  const hours = intervalHours(requestedInterval)
  if (!hours) return auto

  const type = aggregationFunction(requestedFunction)
  const autoHours = auto ? (intervalHours(auto.interval) ?? 0) : 0
  return hours >= autoHours ? { type, interval: `PT${hours}H` } : auto
}

/** Igual que el preajuste mas largo: mas dias castigan al servicio de datos. */
export const MAX_CUSTOM_DAYS = 366

/**
 * Rango de dias completos (`yyyy-MM-dd`, ambos incluidos) en la zona del dashboard. Devuelve null
 * si una fecha no se entiende, si van al reves o si pasan de MAX_CUSTOM_DAYS.
 */
export function customRange(startDay: string, endDay: string, timeZone?: string): DateRange | null {
  const zone = timeZone || FALLBACK_ZONE
  const start = DateTime.fromISO(startDay, { zone }).startOf('day')
  // El final es el inicio del dia siguiente para que el ultimo dia entre entero.
  const end = DateTime.fromISO(endDay, { zone }).startOf('day').plus({ days: 1 })
  if (!start.isValid || !end.isValid || end <= start) return null
  if (end.diff(start, 'days').days > MAX_CUSTOM_DAYS) return null
  return { start: toUtcIso(start), end: toUtcIso(end) }
}

/** Dias que toca un rango, para rellenar el selector. El final es exclusivo: de ahi el milisegundo. */
export function rangeDays(range: DateRange, timeZone?: string): { start: string; end: string } | null {
  const zone = timeZone || FALLBACK_ZONE
  const start = DateTime.fromISO(range.start, { zone }).toISODate()
  const end = DateTime.fromISO(range.end, { zone }).minus({ milliseconds: 1 }).toISODate()
  return start && end ? { start, end } : null
}
