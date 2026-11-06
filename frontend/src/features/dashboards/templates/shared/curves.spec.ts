import { describe, expect, it } from 'vitest'
import { CURVE_STEPS, curvedPath, type LatLng } from './curves'

const A: LatLng = [43.54, -5.67]
const B: LatLng = [43.545, -5.66]

/** Lado de la recta A→B en que cae un punto: positivo a la izquierda, negativo a la derecha. */
function side(from: LatLng, to: LatLng, point: LatLng): number {
  const scale = Math.cos((((from[0] + to[0]) / 2) * Math.PI) / 180)
  const [x0, y0] = [from[1] * scale, from[0]]
  const [x1, y1] = [to[1] * scale, to[0]]
  const [x, y] = [point[1] * scale, point[0]]
  return (x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)
}

describe('curvedPath', () => {
  it('empieza y acaba en los dos puntos, con los tramos pedidos', () => {
    const path = curvedPath(A, B)
    expect(path).toHaveLength(CURVE_STEPS + 1)
    expect(path[0][0]).toBeCloseTo(A[0], 12)
    expect(path[0][1]).toBeCloseTo(A[1], 12)
    expect(path.at(-1)![0]).toBeCloseTo(B[0], 12)
    expect(path.at(-1)![1]).toBeCloseTo(B[1], 12)
  })

  it('se aparta a la derecha del sentido de la marcha', () => {
    const middle = curvedPath(A, B)[CURVE_STEPS / 2]
    expect(side(A, B, middle)).toBeLessThan(0)
  })

  it('la ida y la vuelta van por lados opuestos y no se pisan', () => {
    const there = curvedPath(A, B)[CURVE_STEPS / 2]
    const back = curvedPath(B, A)[CURVE_STEPS / 2]
    expect(side(A, B, there)).toBeLessThan(0)
    expect(side(A, B, back)).toBeGreaterThan(0)
  })

  it('sin curvatura es la recta', () => {
    const middle = curvedPath(A, B, 0)[CURVE_STEPS / 2]
    expect(middle[0]).toBeCloseTo((A[0] + B[0]) / 2, 12)
    expect(middle[1]).toBeCloseTo((A[1] + B[1]) / 2, 12)
  })
})
