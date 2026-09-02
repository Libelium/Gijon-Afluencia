import { DateTime } from 'luxon'
import type { ChartPoint } from '../../charts'
import type { Bucket, Kpis, MatrixCell, Point } from './types'

export type How = 'mean' | 'sum' | 'max'

/**
 * Cuando hay mas puntos de los que un tope admite, se quedan los de dato mas reciente. Se compara
 * por `time_last_data` en orden descendente (cadena ISO, comparable como texto). Si no hay recorte
 * que hacer se devuelve el array original, sin copiarlo, para conservar su orden.
 */
export function topByRecency(points: Point[], limit: number): Point[] {
  if (points.length <= limit) return points
  return [...points]
    .sort((a, b) => (b.entity.time_last_data ?? '').localeCompare(a.entity.time_last_data ?? ''))
    .slice(0, limit)
}

function isNumeric(v: number | null | undefined): v is number {
  return v !== null && v !== undefined && Number.isFinite(v)
}

export function nonNullPoints(points: ChartPoint[]): ChartPoint[] {
  return points.filter((p) => isNumeric(p.v))
}

export function kpisOf(points: ChartPoint[]): Kpis {
  const valid = nonNullPoints(points)
  if (!valid.length) return { current: null, max: null, mean: null, total: null, at: null, maxAt: null }

  const last = valid[valid.length - 1]
  let max = valid[0].v as number
  let maxAt = valid[0].t
  let sum = 0
  for (const point of valid) {
    const value = point.v as number
    sum += value
    if (value > max) {
      max = value
      maxAt = point.t
    }
  }

  return { current: last.v, at: last.t, max, maxAt, mean: sum / valid.length, total: sum }
}

/**
 * Un contador que solo crece se lee por su incremento entre intervalos. Un salto negativo es un
 * reinicio del contador, no un valor negativo de trafico: se emite 0.
 */
export function toIncrements(points: ChartPoint[]): ChartPoint[] {
  const out: ChartPoint[] = []
  let lastKnown: number | null = null

  points.forEach((point, index) => {
    const value = isNumeric(point.v) ? point.v : null

    if (index === 0) {
      out.push({ t: point.t, v: null })
      lastKnown = value
      return
    }

    if (value === null) {
      // No rompe la cadena: el siguiente punto valido compara contra el ultimo no nulo anterior.
      out.push({ t: point.t, v: null })
      return
    }

    if (lastKnown === null) {
      out.push({ t: point.t, v: null })
      lastKnown = value
      return
    }

    const delta = value - lastKnown
    out.push({ t: point.t, v: delta < 0 ? 0 : delta })
    lastKnown = value
  })

  return out
}

/** Suma por marca de tiempo de varias series. Las marcas que no comparten todas se conservan. */
export function sumSeries(series: ChartPoint[][]): ChartPoint[] {
  const sums = new Map<string, number>()
  const hasValue = new Set<string>()
  const times = new Set<string>()

  for (const points of series) {
    for (const point of points) {
      times.add(point.t)
      if (!isNumeric(point.v)) continue
      hasValue.add(point.t)
      sums.set(point.t, (sums.get(point.t) ?? 0) + point.v)
    }
  }

  return [...times].sort().map((t) => ({ t, v: hasValue.has(t) ? (sums.get(t) ?? 0) : null }))
}

function reduce(values: number[], how: How): number | null {
  if (!values.length) return null
  if (how === 'sum') return values.reduce((a, b) => a + b, 0)
  if (how === 'max') return Math.max(...values)
  return values.reduce((a, b) => a + b, 0) / values.length
}

function toZoned(iso: string, timeZone: string): DateTime | null {
  const dt = DateTime.fromISO(iso, { zone: 'utc' }).setZone(timeZone)
  return dt.isValid ? dt : null
}

