import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { measureTitle, timestampInfo } from './measures'

describe('timestampInfo', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-11-05T10:00:00Z'))
  })
  afterEach(() => vi.useRealTimers())

  it('una lectura pasada se dice en relativo', () => {
    const info = timestampInfo('2026-11-05T07:00:00Z', 'Europe/Madrid')
    expect(info.future).toBe(false)
    expect(info.text).toMatch(/^hace /)
  })

  it('una hora futura, la de una prevision, se da con fecha y hora en la zona pedida', () => {
    expect(timestampInfo('2026-11-06T00:00:00Z', 'Europe/Madrid')).toEqual({
      future: true,
      text: '06/11/2026 01:00',
    })
  })

  it('sin marca no hay nada que decir', () => {
    expect(timestampInfo(null).future).toBe(false)
  })
})

describe('measureTitle', () => {
  it('junta nombre e identificador, y no repite el identificador si es el nombre', () => {
    expect(measureTitle({ id: 'visits', name: 'Visitas' })).toBe('Visitas · visits')
    expect(measureTitle({ id: 'mystery', name: 'mystery' })).toBe('mystery')
  })
})
