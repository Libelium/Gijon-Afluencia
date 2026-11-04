import { describe, expect, it } from 'vitest'
import {
  EVENT_CATALOG,
  MAX_EVENT_HOURS,
  SHOULDER_WEIGHT,
  WEATHER_FACTORS,
  eventPeak,
  eventStartHours,
  eventDayStarts,
  eventWeight,
  referenceOf,
  registeredScenarioEvents,
  simulate,
  summariseScenario,
  type ScenarioEvent,
} from './eventSimulation'

const hour = (h: number) => `2026-11-03T${String(h).padStart(2, '0')}:00:00.000Z`
const ms = (h: number) => Date.parse(hour(h))
const times = [16, 17, 18, 19, 20, 21, 22, 23].map(hour)

const event = (over: Partial<ScenarioEvent> = {}): ScenarioEvent => ({
  id: 1,
  kind: 'concert',
  weather: 'clear',
  intensity: 1,
  start: hour(19),
  hours: 2,
  ...over,
})

const share = (kind: ScenarioEvent['kind']) => EVENT_CATALOG.find((s) => s.kind === kind)!.peakShare

describe('eventWeight', () => {
  it('pesa entero mientras dura y a medias la hora anterior y la posterior', () => {
    const e = event()
    expect([17, 18, 19, 20, 21, 22].map((h) => eventWeight(e, ms(h)))).toEqual([
      0,
      SHOULDER_WEIGHT,
      1,
      1,
      SHOULDER_WEIGHT,
      0,
    ])
  })
})

describe('eventos de varios días', () => {
  it('se repiten cada día a la misma hora, con sus horas a medias', () => {
    const e = event({ days: 3 })
    const later = (days: number, h: number) => ms(h) + days * 24 * 3_600_000
    expect([18, 19, 20, 21].map((h) => eventWeight(e, later(1, h)))).toEqual([SHOULDER_WEIGHT, 1, 1, SHOULDER_WEIGHT])
    expect([19, 20].map((h) => eventWeight(e, later(2, h)))).toEqual([1, 1])
    expect(eventWeight(e, later(3, 19))).toBe(0) // el cuarto día ya no
  })

  it('cruzando el cambio de hora sigue empezando a la misma hora local', () => {
    // El 25 de octubre de 2026 Madrid pasa de UTC+2 a UTC+1.
    const market = event({ start: '2026-10-24T08:00:00.000Z', hours: 11, days: 3 })
    expect(eventDayStarts(market, 'Europe/Madrid').map((t) => new Date(t).toISOString())).toEqual([
      '2026-10-24T08:00:00.000Z',
      '2026-10-25T09:00:00.000Z',
      '2026-10-26T09:00:00.000Z',
    ])
  })

  it('si la hora de después de un día es la de antes del siguiente, cuenta una vez', () => {
    const e = event({ start: hour(0), hours: 23, days: 2 })
    expect(eventWeight(e, ms(23))).toBe(SHOULDER_WEIGHT)
  })

  it('un mercado de todo el día durante una semana pesa entero sin huecos', () => {
    const e = event({ kind: 'market', start: hour(0), hours: MAX_EVENT_HOURS, days: 7 })
    const week = Array.from({ length: 7 * 24 }, (_, i) => ms(0) + i * 3_600_000)
    expect(week.every((t) => eventWeight(e, t) === 1)).toBe(true)
    expect(eventWeight(e, ms(0) - 3_600_000)).toBe(SHOULDER_WEIGHT)
    expect(eventWeight(e, ms(0) + 7 * 24 * 3_600_000)).toBe(SHOULDER_WEIGHT)
  })

  it('una semana de mercado suma cada día sobre la previsión', () => {
    const week = Array.from({ length: 7 * 24 }, (_, i) => new Date(ms(0) + i * 3_600_000).toISOString())
    const base = week.map(() => 10)
    const simulated = simulate(week, base, [event({ kind: 'market', start: hour(10), hours: 11, days: 7 })], 100)
    const extra = Math.round(10 + 100 * share('market'))
    expect([0, 1, 2, 3, 4, 5, 6].map((d) => simulated[d * 24 + 15])).toEqual(Array(7).fill(extra))
    expect(simulated[3]).toBe(10)
  })
})

describe('eventPeak', () => {
  it('es la fraccion del aforo de su tipo, por la intensidad y por el tiempo', () => {
    expect(eventPeak(event(), 100)).toBeCloseTo(100 * share('concert'))
    expect(eventPeak(event({ intensity: 2, weather: 'rain' }), 100)).toBeCloseTo(
      100 * share('concert') * 2 * WEATHER_FACTORS.rain,
    )
  })

  it('cada tipo de evento tiene su peso', () => {
    expect(eventPeak(event({ kind: 'festival' }), 100)).toBeGreaterThan(eventPeak(event({ kind: 'market' }), 100))
  })
})

describe('referenceOf', () => {
  it('usa el aforo de la zona cuando lo publica', () => {
    expect(referenceOf(168, [10, 80])).toBe(168)
  })

  it('sin aforo, el maximo de la prevision', () => {
    expect(referenceOf(null, [10, null, 80])).toBe(80)
    expect(referenceOf(0, [10, 40])).toBe(40)
  })

  it('sin aforo ni prevision no hay referencia', () => {
    expect(referenceOf(null, [null, 0])).toBeNull()
    expect(referenceOf(null, [])).toBeNull()
  })
})

