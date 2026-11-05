/**
 * Geometria de los recorridos dibujados en un mapa. Una recta entre dos puntos pinta A→B y B→A
 * en el mismo sitio y no dice hacia donde va la gente; un arco que se aparta siempre hacia la
 * derecha del sentido de la marcha separa los dos sentidos, y una punta de flecha en su mitad dice
 * cual es cada uno.
 *
 * Se calcula en un plano local, con la longitud escalada por el coseno de la latitud, para que el
 * arco tenga la misma forma en pantalla a cualquier latitud. Es una aproximacion valida para
 * distancias de una ciudad, no para continentes.
 */

export type LatLng = [number, number]

/** Cuanto se aparta el arco de la recta, en fraccion de su longitud. */
export const CURVE_BEND = 0.18

/** Tramos rectos con que se dibuja el arco. */
export const CURVE_STEPS = 16

/** Largo de la punta de flecha, en fraccion de la longitud del recorrido. */
export const ARROW_SIZE = 0.07

interface Plane {
  toXY: (point: LatLng) => [number, number]
  toLatLng: (x: number, y: number) => LatLng
}

function planeFor(a: LatLng, b: LatLng): Plane {
  const scale = Math.cos((((a[0] + b[0]) / 2) * Math.PI) / 180) || 1
  return {
    toXY: ([lat, lng]) => [lng * scale, lat],
    toLatLng: (x, y) => [y, x / scale],
  }
}

/** Punto de control del arco: en la mediatriz, a la derecha del sentido de `from` a `to`. */
function control(p0: [number, number], p1: [number, number], bend: number): [number, number] {
  const dx = p1[0] - p0[0]
  const dy = p1[1] - p0[1]
  // Girar el sentido 90° en el de las agujas del reloj da su derecha: (dy, -dx).
  return [(p0[0] + p1[0]) / 2 + dy * bend, (p0[1] + p1[1]) / 2 - dx * bend]
}

function bezier(p0: [number, number], c: [number, number], p1: [number, number], t: number): [number, number] {
  const u = 1 - t
  return [u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0], u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]]
}

/** El arco de `from` a `to`, como lista de puntos. Dos puntos iguales dan una linea de un punto. */
export function curvedPath(from: LatLng, to: LatLng, bend = CURVE_BEND, steps = CURVE_STEPS): LatLng[] {
  const plane = planeFor(from, to)
  const p0 = plane.toXY(from)
  const p1 = plane.toXY(to)
  const c = control(p0, p1, bend)
  return Array.from({ length: steps + 1 }, (_, i) => {
    const [x, y] = bezier(p0, c, p1, i / steps)
    return plane.toLatLng(x, y)
  })
}

/**
 * La punta de flecha en la mitad del arco, como tres puntos (ala, punta, ala) que se dibujan con la
 * misma linea. En la mitad, la tangente de un arco cuadratico es paralela a la recta de `from` a
 * `to`. Vacia si los dos puntos coinciden.
 */
export function arrowHead(from: LatLng, to: LatLng, bend = CURVE_BEND, size = ARROW_SIZE): LatLng[] {
  const plane = planeFor(from, to)
  const p0 = plane.toXY(from)
  const p1 = plane.toXY(to)
  const dx = p1[0] - p0[0]
  const dy = p1[1] - p0[1]
  const length = Math.hypot(dx, dy)
  if (length === 0) return []

  const [mx, my] = bezier(p0, control(p0, p1, bend), p1, 0.5)
  const ux = dx / length
  const uy = dy / length
  const head = length * size
  const tip: [number, number] = [mx + (ux * head) / 2, my + (uy * head) / 2]
  const back: [number, number] = [tip[0] - ux * head, tip[1] - uy * head]
  const wing = head * 0.6
  return [
    plane.toLatLng(back[0] + uy * wing, back[1] - ux * wing),
    plane.toLatLng(tip[0], tip[1]),
    plane.toLatLng(back[0] - uy * wing, back[1] + ux * wing),
  ]
}
