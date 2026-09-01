import type { AriaComponentOption } from 'echarts'
import { t } from '@/i18n'
import { formatDateTime, formatNumber } from '@/lib/format'
import { toMillis } from './chartOptions'
import type { ChartSeries } from './types'

/**
 * Alternativa textual de las graficas (WCAG 1.1.1, hallazgo GDTIS-PT01-ACC-002).
 *
 * Todas las graficas se dibujan en un `<canvas>`: para un lector de pantalla son un pixel. La
 * via correcta NO es describir la imagen —«grafico de lineas ascendente» no permite consultar
 * un valor—, sino ofrecer LOS MISMOS DATOS que alimentan el dibujo en una tabla. Eso es lo que
 * construye este modulo, y `DataTableAlternative.vue` lo pinta.
 *
 * Se complementa con el modulo `aria` de ECharts, que pone `role="img"` y un nombre accesible
 * en el contenedor del lienzo; sin activarlo, el `<canvas>` no tiene ni nombre.
 */

/** Tope de filas de la tabla equivalente. Mas alla, la tabla deja de ser navegable. */
export const MAX_ALTERNATIVE_ROWS = 200

export interface AlternativeTable {
  columns: string[]
  rows: string[][]
  /** Filas que habria sin recortar. Si es mayor que `rows.length`, la tabla esta truncada. */
  total: number
}

export const EMPTY_TABLE: AlternativeTable = { columns: [], rows: [], total: 0 }

/**
 * Opciones `aria` de ECharts.
 *
 * `label.description` sustituye a la descripcion que genera ECharts por su cuenta, que enumera
 * series y valores en ingles y sin formato: aqui se le da el titulo real del panel y se remite
 * a la tabla, que es la alternativa util.
 */
export function ariaOption(title: string): AriaComponentOption {
  return {
    enabled: true,
    label: {
      enabled: true,
      description: t('a11y.chart.description', { title }),
    },
  }
}

/** Etiqueta de una marca del eje: fecha con formato si lo es, y el texto tal cual si no. */
export function stampLabel(raw: string, timeZone: string): string {
  return Number.isFinite(toMillis(raw)) ? formatDateTime(raw, timeZone) : raw
}

function byTime(a: string, b: string, direction: 1 | -1): number {
  const left = toMillis(a)
  const right = toMillis(b)
  if (Number.isFinite(left) && Number.isFinite(right)) return (left - right) * direction
  return a.localeCompare(b) * direction
}

export interface SeriesTableOptions {
  timeZone: string
  units?: string
  limit?: number
  /** 'asc' lee como el grafico, de izquierda a derecha; 'desc' pone lo reciente arriba. */
  order?: 'asc' | 'desc'
  /** Rotulo de la primera columna. Por defecto, «Fecha y hora». */
  stampLabelText?: string
}

/**
 * Tabla equivalente de un conjunto de series: una fila por marca de tiempo y una columna por
 * serie. Es exactamente el dato que recibe la grafica, sin interpretarlo.
 *
 * Se descartan las marcas en las que ninguna serie tiene valor: una fila entera de guiones no
 * aporta nada y alarga la tabla.
 */
export function seriesTable(series: ChartSeries[], options: SeriesTableOptions): AlternativeTable {
  const { timeZone, units, limit = MAX_ALTERNATIVE_ROWS, order = 'asc' } = options
  if (!series.length) return EMPTY_TABLE

  const unitsOf = (serie: ChartSeries) => serie.units ?? units
  const columns = [
    options.stampLabelText ?? t('dashboards.chart.datetime'),
    ...series.map((serie) => (unitsOf(serie) ? `${serie.name} (${unitsOf(serie)})` : serie.name)),
  ]

  const stamps = new Set<string>()
  for (const serie of series) {
    for (const point of serie.points) if (point.v !== null && point.v !== undefined) stamps.add(point.t)
  }

  const values = series.map((serie) => new Map(serie.points.map((point) => [point.t, point.v])))
  const sorted = [...stamps].sort((a, b) => byTime(a, b, order === 'asc' ? 1 : -1))

  const rows = sorted
    .slice(0, limit)
    .map((stamp) => [
      stampLabel(stamp, timeZone),
      ...values.map((map) => formatNumber(map.get(stamp) ?? null)),
    ])

  return { columns, rows, total: sorted.length }
}

/** Tabla equivalente de una lista de pares etiqueta/valor (reparto, marcadores, nodos…). */
export function pairsTable(
  pairs: { label: string; value: string }[],
  columns: [string, string],
  limit = MAX_ALTERNATIVE_ROWS,
): AlternativeTable {
  return {
    columns,
    rows: pairs.slice(0, limit).map((pair) => [pair.label, pair.value]),
    total: pairs.length,
  }
}

/** Tabla equivalente a partir de filas ya formateadas. Para graficas con estructura propia. */
export function rowsTable(
  columns: string[],
  rows: string[][],
  limit = MAX_ALTERNATIVE_ROWS,
): AlternativeTable {
  return { columns, rows: rows.slice(0, limit), total: rows.length }
}
