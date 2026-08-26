import { DateTime } from 'luxon'
import type { Aggregation } from '@/types'

export type RangePresetId = '24h' | '7d' | '30d' | '90d' | '365d'

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
  { id: '24h', hours: HOURS_PER_DAY, labelKey: 'dashboards.range.24h' },
  { id: '7d', hours: HOURS_PER_DAY * 7, labelKey: 'dashboards.range.7d' },
  { id: '30d', hours: HOURS_PER_DAY * 30, labelKey: 'dashboards.range.30d' },
  { id: '90d', hours: HOURS_PER_DAY * 90, labelKey: 'dashboards.range.90d' },
  { id: '365d', hours: HOURS_PER_DAY * 365, labelKey: 'dashboards.range.365d' },
]

export const DEFAULT_RANGE: RangePresetId = '24h'

const FALLBACK_ZONE = 'Europe/Madrid'

const toUtcIso = (dt: DateTime): string => dt.toUTC().toISO({ suppressMilliseconds: true }) ?? ''

export function resolveRange(input: RangeInput, timeZone?: string): DateRange {
  if (typeof input !== 'string') return input
  const preset = RANGE_PRESETS.find((p) => p.id === input) ?? RANGE_PRESETS[0]
  const end = DateTime.now().setZone(timeZone || FALLBACK_ZONE)
  return { start: toUtcIso(end.minus({ hours: preset.hours })), end: toUtcIso(end) }
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
