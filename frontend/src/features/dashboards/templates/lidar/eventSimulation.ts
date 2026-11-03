import { toMillis } from '../../charts/chartOptions'

/**
 * Simulacion de escenarios con eventos sobre la prevision horaria de una zona. El modelo es
 * aditivo: a la prevision de cada hora se le suman las personas que atrae cada evento en esa hora.
 *
 * Lo que atrae un evento en su hora punta es una fraccion del tamaño de la zona (su aforo) segun
 * el tipo de evento, multiplicada por la intensidad que elige quien simula y por el efecto del
 * tiempo. Durante el evento pesa entero, y la hora anterior y la posterior a medias: la gente llega
 * antes y tarda en irse. Varios eventos a la misma hora se suman.
 */

export type EventKind = 'concert' | 'festival' | 'sports' | 'localFestival' | 'food' | 'market'
export type Weather = 'clear' | 'cloudy' | 'rain' | 'storm' | 'heat'

export interface EventSpec {
  kind: EventKind
  /** Personas de mas en la hora punta del evento, como fraccion del aforo de la zona. */
  peakShare: number
}

/**
 * Supuestos, no medidas: sirven para comparar escenarios entre si, no para anticipar una cifra
 * exacta. Si se llegan a medir eventos reales en las zonas, estos valores son lo que hay que
 * ajustar.
 */
export const EVENT_CATALOG: readonly EventSpec[] = [
  { kind: 'concert', peakShare: 0.6 },
  { kind: 'festival', peakShare: 0.8 },
  { kind: 'sports', peakShare: 0.5 },
  { kind: 'localFestival', peakShare: 0.7 },
  { kind: 'food', peakShare: 0.4 },
  { kind: 'market', peakShare: 0.3 },
]

/** Cuanta asistencia se mantiene segun el tiempo que haga. Tambien son supuestos. */
export const WEATHER_FACTORS: Readonly<Record<Weather, number>> = {
  clear: 1,
  cloudy: 0.9,
  rain: 0.6,
  storm: 0.4,
  heat: 0.8,
}

export const MIN_INTENSITY = 0.5
export const MAX_INTENSITY = 3
export const DEFAULT_INTENSITY = 1
export const MAX_EVENT_HOURS = 6

/** Peso de la hora anterior y de la posterior al evento. */
export const SHOULDER_WEIGHT = 0.5

const HOUR_MS = 3_600_000

export interface ScenarioEvent {
  id: number
  kind: EventKind
  weather: Weather
  intensity: number
  /** Comienzo de la primera hora del evento, ISO 8601. */
  start: string
  /** Horas que dura, de 1 a MAX_EVENT_HOURS. */
  hours: number
}

/** Peso del evento en la hora que empieza en `hourMs`: 1 mientras dura, a medias justo antes y despues. */
export function eventWeight(event: ScenarioEvent, hourMs: number): number {
  const start = toMillis(event.start)
  const end = start + event.hours * HOUR_MS
  if (hourMs >= start && hourMs < end) return 1
  if (hourMs >= start - HOUR_MS && hourMs < start) return SHOULDER_WEIGHT
  if (hourMs >= end && hourMs < end + HOUR_MS) return SHOULDER_WEIGHT
  return 0
}

/** Personas que suma un evento en su hora punta, para una zona del tamaño `reference`. */
export function eventPeak(event: ScenarioEvent, reference: number): number {
  const spec = EVENT_CATALOG.find((item) => item.kind === event.kind)
  return reference * (spec?.peakShare ?? 0) * event.intensity * WEATHER_FACTORS[event.weather]
}

const isValue = (value: number | null | undefined): value is number =>
  value !== null && value !== undefined && Number.isFinite(value)

/**
 * Tamaño de la zona al que se refieren los eventos: su aforo o, si no lo publica, el maximo de la
 * prevision. null si no hay ninguno de los dos y entonces no se puede simular.
 */
export function referenceOf(capacity: number | null, base: (number | null)[]): number | null {
  if (isValue(capacity) && capacity > 0) return capacity
  const values = base.filter(isValue)
  const peak = values.length ? Math.max(...values) : 0
  return peak > 0 ? peak : null
}

/** La prevision con los eventos sumados hora a hora. Donde no hay prevision no se inventa nada. */
export function simulate(
  times: string[],
  base: (number | null)[],
  events: ScenarioEvent[],
  reference: number,
): (number | null)[] {
  return times.map((iso, i) => {
    const value = base[i]
    if (!isValue(value)) return null
    const hour = toMillis(iso)
    const extra = events.reduce((sum, event) => sum + eventPeak(event, reference) * eventWeight(event, hour), 0)
    return Math.round(value + extra)
  })
}

/** Horas en las que puede empezar un evento: las que tienen prevision, desde la hora en curso. */
export function eventStartHours(times: string[], base: (number | null)[], nowMs: number): string[] {
  const currentHour = Math.floor(nowMs / HOUR_MS) * HOUR_MS
  return times.filter((iso, i) => isValue(base[i]) && toMillis(iso) >= currentHour)
}

export interface ScenarioSummary {
  /** Maximo de la prevision con eventos, o null si no hay prevision. */
  peak: number | null
  peakAt: string | null
  /** Personas de mas que ponen los eventos en esa hora. */
  extraAtPeak: number | null
  /** Horas por encima del aforo con eventos, o null si la zona no publica aforo. */
  hoursOverCapacity: number | null
}

export function summariseScenario(
  times: string[],
  base: (number | null)[],
  simulated: (number | null)[],
  capacity: number | null,
): ScenarioSummary {
  let peakIndex = -1
  simulated.forEach((value, i) => {
    if (isValue(value) && (peakIndex === -1 || value > (simulated[peakIndex] as number))) peakIndex = i
  })
  const hasCapacity = isValue(capacity) && capacity > 0
  return {
    peak: peakIndex === -1 ? null : (simulated[peakIndex] as number),
    peakAt: peakIndex === -1 ? null : times[peakIndex],
    extraAtPeak: peakIndex === -1 ? null : Math.round((simulated[peakIndex] as number) - (base[peakIndex] as number)),
    hoursOverCapacity: hasCapacity ? simulated.filter((value) => isValue(value) && value > capacity).length : null,
  }
}
