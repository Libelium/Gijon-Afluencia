import { DateTime } from 'luxon'
import { locale } from '@/i18n'
import { formatNumber } from '@/lib/format'
import type { ChartPoint, ChartSeries } from './types'

const HOUR = 3600 * 1000
const DAY = 24 * HOUR

/** Las marcas de tiempo del backend llegan en UTC; el eje se dibuja en milisegundos. */
export function toMillis(iso: string): number {
  const dt = DateTime.fromISO(iso, { zone: 'utc' })
  return dt.isValid ? dt.toMillis() : Number.NaN
}

export function nonNull(points: ChartPoint[]): ChartPoint[] {
  return points.filter((p) => p.v !== null && p.v !== undefined && Number.isFinite(p.v))
}

export function lastPoint(series?: ChartSeries): ChartPoint | null {
  if (!series) return null
  const valid = nonNull(series.points)
  return valid.length ? valid[valid.length - 1] : null
}

export function hasData(series: ChartSeries[]): boolean {
  return series.some((s) => nonNull(s.points).length > 0)
}

/** Amplitud temporal del conjunto, para decidir el detalle de las etiquetas del eje. */
export function spanOf(series: ChartSeries[]): number {
  let min = Number.POSITIVE_INFINITY
  let max = Number.NEGATIVE_INFINITY
  for (const s of series) {
    for (const p of s.points) {
      const ms = toMillis(p.t)
      if (!Number.isFinite(ms)) continue
      if (ms < min) min = ms
      if (ms > max) max = ms
    }
  }
  return Number.isFinite(min) && Number.isFinite(max) ? max - min : 0
}

/**
 * Separacion tipica entre puntos consecutivos. Se toma la mediana de los huecos, no el minimo,
 * para que un par de lecturas seguidas no haga pasar por horaria una serie agregada por dias.
 */
export function stepOf(series: ChartSeries[]): number {
  const stamps = new Set<number>()
  for (const s of series) {
    for (const p of s.points) {
      const ms = toMillis(p.t)
      if (Number.isFinite(ms)) stamps.add(ms)
    }
  }
  const sorted = [...stamps].sort((a, b) => a - b)
  if (sorted.length < 2) return 0
  const gaps = sorted.slice(1).map((ms, i) => ms - sorted[i])
  gaps.sort((a, b) => a - b)
  return gaps[Math.floor(gaps.length / 2)]
}

/**
 * Detalle de las etiquetas del eje temporal. Manda la separacion entre puntos antes que la
 * amplitud: con lecturas agregadas por dias la hora siempre es 00:00 y dos fechas distintas
 * quedarian rotuladas igual.
 */
export function timeFormatFor(span: number, compact = false, step = 0): string {
  if (step >= 20 * HOUR) return span <= 100 * DAY ? 'dd/MM' : 'MM/yyyy'
  if (span <= 36 * HOUR) return 'HH:mm'
  if (span <= 7 * DAY) return compact ? 'dd/MM' : 'dd/MM HH:mm'
  if (span <= 90 * DAY) return 'dd/MM'
  return 'MM/yyyy'
}

/** Formato del eje a partir de la propia serie, que es como lo piden todos los graficos. */
export function timeFormatOf(series: ChartSeries[], compact = false): string {
  return timeFormatFor(spanOf(series), compact, stepOf(series))
}

/**
 * ECharts reparte las marcas del eje temporal en la hora del navegador, asi que se le da un
 * formateador propio para imprimirlas en la zona del usuario: el valor mostrado es el correcto
 * aunque el reparto de marcas siga el horario local, que es la diferencia asumible.
 */
export function timeLabel(ms: number, timeZone: string, format: string): string {
  const dt = DateTime.fromMillis(ms, { zone: timeZone })
  return dt.isValid ? dt.setLocale(locale).toFormat(format) : '—'
}

/** Etiqueta de categoria: fecha si el valor es una marca de tiempo, y si no el texto tal cual. */
export function categoryLabel(raw: string, timeZone: string, format: string): string {
  const ms = toMillis(raw)
  return Number.isFinite(ms) ? timeLabel(ms, timeZone, format) : raw
}

export function axisValue(value: number): string {
  if (!Number.isFinite(value)) return '—'
  const abs = Math.abs(value)
  if (abs >= 100000) {
    return new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }).format(
      value,
    )
  }
  if (abs >= 1000) return formatNumber(value, 0)
  if (abs >= 10) return formatNumber(value, 1)
  return formatNumber(value, 2)
}

/**
 * A partir de la cuarta serie el color deja de distinguirse con fiabilidad (y no sirve a quien
 * no percibe bien el color): se refuerza con un patron de trazo distinto.
 */
export type DashPattern = 'solid' | 'dashed' | 'dotted' | number[]

const DASHES: DashPattern[] = ['solid', 'dashed', 'dotted', [10, 4, 2, 4]]

export function dashFor(index: number, total: number): DashPattern {
  return total < 4 ? 'solid' : DASHES[index % DASHES.length]
}

export interface TooltipItem {
  seriesName?: string
  marker?: string
  name?: string
  axisValue?: number | string
  value?: unknown
  percent?: number
}

/** El formateador recibe un objeto cuando hay un solo dato y una lista cuando el disparo es por eje. */
export function asItems(params: unknown): TooltipItem[] {
  return (Array.isArray(params) ? params : [params]) as TooltipItem[]
}

/** El tooltip de ECharts admite HTML y los nombres de serie vienen del backend: hay que escaparlos. */
export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function tooltipRow(marker: string | undefined, label: string, value: string): string {
  return `<div style="display:flex;align-items:center;gap:8px;margin-top:4px">${marker ?? ''}<span style="flex:1">${escapeHtml(label)}</span><strong style="margin-left:12px">${escapeHtml(value)}</strong></div>`
}

export function tooltipHeader(text: string): string {
  return `<div style="opacity:.7">${escapeHtml(text)}</div>`
}

/** Techo redondeado por encima del valor, para que una aguja no acabe pegada al maximo. */
export function niceCeil(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 100
  const magnitude = 10 ** Math.floor(Math.log10(value))
  const steps = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
  for (const step of steps) {
    const candidate = step * magnitude
    if (candidate >= value * 1.05) return candidate
  }
  return 10 * magnitude
}
