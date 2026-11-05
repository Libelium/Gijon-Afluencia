import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  FORECAST_HORIZON_HOURS,
  autoAggregation,
  extendRange,
  intervalHours,
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