describe('simulate', () => {
  const base = [20, 30, 40, 50, 50, 40, 30, null]

  it('sin eventos devuelve la prevision', () => {
    expect(simulate(times, base, [], 100)).toEqual(base)
  })

  it('suma el evento con su forma: rampa, pleno y rampa', () => {
    const peak = 100 * share('concert')
    expect(simulate(times, base, [event()], 100)).toEqual([
      20,
      30,
      Math.round(40 + peak * SHOULDER_WEIGHT),
      Math.round(50 + peak),
      Math.round(50 + peak),
      Math.round(40 + peak * SHOULDER_WEIGHT),
      30,
      null,
    ])
  })

  it('dos eventos a la misma hora se suman', () => {
    const both = simulate(times, base, [event(), event({ id: 2, kind: 'food' })], 100)
    expect(both[3]).toBe(Math.round(50 + 100 * share('concert') + 100 * share('food')))
  })

  it('donde no hay prevision no inventa nada', () => {
    expect(simulate(times, base, [event({ start: hour(23), hours: 1 })], 100)[7]).toBeNull()
  })
})

describe('eventStartHours', () => {
  it('ofrece las horas con prevision desde la hora en curso', () => {
    const base = [1, 1, null, 1, 1, 1, 1, 1]
    expect(eventStartHours(times, base, ms(17) + 20 * 60_000)).toEqual([hour(17), ...[19, 20, 21, 22, 23].map(hour)])
  })
})

describe('summariseScenario', () => {
  const base = [20, 30, 40, 50, 50, 40, 30, null]

  it('da el pico con eventos, su hora y lo que ponen los eventos en ella', () => {
    const simulated = simulate(times, base, [event()], 100)
    const summary = summariseScenario(times, base, simulated, 100)
    expect(summary.peak).toBe(110)
    expect(summary.peakAt).toBe(hour(19))
    expect(summary.extraAtPeak).toBe(60)
    expect(summary.hoursOverCapacity).toBe(2)
  })

  it('sin aforo no cuenta horas por encima', () => {
    expect(summariseScenario(times, base, base, null).hoursOverCapacity).toBeNull()
  })

  it('sin prevision no hay pico', () => {
    expect(summariseScenario(['x'], [null], [null], 100)).toEqual({
      peak: null,
      peakAt: null,
      extraAtPeak: null,
      hoursOverCapacity: 0,
    })
  })
})

describe('registeredScenarioEvents', () => {
  const tz = 'Europe/Madrid'
  const raw = (list: unknown[]) => JSON.stringify(list)

  it('un mercado de varios días es un evento que se repite cada día, a sus horas locales', () => {
    const events = registeredScenarioEvents(
      raw([
        { date: '2026-12-14', endDate: '2026-12-20', type: 'market', startHour: 10, endHour: 21, notes: 'Navidad' },
        { date: '2026-12-31', type: 'concert', startHour: 22, endHour: 24 },
      ]),
      tz,
    )
    expect(events.map((e) => [e.start, e.hours, e.days, e.kind, e.registered])).toEqual([
      ['2026-12-14T09:00:00.000Z', 11, 7, 'market', true], // 10:00 en Madrid, UTC+1 en diciembre
      ['2026-12-31T21:00:00.000Z', 2, 1, 'concert', true],
    ])
    expect(events[0].notes).toBe('Navidad')
    expect(new Set(events.map((e) => e.id)).size).toBe(2)
    expect(events.every((e) => e.id < 0)).toBe(true) // no chocan con los que añade quien simula
  })

  it('los días de un evento que cruza el cambio de hora se cuentan por calendario', () => {
    const [event] = registeredScenarioEvents(raw([{ date: '2026-10-24', endDate: '2026-10-26', type: 'market' }]), tz)
    expect(event.days).toBe(3)
  })

  it('sin horas dibuja un día de mercado y un tipo desconocido se toma por mercado', () => {
    const [event] = registeredScenarioEvents(raw([{ date: '2026-12-14', type: 'feria_del_libro' }]), tz)
    expect(event.kind).toBe('market')
    expect(event.start).toBe('2026-12-14T09:00:00.000Z')
    expect(event.hours).toBe(11)
  })

  it('un tipo del catálogo se conserva', () => {
    const [event] = registeredScenarioEvents(raw([{ date: '2026-12-14', type: 'concert', startHour: 20, endHour: 23 }]), tz)
    expect(event.kind).toBe('concert')
    expect(event.hours).toBe(3)
  })

  it('lo que no se entiende no rompe nada: no hay eventos', () => {
    expect(registeredScenarioEvents('no es JSON', tz)).toEqual([])
    expect(registeredScenarioEvents('{"date":"2026-12-14"}', tz)).toEqual([])
    expect(registeredScenarioEvents(undefined, tz)).toEqual([])
    expect(registeredScenarioEvents(raw([{ date: 'ayer' }, { date: '2026-12-14', endDate: '2026-12-01' }]), tz)).toEqual([])
    expect(registeredScenarioEvents(raw([{ date: '2026-12-14', startHour: 21, endHour: 10 }]), tz)).toEqual([])
  })

  it('suma como cualquier otro evento', () => {
    const [event] = registeredScenarioEvents(raw([{ date: '2026-11-03', type: 'market', startHour: 18, endHour: 20 }]), 'UTC')
    const simulated = simulate(times, [20, 30, 40, 50, 50, 40, 30, null], [event], 100)
    expect(simulated[2]).toBe(Math.round(40 + 100 * share('market')))
  })
})
