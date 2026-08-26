import { DateTime } from 'luxon'
import { formatDate, formatDateTime, formatNumber, relativeFromNow } from '@/lib/format'

/**
 * Vista previa de como quedan fecha y numero con las opciones elegidas. El formato `es-ES`
 * es el que ya aplica la aplicacion, asi que se delega en `@/lib/format` para que la
 * previsualizacion y la interfaz real no puedan divergir.
 */

export function previewDateTime(iso: string, timeZone: string, format: string): string {
  if (format === 'es-ES') return formatDateTime(iso, timeZone)
  const dt = DateTime.fromISO(iso, { zone: 'utc' }).setZone(timeZone)
  if (!dt.isValid) return '—'
  if (format === 'en-US') return dt.setLocale('en-US').toFormat('MM/dd/yyyy hh:mm a')
  return dt.toFormat("yyyy-MM-dd'T'HH:mm:ssZZ")
}

export function previewDate(iso: string, timeZone: string, format: string): string {
  if (format === 'es-ES') return formatDate(iso, timeZone)
  const dt = DateTime.fromISO(iso, { zone: 'utc' }).setZone(timeZone)
  if (!dt.isValid) return '—'
  return dt.toFormat(format === 'en-US' ? 'MM/dd/yyyy' : 'yyyy-MM-dd')
}

export function previewTime(iso: string, timeZone: string, format: string): string {
  const dt = DateTime.fromISO(iso, { zone: 'utc' }).setZone(timeZone)
  if (!dt.isValid) return '—'
  if (format === 'en-US') return dt.setLocale('en-US').toFormat('hh:mm a')
  return dt.toFormat(format === 'ISO-8601' ? 'HH:mm:ss' : 'HH:mm')
}

export function previewRelative(iso: string, timeZone: string): string {
  return relativeFromNow(iso, timeZone)
}

export function previewNumber(value: number, format: string): string {
  if (format === 'es-ES') return formatNumber(value)
  try {
    return new Intl.NumberFormat(format, { maximumFractionDigits: 2 }).format(value)
  } catch {
    return formatNumber(value)
  }
}
