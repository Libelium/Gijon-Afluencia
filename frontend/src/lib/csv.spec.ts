import { describe, expect, it } from 'vitest'
import { csvFileName, toCsv } from './csv'

describe('toCsv', () => {
  it('abre bien en una hoja de cálculo en castellano: punto y coma, coma decimal y BOM', () => {
    const csv = toCsv(['Fecha', 'Ocupación (personas)'], [['2026-11-17 13:00', 12.5], ['2026-11-17 14:00', 1234]])
    expect(csv.startsWith('﻿')).toBe(true)
    expect(csv.slice(1).split('\r\n')).toEqual(['Fecha;Ocupación (personas)', '2026-11-17 13:00;12,5', '2026-11-17 14:00;1234'])
  })

  it('deja vacío lo que no tiene valor y entrecomilla lo que rompería la fila', () => {
    const csv = toCsv(['a', 'b', 'c'], [[null, 'Cimavilla; Sur', 'dice "hola"'], [undefined, Number.NaN, 'x']])
    expect(csv.slice(1).split('\r\n').slice(1)).toEqual([';"Cimavilla; Sur";"dice ""hola"""', ';;x'])
  })
})

describe('csvFileName', () => {
  it('quita tildes y signos del título y añade la fecha', () => {
    expect(csvFileName('Ocupación prevista · Plaza Mayor', new Date('2026-11-17T10:00:00Z'))).toBe(
      'ocupacion-prevista-plaza-mayor_2026-11-17.csv',
    )
    expect(csvFileName('¡¿?!', new Date('2026-11-17T10:00:00Z'))).toBe('datos_2026-11-17.csv')
  })
})
