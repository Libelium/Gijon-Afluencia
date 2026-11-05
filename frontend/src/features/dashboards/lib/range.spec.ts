import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  FORECAST_HORIZON_HOURS,
  MAX_CUSTOM_DAYS,
  autoAggregation,
  customRange,
  extendRange,
  intervalHours,
  rangeDays,
  rangeHours,
  resolveAggregation,
  resolveRange,
} from './range'

const DAY = { start: '2026-10-26T12:30:00Z', end: '2026-10-27T12:30:00Z' }

describe('resolveRange', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-10-27T12:30:00Z'))
  })
  afterEach(() => vi.useRealTimers())

  it('un preajuste acaba en «ahora»: por eso hay que ampliarlo para ver una prevision', () => {
    expect(resolveRange('24h', 'Europe/Madrid')).toEqual(DAY)
  })

  it('los preajustes cortos piden solo sus horas', () => {
    expect(resolveRange('1h', 'Europe/Madrid')).toEqual({ start: '2026-10-27T11:30:00Z', end: DAY.end })
    expect(resolveRange('6h', 'Europe/Madrid')).toEqual({ start: '2026-10-27T06:30:00Z', end: DAY.end })
    expect(resolveRange('12h', 'Europe/Madrid')).toEqual({ start: '2026-10-27T00:30:00Z', end: DAY.end })
  })

  it('un preajuste desconocido cae en el de por defecto', () => {
    expect(resolveRange('xyz' as never)).toEqual(DAY)
  })

  it('un rango ya resuelto se devuelve tal cual', () => {
    const range = { start: '2026-01-01T00:00:00Z', end: '2026-01-02T00:00:00Z' }
    expect(resolveRange(range)).toBe(range)
  })
})

describe('customRange', () => {
  it('un solo dia va de su medianoche a la del dia siguiente, en la zona del dashboard', () => {
    expect(customRange('2026-07-15', '2026-07-15', 'Europe/Madrid')).toEqual({
      start: '2026-07-14T22:00:00Z',
      end: '2026-07-15T22:00:00Z',
    })
  })

  it('varios dias incluyen el ultimo entero', () => {
    expect(customRange('2026-01-10', '2026-01-12', 'Europe/Madrid')).toEqual({
      start: '2026-01-09T23:00:00Z',
      end: '2026-01-12T23:00:00Z',
    })
  })

  it('el dia del cambio de hora dura 25 horas', () => {
    const range = customRange('2026-10-25', '2026-10-25', 'Europe/Madrid')
    expect(range).toEqual({ start: '2026-10-24T22:00:00Z', end: '2026-10-25T23:00:00Z' })
    expect(rangeHours(range!)).toBe(25)
  })

  it('sin zona usa la de Madrid', () => {
    expect(customRange('2026-07-15', '2026-07-15')).toEqual(customRange('2026-07-15', '2026-07-15', 'Europe/Madrid'))
  })

  it('rechaza fechas ilegibles, al reves o mas largas que el maximo', () => {
    expect(customRange('no-es-una-fecha', '2026-01-01')).toBeNull()
    expect(customRange('2026-01-12', '2026-01-10')).toBeNull()
    // 2024 es bisiesto: del 1 de enero al 1 de enero siguiente, ambos incluidos, son 367 dias.
    expect(customRange('2024-01-01', '2025-01-01')).toBeNull()
    expect(MAX_CUSTOM_DAYS).toBe(366)
    expect(customRange('2025-01-01', '2026-01-01')).not.toBeNull()
  })
})

describe('rangeDays', () => {
  it('devuelve los mismos dias con los que se hizo un rango personalizado', () => {
    const range = customRange('2026-10-24', '2026-10-25', 'Europe/Madrid')!
    expect(rangeDays(range, 'Europe/Madrid')).toEqual({ start: '2026-10-24', end: '2026-10-25' })
  })

  it('un preajuste acaba en el dia de «ahora» en la zona del dashboard', () => {
    expect(rangeDays(DAY, 'Europe/Madrid')).toEqual({ start: '2026-10-26', end: '2026-10-27' })
  })

  it('un rango ilegible no da dias', () => {
    expect(rangeDays({ start: 'x', end: 'y' })).toBeNull()
  })
})

describe('extendRange', () => {
  it('alarga solo el final, el horizonte que publica la prevision', () => {
    expect(extendRange(DAY, FORECAST_HORIZON_HOURS)).toEqual({
      start: DAY.start,
      end: '2026-10-28T12:30:00Z',
    })
  })

  it('devuelve el final en UTC y sin milisegundos aunque llegue con desplazamiento', () => {
    expect(extendRange({ start: DAY.start, end: '2026-10-27T14:30:00.000+02:00' }, 1).end).toBe(
      '2026-10-27T13:30:00Z',
    )
  })

  it('un final ilegible se deja como estaba', () => {
    expect(extendRange({ start: 'a', end: 'no-es-una-fecha' }, 24)).toEqual({
      start: 'a',
      end: 'no-es-una-fecha',
    })
  })

  it('un dia mas el horizonte sigue agregandose por horas', () => {
    const range = extendRange(DAY, FORECAST_HORIZON_HOURS)
    expect(rangeHours(range)).toBe(48)
    expect(autoAggregation(range)?.interval).toBe('PT1H')
  })
})

describe('agregacion', () => {
  it('sin agregar hasta un dia; por horas, dias o semanas segun la ventana', () => {
    expect(autoAggregation(DAY)).toBeNull()
    expect(autoAggregation({ start: '2026-01-01T00:00:00Z', end: '2026-03-01T00:00:00Z' })?.interval).toBe('PT24H')
    expect(autoAggregation({ start: '2024-01-01T00:00:00Z', end: '2026-01-01T00:00:00Z' })?.interval).toBe('PT168H')
  })

  it('una funcion que el servicio no acepta degrada a la media', () => {
    expect(autoAggregation(extendRange(DAY, 24), 'median')?.type).toBe('mean')
  })

  it('solo entiende duraciones en horas', () => {
    expect(intervalHours('PT6H')).toBe(6)
    expect(intervalHours('P1D')).toBeNull()
    expect(intervalHours(null)).toBeNull()
  })

  it('respeta el intervalo guardado si es mas grueso que el automatico, y si no usa el automatico', () => {
    const twoDays = extendRange(DAY, 24)
    expect(resolveAggregation(twoDays, 'max', 'PT6H')).toEqual({ type: 'max', interval: 'PT6H' })
    expect(resolveAggregation({ start: '2026-01-01T00:00:00Z', end: '2026-03-01T00:00:00Z' }, 'sum', 'PT1H')).toEqual({
      type: 'sum',
      interval: 'PT24H',
    })
    expect(resolveAggregation(twoDays, 'sum')).toEqual({ type: 'sum', interval: 'PT1H' })
  })

  it('un rango con fechas ilegibles mide cero horas', () => {
    expect(rangeHours({ start: 'x', end: 'y' })).toBe(0)
  })
})
