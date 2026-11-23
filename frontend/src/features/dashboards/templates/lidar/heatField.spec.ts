import { describe, expect, it } from 'vitest'
import { HEAT_OPACITY, heatAt, heatColor, renderHeat, type HeatZone } from './heatField'

const square = (x: number, y: number, side: number, value: number): HeatZone => ({
  value,
  ring: [
    [x, y],
    [x + side, y],
    [x + side, y + side],
    [x, y + side],
  ],
})

describe('heatColor', () => {
  it('va de verde claro con la zona vacia a rojo oscuro con la llena, y no se sale de la escala', () => {
    expect(heatColor(0)).toEqual([0x66, 0xbd, 0x63])
    expect(heatColor(0.5)).toEqual([0xf5, 0xe6, 0x63])
    expect(heatColor(1)).toEqual([0x9e, 0x0f, 0x12])
    expect(heatColor(3)).toEqual(heatColor(1))
    expect(heatColor(Number.NaN)).toEqual(heatColor(0))
  })
})

describe('heatAt', () => {
  const zone = square(0, 0, 100, 0.6)

  it('dentro de la zona vale su proporcion de aforo, sin difuminar', () => {
    expect(heatAt(50, 50, [zone], 20)).toMatchObject({ value: 0.6, alpha: 1 })
    expect(heatAt(1, 1, [zone], 20)).toMatchObject({ value: 0.6, alpha: 1 })
  })

  it('con difuminado interior el borde se suaviza tambien por dentro, y el centro sigue igual', () => {
    expect(heatAt(50, 50, [zone], 20, 10)).toMatchObject({ value: 0.6, alpha: 1 })
    const edge = heatAt(2, 50, [zone], 20, 10)
    expect(edge.alpha).toBeLessThan(1)
    expect(edge.alpha).toBeGreaterThan(heatAt(-2, 50, [zone], 20, 10).alpha)
  })

  it('por fuera se apaga a lo largo del difuminado y desaparece despues', () => {
    const near = heatAt(105, 50, [zone], 20)
    const far = heatAt(115, 50, [zone], 20)
    expect(near.alpha).toBeGreaterThan(far.alpha)
    expect(near.value).toBeLessThan(0.6)
    expect(heatAt(130, 50, [zone], 20)).toMatchObject({ value: 0, alpha: 0 })
  })

  it('entre dos zonas cercanas manda la mas caliente', () => {
    const hot = square(130, 0, 100, 1)
    expect(heatAt(115, 50, [zone, hot], 20).value).toBeGreaterThan(heatAt(115, 50, [zone], 20).value)
  })
})

describe('renderHeat', () => {
  it('pinta las celdas de la zona con su color y deja transparente lo lejano', () => {
    const data = renderHeat([square(0, 0, 40, 1)], 20, 4, 4, 8)
    const pixel = (col: number, row: number) => [...data.slice((row * 20 + col) * 4, (row * 20 + col) * 4 + 4)]
    expect(pixel(2, 2)).toEqual([...heatColor(1), Math.round(255 * HEAT_OPACITY)])
    expect(pixel(19, 2)[3]).toBe(0)
  })
})

