import { formatNumber } from '@/lib/format'
import type { Entity, Geolocation, Measure } from '@/types'

/** De donde sale la coordenada, para poder rotularla en la ficha. */
export type LocationSource = 'entity' | 'measure'

export interface EntityLocation {
  lat: number
  lon: number
  source: LocationSource
  /** Medida de la que se ha leido, cuando no venia en la ficha de la entidad. */
  measureId?: string
}

const GEO_ID = /^(location|geolocation|position|coordinates)$/i
const GEO_HINT = /location|coordinates|geolocation/i
const LATITUDE_ID = /^(latitude|lat)$/i
const LONGITUDE_ID = /^(longitude|lon|lng)$/i

function isPlausible(lat: number, lon: number): boolean {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return false
  // El par 0,0 es como el broker representa "sin ubicacion", no un punto en el golfo de Guinea.
  return lat !== 0 || lon !== 0
}

function toObject(value: unknown): Record<string, unknown> | null {
  if (typeof value === 'string') {
    const text = value.trim()
    if (!text.startsWith('{')) return null
    try {
      const parsed: unknown = JSON.parse(text)
      return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null
    } catch {
      return null
    }
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

/** La ubicacion llega unas veces como objeto y otras como cadena JSON dentro de una medida. */
export function parseGeoJson(value: unknown): Geolocation | null {
  const obj = toObject(value)
  if (!obj) return null
  if (obj.type === 'Feature') return parseGeoJson(obj.geometry)
  if (obj.type !== 'Point' && obj.type !== 'Polygon') return null
  return Array.isArray(obj.coordinates) ? (obj as unknown as Geolocation) : null
}

function pointLatLon(coordinates: unknown): { lat: number; lon: number } | null {
  if (!Array.isArray(coordinates) || coordinates.length < 2) return null
  // GeoJSON ordena longitud antes de latitud.
  const lon = Number(coordinates[0])
  const lat = Number(coordinates[1])
  return isPlausible(lat, lon) ? { lat, lon } : null
}

/**
 * Centroide del anillo exterior por la formula del area (shoelace). Promediar vertices desplaza
 * el punto hacia los tramos que tienen mas, y en recintos urbanos el error se ve.
 */
function polygonCentroid(rings: unknown): { lat: number; lon: number } | null {
  const ring = Array.isArray(rings) ? rings[0] : null
  const points = (Array.isArray(ring) ? (ring as unknown[]) : [])
    .map((c) => {
      const pair = Array.isArray(c) ? (c as unknown[]) : []
      return [Number(pair[0]), Number(pair[1])] as const
    })
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

  // Area nula: el anillo es un punto o una linea, y entonces la media de vertices si es correcta.
  if (twiceArea === 0) {
    const sum = points.reduce((acc, [px, py]) => [acc[0] + px, acc[1] + py], [0, 0])
    return pointLatLon([sum[0] / points.length, sum[1] / points.length])
  }

  const factor = 1 / (3 * twiceArea)
  return pointLatLon([x * factor, y * factor])
}

export function geoJsonLatLon(geo?: Geolocation | null): { lat: number; lon: number } | null {
  if (!geo) return null
  if (geo.type === 'Point') return pointLatLon(geo.coordinates)
  if (geo.type === 'Polygon') return polygonCentroid(geo.coordinates)
  return null
}

function numberFromMeasure(measures: Measure[], id: RegExp): number | null {
  for (const measure of measures) {
    if (!id.test(measure.id)) continue
    const n = Number(measure.value)
    if (Number.isFinite(n)) return n
  }
  return null
}

/**
 * Orden de resolucion: la ubicacion de la ficha, la medida con un GeoJSON y, en ultimo lugar,
 * un par de medidas de latitud y longitud. La respuesta de /entities/{id} casi nunca trae la
 * primera, asi que sin las otras dos la mayoria de entidades se quedarian sin mapa.
 */
export function resolveEntityLocation(
  entity?: Entity | null,
  measures: Measure[] = [],
): EntityLocation | null {
  const own = geoJsonLatLon(entity?.geolocation)
  if (own) return { ...own, source: 'entity' }

  const exact = measures.filter((m) => GEO_ID.test(m.id))
  const hinted = measures.filter(
    (m) => !GEO_ID.test(m.id) && (GEO_HINT.test(m.id) || GEO_HINT.test(m.name)),
  )
  for (const measure of [...exact, ...hinted]) {
    const point = geoJsonLatLon(parseGeoJson(measure.value))
    if (point) return { ...point, source: 'measure', measureId: measure.id }
  }

  const lat = numberFromMeasure(measures, LATITUDE_ID)
  const lon = numberFromMeasure(measures, LONGITUDE_ID)
  if (lat !== null && lon !== null && isPlausible(lat, lon)) return { lat, lon, source: 'measure' }

  return null
}

/** Cinco decimales bastan para situar un sensor en la acera correcta. */
export function coordinatesText(point: { lat: number; lon: number }): string {
  return `${formatNumber(point.lat, 5)} · ${formatNumber(point.lon, 5)}`
}
