import { DateTime } from 'luxon'
import { locale } from '@/i18n'

export const NO_VALUE = '—'

const DEFAULT_ZONE = 'Europe/Madrid'

/**
 * Unico punto donde se interpreta una marca temporal del servidor.
 *
 * La API las emite en UTC, sin indicarlo, y separando fecha y hora con un espacio en lugar
 * de la «T» que exige ISO 8601: «2026-07-28 23:00:00». Luxon rechaza ese separador, asi que
 * mientras no se normalizaba, TODAS las fechas de la aplicacion se pintaban como «—».
 *
 * Se sustituye solo el primer espacio: lo que va detras es la hora, o un offset con su
 * propio espacio, y tocarlo romperia el valor. Si la cadena ya trae zona u offset, luxon lo
 * respeta y el `zone: 'utc'` de partida no se aplica.
 */
export function parseApiDateTime(value?: string | null, timeZone?: string): DateTime | null {
  if (!value) return null
  const dt = DateTime.fromISO(value.trim().replace(' ', 'T'), { zone: 'utc' })
  return dt.isValid ? dt.setZone(timeZone || DEFAULT_ZONE).setLocale(locale) : null
}

/** Formato de fechas y numeros. La zona horaria sale de las preferencias del usuario. */
export function formatDateTime(iso?: string | null, timeZone?: string): string {
  return parseApiDateTime(iso, timeZone)?.toFormat('dd/MM/yyyy HH:mm') ?? NO_VALUE
}

export function formatDate(iso?: string | null, timeZone?: string): string {
  return parseApiDateTime(iso, timeZone)?.toFormat('dd/MM/yyyy') ?? NO_VALUE
}

export function relativeFromNow(iso?: string | null, timeZone?: string): string {
  return parseApiDateTime(iso, timeZone)?.toRelative() ?? NO_VALUE
}

export function formatNumber(value: unknown, maxDecimals = 2): string {
  if (value === null || value === undefined || value === '') return NO_VALUE
  const n = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(n)) return String(value)
  return new Intl.NumberFormat(locale, { maximumFractionDigits: maxDecimals }).format(n)
}

export function formatMeasure(value: unknown, units?: string): string {
  const n = formatNumber(value)
  return units && n !== NO_VALUE ? `${n} ${units}` : n
}

/** Ultimo segmento de un URN NGSI-LD, que es lo que resulta legible en una tabla. */
export function urnTail(urn?: string): string {
  if (!urn) return NO_VALUE
  const parts = urn.split(':')
  return parts[parts.length - 1] || urn
}
