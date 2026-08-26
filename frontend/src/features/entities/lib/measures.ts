import { t } from '@/i18n'
import { formatDate, formatDateTime, formatMeasure, formatNumber } from '@/lib/format'
import type { Measure } from '@/types'
import { coordinatesText, geoJsonLatLon, parseGeoJson } from './location'

export type MeasureKind = 'empty' | 'boolean' | 'coordinates' | 'number' | 'text'

export interface MeasureDisplay {
  kind: MeasureKind
  /** Texto ya formateado. Las unidades van aparte para poder rotularlas atenuadas. */
  text: string
  /** Valor completo, para el titulo cuando el texto se muestra truncado. */
  full: string
  units?: string
  truthy?: boolean
}

const ISO_DATETIME = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/
const LABEL_KEYS = ['name', 'label', 'title', 'description']

function pickLabel(value: Record<string, unknown>): string | null {
  for (const key of LABEL_KEYS) {
    const raw = value[key]
    if (typeof raw === 'string' && raw.trim()) return raw.trim()
  }
  return null
}

function scalarText(value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'boolean') return value ? t('entities.measures.yes') : t('entities.measures.no')
  if (typeof value === 'number') return formatNumber(value)
  return String(value)
}

/** Los valores compuestos se resumen por su etiqueta o por sus pares clave-valor, nunca en JSON. */
function objectText(value: object): string {
  if (Array.isArray(value)) {
    return value
      .map((item) => (item && typeof item === 'object' ? objectText(item) : scalarText(item)))
      .filter(Boolean)
      .join(', ')
  }

  const record = value as Record<string, unknown>
  const label = pickLabel(record)
  if (label) return label

  const parts: string[] = []
  for (const [key, raw] of Object.entries(record)) {
    const text = raw && typeof raw === 'object' ? objectText(raw) : scalarText(raw)
    if (text) parts.push(`${key}: ${text}`)
  }
  return parts.join(' · ')
}

function oneDate(value: string, timeZone?: string): string {
  return ISO_DATE.test(value) ? formatDate(value, timeZone) : formatDateTime(value, timeZone)
}

function dateText(value: string, timeZone?: string): string | null {
  // Los periodos llegan como "inicio/fin" y se leen mucho mejor como un rango.
  const parts = value.split('/')
  if (parts.length === 2 && parts.every((p) => ISO_DATETIME.test(p) || ISO_DATE.test(p))) {
    return `${oneDate(parts[0], timeZone)} – ${oneDate(parts[1], timeZone)}`
  }
  if (ISO_DATETIME.test(value) || ISO_DATE.test(value)) return oneDate(value, timeZone)
  return null
}

function booleanValue(measure: Measure): boolean | null {
  const raw = measure.value
  if (typeof raw === 'boolean') return raw
  if (measure.value_type !== 'bool' && measure.value_type !== 'boolean') return null
  if (raw === 'true' || raw === 1 || raw === '1') return true
  if (raw === 'false' || raw === 0 || raw === '0') return false
  return null
}

/** Traduce el valor crudo de una medida a algo presentable: nada de JSON, ISO ni true/false. */
export function describeMeasure(measure: Measure, timeZone?: string): MeasureDisplay {
  const none = t('common.noValue')
  const raw = typeof measure.value === 'string' ? measure.value.trim() : measure.value

  if (raw === null || raw === undefined || raw === '') return { kind: 'empty', text: none, full: none }

  const bool = booleanValue(measure)
  if (bool !== null) {
    const text = bool ? t('entities.measures.yes') : t('entities.measures.no')
    return { kind: 'boolean', text, full: text, truthy: bool }
  }

  const point = geoJsonLatLon(parseGeoJson(raw))
  if (point) {
    return {
      kind: 'coordinates',
      text: coordinatesText(point),
      full: t('entities.detail.coordinates', {
        lat: formatNumber(point.lat, 5),
        lon: formatNumber(point.lon, 5),
      }),
    }
  }

  if (typeof raw === 'object') {
    const text = objectText(raw) || none
    return { kind: 'text', text, full: text }
  }

  if (typeof raw === 'string') {
    const asDate = dateText(raw, timeZone)
    if (asDate) return { kind: 'text', text: asDate, full: asDate }
  }

  // Solo se formatea como numero lo que YA llega como numero: el servidor tipa la propiedad y
  // deja en cadena lo que no lo es. Coaccionar la cadena corrompe el dato — un numero de serie
  // «2144123» se pintaria «2.144.123» y «0012» perderia el cero de cabecera — y son justo los
  // identificadores que el usuario copia o compara contra el sistema.
  if (typeof raw === 'number') {
    return {
      kind: 'number',
      text: formatNumber(raw),
      full: formatMeasure(raw, measure.units),
      units: measure.units,
    }
  }

  const text = String(raw)
  return { kind: 'text', text, full: text }
}

/**
 * Solo una medida numerica se puede dibujar en una grafica: el historico de un texto, de un
 * booleano o de unas coordenadas no es una serie temporal que se pueda leer en un eje.
 */
export function hasChartableHistory(measure: Measure, timeZone?: string): boolean {
  return describeMeasure(measure, timeZone).kind === 'number'
}
