import type { Bounds, Entity, Geolocation } from '@/types'
import { formatNumber } from '@/lib/format'

/** Par [latitud, longitud], que es el orden que espera el mapa (GeoJSON usa el contrario). */
export type LatLng = [number, number]

/** Coordenadas para leer: cuatro decimales bastan para situar un sensor en su calle. */
export function formatLatLng(latLng: LatLng): string {
  return `${formatNumber(latLng[0], 4)} · ${formatNumber(latLng[1], 4)}`
}

export interface PlacedEntity {
  entity: Entity
  latLng: LatLng
}

function toLatLng(coordinates: [number, number] | undefined): LatLng | null {
  if (!coordinates) return null
  const lon = Number(coordinates[0])
  const lat = Number(coordinates[1])
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null
  return [lat, lon]
}

/**
 * Centroide del anillo exterior por la formula del area (shoelace). La media de vertices
 * desplaza el punto hacia los tramos con mas vertices, y en recintos urbanos se nota.
 */
function ringCentroid(ring: [number, number][] | undefined): LatLng | null {
  const points = (ring ?? [])
    .map((c) => [Number(c?.[0]), Number(c?.[1])] as const)
    .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y))

  if (!points.length) return null

  let twiceArea = 0
  let x = 0
  let y = 0
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    const [x0, y0] = points[j]
    const [x1, y1] = points[i]
    const cross = x0 * y1 - x1 * y0
    twiceArea += cross
    x += (x0 + x1) * cross
    y += (y0 + y1) * cross
  }

  // Area nula: el anillo es un punto o una linea, asi que sirve la media de vertices.
  if (twiceArea === 0) {
    const n = points.length
    const sum = points.reduce((acc, [px, py]) => [acc[0] + px, acc[1] + py], [0, 0])
    return toLatLng([sum[0] / n, sum[1] / n])
  }

  const factor = 1 / (3 * twiceArea)
  return toLatLng([x * factor, y * factor])
}

export function geolocationLatLng(geolocation?: Geolocation | null): LatLng | null {
  if (!geolocation) return null
  if (geolocation.type === 'Point') return toLatLng(geolocation.coordinates)
  if (geolocation.type === 'Polygon') return ringCentroid(geolocation.coordinates?.[0])
  return null
}

/**
 * Rectangulo minimo que contiene todos los puntos, o null si no hay ninguno. Sirve para encuadrar
 * el mapa sobre las entidades en lugar de sobre un centro fijo que puede estar en otra region.
 */
export function boundsOf(placed: PlacedEntity[]): Bounds | null {
  if (!placed.length) return null

  let south = 90
  let north = -90
  let west = 180
  let east = -180

  for (const item of placed) {
    const [lat, lon] = item.latLng
    if (lat < south) south = lat
    if (lat > north) north = lat
    if (lon < west) west = lon
    if (lon > east) east = lon
  }

  return { south, west, north, east }
}

/** Reparte el listado en lo que se puede pintar y lo que no tiene ubicacion utilizable. */
export function placeEntities(entities: Entity[]): { placed: PlacedEntity[]; withoutLocation: number } {
  const placed: PlacedEntity[] = []
  let withoutLocation = 0

  for (const entity of entities) {
    const latLng = geolocationLatLng(entity.geolocation)
    if (latLng) placed.push({ entity, latLng })
    else withoutLocation += 1
  }

  return { placed, withoutLocation }
}
