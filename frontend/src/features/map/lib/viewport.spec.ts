import { describe, expect, it } from 'vitest'
import { FOCUS_ZOOM, focusZoom, shouldLocate } from './viewport'

describe('focusZoom', () => {
  it('desde lejos acerca el mapa hasta el zoom de calle', () => {
    expect(focusZoom(5)).toBe(FOCUS_ZOOM)
    expect(focusZoom(FOCUS_ZOOM - 1)).toBe(FOCUS_ZOOM)
  })

  it('si ya esta igual de cerca o mas, no lo aleja', () => {
    expect(focusZoom(FOCUS_ZOOM)).toBeNull()
    expect(focusZoom(19)).toBeNull()
  })
})

describe('shouldLocate', () => {
  const base = { count: 0, first: false, byFilter: false, filtered: false }

  it('la primera carga vacia y sin filtros busca donde hay datos', () => {
    expect(shouldLocate({ ...base, first: true })).toBe(true)
  })

  it('un filtro sin resultados en la vista lleva a donde esten', () => {
    expect(shouldLocate({ ...base, byFilter: true, filtered: true })).toBe(true)
  })

  it('arrastrar el mapa a una zona vacia no mueve la vista', () => {
    expect(shouldLocate(base)).toBe(false)
    expect(shouldLocate({ ...base, filtered: true })).toBe(false)
  })

  it('quitar los filtros no mueve la vista', () => {
    expect(shouldLocate({ ...base, byFilter: true })).toBe(false)
  })

  it('con resultados en la vista nunca la mueve', () => {
    expect(shouldLocate({ ...base, count: 3, first: true })).toBe(false)
    expect(shouldLocate({ ...base, count: 1, byFilter: true, filtered: true })).toBe(false)
  })

  it('la primera carga ya filtrada no se recoloca por ser la primera', () => {
    expect(shouldLocate({ ...base, first: true, filtered: true })).toBe(false)
  })
})
