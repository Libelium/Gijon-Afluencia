import { polygonLatLngs } from '@/features/map/lib/geometry'
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
