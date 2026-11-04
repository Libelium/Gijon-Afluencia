import { afterEach, describe, expect, it, vi } from 'vitest'
import { FOCUS_ZOOM, focusZoom, onceOrAfter, shouldLocate } from './viewport'

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

describe('onceOrAfter', () => {
  /** Emisor minimo con la forma de los de Leaflet: `once`, `off` y un `fire` para la prueba. */
  function emitter() {
    const handlers = new Map<string, Set<() => void>>()
    return {
      once(type: string, fn: () => void) {
        const set = handlers.get(type) ?? new Set()
        const wrapped = () => {
          set.delete(wrapped)
          fn()
        }
        Object.assign(wrapped, { original: fn })
        set.add(wrapped)
        handlers.set(type, set)
      },
      off(type: string, fn: () => void) {
        for (const h of handlers.get(type) ?? []) {
          if ((h as unknown as { original: () => void }).original === fn) handlers.get(type)!.delete(h)
        }
      },
      fire(type: string) {
        for (const h of [...(handlers.get(type) ?? [])]) h()
      },
      listeners: (type: string) => handlers.get(type)?.size ?? 0,
    }
  }

  afterEach(() => {
    vi.useRealTimers()
  })

  it('con el evento, avisa una vez y ya no espera al plazo', () => {
    vi.useFakeTimers()
    const target = emitter()
    const done = vi.fn()
    onceOrAfter(target, 'animationend', 600, done)
    target.fire('animationend')
    vi.advanceTimersByTime(600)
    expect(done).toHaveBeenCalledTimes(1)
  })

  it('sin el evento, avisa al cumplirse el plazo y deja de escucharlo', () => {
    vi.useFakeTimers()
    const target = emitter()
    const done = vi.fn()
    onceOrAfter(target, 'animationend', 600, done)
    vi.advanceTimersByTime(599)
    expect(done).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1)
    expect(done).toHaveBeenCalledTimes(1)
    expect(target.listeners('animationend')).toBe(0)
    target.fire('animationend')
    expect(done).toHaveBeenCalledTimes(1)
  })
})
