import { describe, expect, it } from 'vitest'
import { initialsOf, maskEmail, maskName } from './mask'

describe('maskName', () => {
  it('deja solo la inicial de cada parte', () => {
    expect(maskName('María López García')).toBe('M••• L••• G•••')
  })

  it('no revela la longitud', () => {
    expect(maskName('Ana')).toBe(maskName('Anastasia'))
  })

  it('tolera vacios y espacios de sobra', () => {
    expect(maskName('')).toBe('—')
    expect(maskName(null)).toBe('—')
    expect(maskName('  Luis   Pérez ')).toBe('L••• P•••')
  })
})

describe('maskEmail', () => {
  it('oculta usuario y dominio y conserva el dominio de primer nivel', () => {
    expect(maskEmail('maria.lopez@gijon.es')).toBe('m•••@g•••.es')
  })

  it('usa el ultimo punto para el dominio de primer nivel', () => {
    expect(maskEmail('nexus@pid.gijon.example')).toBe('n•••@p•••.example')
  })

  it('no rompe con valores sin arroba', () => {
    expect(maskEmail('sinarroba')).toBe('s•••')
    expect(maskEmail(undefined)).toBe('—')
  })
})

describe('initialsOf', () => {
  it('oculta las iniciales cuando los datos van ofuscados', () => {
    expect(initialsOf('María López', true)).toBe('•')
    expect(initialsOf('María López', false)).toBe('ML')
  })
})
