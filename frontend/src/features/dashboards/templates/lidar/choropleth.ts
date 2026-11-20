import { polygonLatLngs } from '@/features/map/lib/geometry'
import { parseApiDateTime } from '@/lib/format'
import type { ChartPoint } from '../../charts'

/** Lo que el mapa sabe de una zona en el momento que muestra. */
export interface ZoneState {
  id: number
  name: string
  /** Contorno [lat, lon] de la zona, o null si solo tiene un punto y no se puede pintar. */
  polygon: [number, number][] | null
  /** Personas en la zona en ese momento, o null sin lectura. */
  value: number | null
  /** Aforo en personas, o null si la zona no lo publica. */
  capacity: number | null
  /** Proporcion del aforo, o null si falta la lectura o el aforo. */
  ratio: number | null
}

/** Contorno de una zona en [lat, lon], el orden de Leaflet. GeoJSON lo guarda como [lon, lat]. */
export const polygonOf = polygonLatLngs

/** Pasadas de suavizado: con tres las esquinas ya se ven curvas y el contorno no se engorda. */
const SMOOTH_PASSES = 3

/**
 * Contorno [lat, lon] con las esquinas redondeadas (corte de esquinas de Chaikin): cada lado se
 * sustituye por sus puntos al 25 % y al 75 %. Conserva la forma y el sitio de la zona; solo se usa
 * para dibujar. El recorte es igual en grados que en metros, asi que no hace falta proyectar.
 */
export function smoothPolygon(polygon: [number, number][] | null, passes = SMOOTH_PASSES): [number, number][] | null {
  if (!polygon) return polygon
  let ring = polygon
  const [first, last] = [ring[0], ring[ring.length - 1]]
  // GeoJSON repite el primer vertice al final: con el duplicado, esa esquina no se redondearia.
  if (ring.length > 1 && first[0] === last[0] && first[1] === last[1]) ring = ring.slice(0, -1)
  if (ring.length < 3) return polygon
  for (let pass = 0; pass < passes; pass++) {
    const next: [number, number][] = []
    for (let i = 0; i < ring.length; i++) {
      const [lat1, lon1] = ring[i]
      const [lat2, lon2] = ring[(i + 1) % ring.length]
      next.push([0.75 * lat1 + 0.25 * lat2, 0.75 * lon1 + 0.25 * lon2])
      next.push([0.25 * lat1 + 0.75 * lat2, 0.25 * lon1 + 0.75 * lon2])
    }
    ring = next
  }
  return ring
}

export function ratioOf(value: number | null, capacity: number | null): number | null {
  return value === null || !capacity || capacity <= 0 ? null : value / capacity
}

/** Marcas horarias de todas las series, ordenadas y sin repetir: los pasos de la barra de horas. */
export function timeSteps(series: Iterable<ChartPoint[]>): string[] {
  const set = new Set<string>()
  for (const points of series) for (const point of points) if (point.v !== null) set.add(point.t)
  return [...set].sort()
}

/** Valor de una serie en una marca exacta, o null si esa hora no tiene lectura. */
export function valueAt(points: ChartPoint[], timestamp: string): number | null {
  return points.find((point) => point.t === timestamp)?.v ?? null
}

/**
 * Fin del intervalo que resume un paso de la barra: la serie llega agregada en tramos que empiezan
 * en la marca del paso y duran una hora o un dia.
 */
export function stepEnd(timestamp: string, granularity: 'hour' | 'day'): string | null {
  const start = parseApiDateTime(timestamp, 'utc')
  return start ? start.plus(granularity === 'hour' ? { hours: 1 } : { days: 1 }).toISO() : null
}

/** Marca mas reciente de una lista, o null si no hay ninguna valida. */
export function latest(timestamps: (string | null | undefined)[]): string | null {
  let best: string | null = null
  let bestTime = -Infinity
  for (const timestamp of timestamps) {
    const time = parseApiDateTime(timestamp)?.toMillis()
    if (time !== undefined && time > bestTime) {
      best = timestamp as string
      bestTime = time
    }
  }
  return best
}

/** A partir de esta proporcion la zona cuenta como llena en los indicadores. */
export const NEAR_FULL = 0.8

export interface ChoroplethSummary {
  /** Personas de todas las zonas con aforo, sobre la suma de sus aforos. */
  combinedRatio: number | null
  /** Zonas al NEAR_FULL de su aforo o por encima. */
  nearFull: number
  /** Zona con mayor proporcion de aforo. */
  fullest: ZoneState | null
}

export function summarize(states: ZoneState[]): ChoroplethSummary {
  let people = 0
  let capacity = 0
  let nearFull = 0
  let fullest: ZoneState | null = null
  for (const state of states) {
    if (state.ratio === null || state.value === null || state.capacity === null) continue
    people += state.value
    capacity += state.capacity
    if (state.ratio >= NEAR_FULL) nearFull++
    if (!fullest || state.ratio > (fullest.ratio ?? -1)) fullest = state
  }
  return { combinedRatio: capacity > 0 ? people / capacity : null, nearFull, fullest }
}

export type DeviceKind = 'lidar' | 'smartspot'

/** Un dispositivo de una zona, ya situado. */
export interface ZoneDevice {
  key: string
  kind: DeviceKind
  serial: string
  zoneId: number
  zoneName: string
  lat: number
  lon: number
}

function serialList(raw: unknown): string[] {
  let value = raw
  if (typeof raw === 'string') {
    try {
      value = JSON.parse(raw)
    } catch {
      return raw.trim() ? [raw.trim()] : []
    }
  }
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && !!item) : []
}

/**
 * Dispositivos que la fusion declara en la zona: `lidarSerial` y `smartspotSerial`, listas JSON
 * con el serie de cada uno. Son los mismos de `zones.json` que alimentan la cifra de la zona.
 */
export function zoneSerials(measures: { id: string; value?: unknown }[]): Record<DeviceKind, string[]> {
  const find = (id: string) => measures.find((m) => m.id.toLowerCase() === id.toLowerCase())?.value
  return { lidar: serialList(find('lidarSerial')), smartspot: serialList(find('smartspotSerial')) }
}

/**
 * Entidad que situa cada dispositivo. Un Smart Spot publica sus conteos en `{serie}_CFO` y un
 * LIDAR en la entidad de sus metricas; las dos llevan la ubicacion del sensor.
 */
export function deviceUrn(kind: DeviceKind, serial: string, models: Record<DeviceKind, string>): string {
  return kind === 'smartspot'
    ? `urn:ngsi-ld:${models.smartspot}:${serial}_CFO`
    : `urn:ngsi-ld:${models.lidar}:${serial}`
}

/**
 * URN de la gemela de una zona en otro modelo de datos: comparten el final, que es el id de la
 * zona en `zones.json`. El aforo maximo lo publica la gemela de analitica del LIDAR, no la zona
 * combinada.
 */
export function twinUrn(urn: string, fromModel: string, toModel: string): string | null {
  const marker = `:${fromModel}:`
  return urn.includes(marker) ? urn.replace(marker, `:${toModel}:`) : null
}
