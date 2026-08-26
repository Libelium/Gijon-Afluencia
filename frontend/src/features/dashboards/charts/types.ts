export type ChartKind = 'line' | 'bar' | 'pie' | 'gauge' | 'kpi' | 'table' | 'unsupported'

export interface ChartPoint {
  t: string
  v: number | null
}

export interface ChartSeries {
  name: string
  units?: string
  points: ChartPoint[]
}

export interface ChartData {
  series: ChartSeries[]
}
