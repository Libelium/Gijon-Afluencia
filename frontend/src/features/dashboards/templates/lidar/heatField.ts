/**
 * Campo de calor de las zonas: dentro de cada zona vale su proporcion de aforo, y por fuera se
 * difumina hasta desaparecer. Trabaja en pixeles de pantalla; la capa de Leaflet (`heatLayer.ts`)
 * proyecta los contornos y pinta el resultado.
 */

export interface HeatZone {
  /** Contorno en pixeles [x, y]. */
  ring: [number, number][]
  /** Proporcion de aforo, 0..1 (lo que pasa de 1 cuenta como 1). */
  value: number
}

/** Paradas de color, de vacio a lleno: verde claro, amarillo, naranja, rojo y rojo oscuro. */
export const HEAT_STOPS: readonly [number, string][] = [
  [0, '#66BD63'],
  [0.5, '#F5E663'],
  [0.7, '#FDAE61'],
  [0.85, '#E8452C'],
  [1, '#9E0F12'],
]

/** Opacidad maxima del calor: deja ver las calles debajo. */
export const HEAT_OPACITY = 0.72

function hexToRgb(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

const STOPS_RGB = HEAT_STOPS.map(([at, hex]) => [at, hexToRgb(hex)] as const)

/** Color de una proporcion 0..1, interpolando entre las paradas. */
export function heatColor(value: number): [number, number, number] {
  const v = Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : 0
  for (let i = 1; i < STOPS_RGB.length; i++) {
    const [at, rgb] = STOPS_RGB[i]
    if (v <= at) {
      const [prevAt, prev] = STOPS_RGB[i - 1]
      const f = (v - prevAt) / (at - prevAt)
      return [0, 1, 2].map((c) => Math.round(prev[c] + (rgb[c] - prev[c]) * f)) as [number, number, number]
    }
  }
  return STOPS_RGB[STOPS_RGB.length - 1][1] as [number, number, number]
}

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.min(1, Math.max(0, (x - edge0) / (edge1 - edge0)))
  return t * t * (3 - 2 * t)
}

function inside(x: number, y: number, ring: [number, number][]): boolean {
  let hit = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit
  }
  return hit
}

function distanceToRing(x: number, y: number, ring: [number, number][]): number {
  let best = Infinity
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [ax, ay] = ring[j]
    const [bx, by] = ring[i]
    const dx = bx - ax
    const dy = by - ay
    const length = dx * dx + dy * dy
    const t = length ? Math.min(1, Math.max(0, ((x - ax) * dx + (y - ay) * dy) / length)) : 0
    best = Math.min(best, Math.hypot(x - ax - t * dx, y - ay - t * dy))
  }
  return best
}

/**
 * Calor en un punto. En el interior de una zona, su proporcion tal cual: el color dice su aforo
 * sin deformarlo. El borde se difumina: empieza `inner` pixeles hacia dentro y acaba `fade`
 * pixeles hacia fuera, asi que no se adivina la forma exacta del contorno y se ve como un halo que
 * pasa a verde. Con varias zonas cerca, manda la mas caliente.
 */
export function heatAt(
  x: number,
  y: number,
  zones: HeatZone[],
  fade: number,
  inner = 0,
): { value: number; alpha: number } {
  let value = 0
  let alpha = 0
  for (const zone of zones) {
    // Distancia al borde con signo: positiva dentro de la zona, negativa fuera.
    const distance = distanceToRing(x, y, zone.ring) * (inside(x, y, zone.ring) ? 1 : -1)
    const presence = distance >= inner ? 1 : smoothstep(-fade, inner, distance)
    if (presence <= 0) continue
    value = Math.max(value, Math.min(1, Math.max(0, zone.value)) * presence)
    alpha = Math.max(alpha, presence)
  }
  return { value, alpha }
}

/** Caja que encierra un contorno, ampliada en `margin` pixeles. */
export function boundsOf(ring: [number, number][], margin: number): [number, number, number, number] {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const [x, y] of ring) {
    minX = Math.min(minX, x)
    minY = Math.min(minY, y)
    maxX = Math.max(maxX, x)
    maxY = Math.max(maxY, y)
  }
  return [minX - margin, minY - margin, maxX + margin, maxY + margin]
}

/**
 * Rellena una imagen de `width` x `height` celdas, cada una de `cell` pixeles de pantalla. Solo
 * se calculan las celdas cerca de alguna zona: el resto queda transparente.
 */
export function renderHeat(
  zones: HeatZone[],
  width: number,
  height: number,
  cell: number,
  fade: number,
  inner = 0,
): Uint8ClampedArray {
  const data = new Uint8ClampedArray(width * height * 4)
  const boxes = zones.map((zone) => boundsOf(zone.ring, fade))
  for (let row = 0; row < height; row++) {
    const y = (row + 0.5) * cell
    for (let col = 0; col < width; col++) {
      const x = (col + 0.5) * cell
      const near = zones.filter((_, i) => {
        const [x0, y0, x1, y1] = boxes[i]
        return x >= x0 && x <= x1 && y >= y0 && y <= y1
      })
      if (!near.length) continue
      const { value, alpha } = heatAt(x, y, near, fade, inner)
      if (alpha <= 0) continue
      const [r, g, b] = heatColor(value)
      const at = (row * width + col) * 4
      data[at] = r
      data[at + 1] = g
      data[at + 2] = b
      data[at + 3] = Math.round(255 * HEAT_OPACITY * alpha)
    }
  }
  return data
}
