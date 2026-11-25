import { describe, expect, it } from 'vitest'
import { toCsv } from './csv'
import { formatCoordinates } from './format'

describe('formatCoordinates', () => {
  it('usa punto decimal: con coma no se distinguiria de la que separa latitud y longitud', () => {
    expect(formatCoordinates(43.5450251, -5.662616)).toBe('43.54503, -5.66262')
    expect(formatCoordinates(43.5, -5.66)).toBe('43.5, -5.66')
    expect(formatCoordinates(Number.NaN, -5.66)).toBe('—, -5.66')
  })

  it('en el CSV van en una sola celda y con punto', () => {
    const csv = toCsv(['Zona', 'Coordenadas'], [['Plaza Mayor', formatCoordinates(43.5450251, -5.662616)]])
    expect(csv.split('\r\n')[1]).toBe('Plaza Mayor;43.54503, -5.66262')
  })
})