/** 24 cubos, claves '0'..'23', rotulos '00 h'..'23 h'. */
export function byHourOfDay(points: ChartPoint[], timeZone: string, how: How): Bucket[] {
  const buckets: number[][] = Array.from({ length: 24 }, () => [])
  for (const point of points) {
    if (!isNumeric(point.v)) continue
    const dt = toZoned(point.t, timeZone)
    if (!dt) continue
    buckets[dt.hour].push(point.v)
  }
  return buckets.map((values, hour) => ({
    key: String(hour),
    label: `${String(hour).padStart(2, '0')} h`,
    value: reduce(values, how),
  }))
}

const WEEKDAY_LABELS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

/** 7 cubos empezando en lunes, rotulos 'Lunes'..'Domingo'. */
export function byWeekday(points: ChartPoint[], timeZone: string, how: How): Bucket[] {
  const buckets: number[][] = Array.from({ length: 7 }, () => [])
  for (const point of points) {
    if (!isNumeric(point.v)) continue
    const dt = toZoned(point.t, timeZone)
    if (!dt) continue
    // Luxon: weekday es 1 = lunes.
    buckets[dt.weekday - 1].push(point.v)
  }
  return buckets.map((values, index) => ({ key: String(index), label: WEEKDAY_LABELS[index], value: reduce(values, how) }))
}

/** Un cubo por dia natural, clave 'yyyy-MM-dd', rotulo 'dd/MM'. Sin huecos: los dias sin dato salen con value null. */
export function byDate(points: ChartPoint[], timeZone: string, how: How): Bucket[] {
  const byDay = new Map<string, number[]>()
  let minDay: DateTime | null = null
  let maxDay: DateTime | null = null

  for (const point of points) {
    const dt = toZoned(point.t, timeZone)
    if (!dt) continue
    const day = dt.startOf('day')
    if (!minDay || day < minDay) minDay = day
    if (!maxDay || day > maxDay) maxDay = day
    if (!isNumeric(point.v)) continue
    const key = day.toFormat('yyyy-MM-dd')
    const list = byDay.get(key) ?? []
    list.push(point.v)
    byDay.set(key, list)
  }

  if (!minDay || !maxDay) return []

  const out: Bucket[] = []
  for (let cursor = minDay; cursor <= maxDay; cursor = cursor.plus({ days: 1 })) {
    const key = cursor.toFormat('yyyy-MM-dd')
    out.push({ key, label: cursor.toFormat('dd/MM'), value: reduce(byDay.get(key) ?? [], how) })
  }
  return out
}

/** Matriz 7x24. `x` = hora 0..23, `y` = 0 lunes … 6 domingo, de arriba a abajo. */
export function byWeekHour(points: ChartPoint[], timeZone: string, how: How): MatrixCell[] {
  const buckets: number[][][] = Array.from({ length: 7 }, () => Array.from({ length: 24 }, () => []))
  for (const point of points) {
    if (!isNumeric(point.v)) continue
    const dt = toZoned(point.t, timeZone)
    if (!dt) continue
    buckets[dt.weekday - 1][dt.hour].push(point.v)
  }

  const cells: MatrixCell[] = []
  for (let y = 0; y < 7; y++) {
    for (let x = 0; x < 24; x++) cells.push({ x, y, value: reduce(buckets[y][x], how) })
  }
  return cells
}

/** Cubo con el valor mas alto, o null si todos son null. Sirve para «hora punta» y «dia punta». */
export function peakOf(buckets: Bucket[]): Bucket | null {
  let best: Bucket | null = null
  for (const bucket of buckets) {
    if (bucket.value === null) continue
    if (!best || (best.value !== null && bucket.value > best.value)) best = bucket
  }
  return best
}

/** Proporcion 0..1 de un valor respecto a un maximo, para elegir el color de nivel. */
export function levelRatio(value: number | null, max: number | null): number {
  return !max || max <= 0 || value === null ? 0 : Math.min(1, Math.max(0, value / max))
}
