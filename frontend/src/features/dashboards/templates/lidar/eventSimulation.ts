import { DateTime } from 'luxon'
import { toMillis } from '../../charts/chartOptions'

/**
 * Simulacion de escenarios con eventos sobre la prevision horaria de una zona. El modelo es
 * aditivo: a la prevision de cada hora se le suman las personas que atrae cada evento en esa hora.
 *
 * Lo que atrae un evento en su hora punta es una fraccion del tamaño de la zona (su aforo) segun
 * el tipo de evento, multiplicada por la intensidad que elige quien simula y por el efecto del
 * tiempo. Durante el evento pesa entero, y la hora anterior y la posterior a medias: la gente llega
 * antes y tarda en irse. Varios eventos a la misma hora se suman. Un evento de varios dias (una
 * semana de mercado) se repite cada dia a la misma hora local.
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
/** Un dia entero: un mercado que no cierra en todo el dia. */
export const MAX_EVENT_HOURS = 24
/** Lo que alcanza la prevision: una semana. */
export const MAX_EVENT_DAYS = 7

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
  /** Horas que dura cada dia: de 1 a MAX_EVENT_HOURS los que se simulan, sin tope los registrados. */
  hours: number
  /** Dias seguidos que se repite, a la misma hora local; 1 si falta. */
  days?: number
  /** Viene del registro de eventos de la plataforma, no lo ha añadido quien simula. */
  registered?: boolean
  /** Lo que el registro dice del evento, para mostrarlo. */
  notes?: string
}

/** Horas que se dibujan de un evento registrado que no dice las suyas: un dia de mercado. */
export const REGISTERED_DEFAULT_HOURS = { start: 10, end: 21 } as const

/** Un evento tal y como lo publica la entidad de prevision en `registeredEvents`. */
interface RegisteredEvent {
  date: string
  endDate?: string
  type?: string
  startHour?: number | null
  endHour?: number | null
  notes?: string
}

const isKind = (value: unknown): value is EventKind => EVENT_CATALOG.some((spec) => spec.kind === value)

const isHour = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 24

/**
 * Los eventos registrados de la zona, listos para sumarse a la prevision: uno por fila del
 * registro, que se repite cada dia de su rango. Llegan como el texto JSON del atributo
 * `registeredEvents`: el modelo predice el dia normal y el evento se dibuja encima. El tipo vale si
 * es uno del catalogo y si no se toma por un mercado; las fechas son dias locales de `timeZone`. Un
 * texto que no se entiende no rompe el panel: no hay eventos.
 */
export function registeredScenarioEvents(raw: unknown, timeZone: string): ScenarioEvent[] {
  let list: unknown
  try {
    list = typeof raw === 'string' ? JSON.parse(raw) : raw
  } catch {
    return []
  }
  if (!Array.isArray(list)) return []

  const events: ScenarioEvent[] = []
  for (const item of list as RegisteredEvent[]) {
    const first = DateTime.fromISO(String(item?.date ?? ''), { zone: timeZone })
    const last = item?.endDate ? DateTime.fromISO(item.endDate, { zone: timeZone }) : first
    if (!first.isValid || !last.isValid || last < first) continue
    const startHour = isHour(item.startHour) ? item.startHour : REGISTERED_DEFAULT_HOURS.start
    const endHour = isHour(item.endHour) ? item.endHour : REGISTERED_DEFAULT_HOURS.end
    if (endHour <= startHour) continue
    events.push({
      id: -(events.length + 1),
      kind: isKind(item.type) ? item.type : 'market',
      weather: 'clear',
      intensity: DEFAULT_INTENSITY,
      start: first.set({ hour: startHour, minute: 0, second: 0, millisecond: 0 }).toUTC().toISO()!,
      hours: endHour - startHour,
      days: Math.round(last.startOf('day').diff(first.startOf('day'), 'days').days) + 1,
      registered: true,
      notes: item.notes || undefined,
    })
  }
  return events
}

/**
 * Comienzo de cada dia del evento, en milisegundos. Se suma un dia de calendario en `timeZone`, no
 * 24 horas: un mercado que cruza el cambio de hora sigue abriendo a las 10:00 locales.
 */
export function eventDayStarts(event: ScenarioEvent, timeZone = 'UTC'): number[] {
  const first = DateTime.fromMillis(toMillis(event.start), { zone: timeZone })
  return Array.from({ length: Math.max(1, event.days ?? 1) }, (_, day) => first.plus({ days: day }).toMillis())
}

/**
 * Peso del evento en la hora que empieza en `hourMs`: 1 mientras dura, a medias justo antes y
 * despues, cada dia que se repite. Si el final de un dia toca el comienzo del siguiente (un evento
 * de 24 horas), cuenta el mayor: no se suma dos veces la misma gente.
 */
export function eventWeight(event: ScenarioEvent, hourMs: number, timeZone = 'UTC'): number {
  let weight = 0
  for (const start of eventDayStarts(event, timeZone)) {
    const end = start + event.hours * HOUR_MS
    if (hourMs >= start && hourMs < end) return 1
    if ((hourMs >= start - HOUR_MS && hourMs < start) || (hourMs >= end && hourMs < end + HOUR_MS)) {
      weight = SHOULDER_WEIGHT
    }
  }
  return weight
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
  timeZone = 'UTC',
): (number | null)[] {
  return times.map((iso, i) => {
    const value = base[i]
    if (!isValue(value)) return null
    const hour = toMillis(iso)
    const extra = events.reduce(
      (sum, event) => sum + eventPeak(event, reference) * eventWeight(event, hour, timeZone),
      0,
    )
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
