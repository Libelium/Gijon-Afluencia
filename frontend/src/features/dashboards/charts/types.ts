export type ChartKind = 'line' | 'bar' | 'pie' | 'gauge' | 'kpi' | 'table' | 'unsupported'

export interface ChartPoint {
  t: string
  v: number | null
}

export interface ChartSeries {
  name: string
  units?: string
  points: ChartPoint[]
  /** Solo puntos, sin linea: instantes sueltos marcados sobre otra serie (las horas anomalas). */
  markers?: boolean
}

export interface ChartData {
  series: ChartSeries[]
}
