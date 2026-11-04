import { describe, expect, it } from 'vitest'
import {
  EVENT_CATALOG,
  SHOULDER_WEIGHT,
  WEATHER_FACTORS,
  eventPeak,
  eventStartHours,
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

  it('un mercado de varios días es un evento por día, a sus horas locales', () => {
    const events = registeredScenarioEvents(
      raw([{ date: '2026-12-14', endDate: '2026-12-15', type: 'market', startHour: 10, endHour: 21, notes: 'Navidad' }]),
      tz,
    )
    expect(events.map((e) => [e.start, e.hours, e.kind, e.registered])).toEqual([
      ['2026-12-14T09:00:00.000Z', 11, 'market', true], // 10:00 en Madrid, UTC+1 en diciembre
      ['2026-12-15T09:00:00.000Z', 11, 'market', true],
    ])
    expect(events[0].notes).toBe('Navidad')
    expect(new Set(events.map((e) => e.id)).size).toBe(2)
    expect(events.every((e) => e.id < 0)).toBe(true) // no chocan con los que añade quien simula
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
