import { describe, expect, it } from 'vitest'
import { EXPANDED_CHROME, expandedHeight } from './expanded'

describe('expandedHeight', () => {
  it('ocupa la ventana menos el marco y nunca encoge la grafica', () => {
    expect(expandedHeight(280, 1000)).toBe(1000 - EXPANDED_CHROME)
    expect(expandedHeight(900, 1000)).toBe(900)
    expect(expandedHeight('60vh', 1000)).toBe(`max(60vh, ${1000 - EXPANDED_CHROME}px)`)
    expect(expandedHeight('60vh', 100)).toBe('60vh')
  })
})
