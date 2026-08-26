import type { Aggregation } from '@/types'
import type { ChartKind } from '../charts'

export type ChartTypeId = 'line' | 'area' | 'bar' | 'stackedBar' | 'pie' | 'gauge' | 'kpi' | 'table'

export interface ChartTypeOption {
  id: ChartTypeId
  /** Familia con la que lo dibujara ChartRenderer. */
  kind: ChartKind
  labelKey: string
  icon: string
  /** Graficos de ultimo valor: la agregacion y el intervalo no les afectan. */
  lastValueOnly: boolean
}

export const CHART_TYPES: ChartTypeOption[] = [
  { id: 'line', kind: 'line', labelKey: 'dashboards.chartType.line', icon: 'mdi-chart-line', lastValueOnly: false },
  { id: 'area', kind: 'line', labelKey: 'dashboards.chartType.area', icon: 'mdi-chart-areaspline', lastValueOnly: false },
  { id: 'bar', kind: 'bar', labelKey: 'dashboards.chartType.bar', icon: 'mdi-chart-bar', lastValueOnly: false },
  { id: 'stackedBar', kind: 'bar', labelKey: 'dashboards.chartType.stackedBar', icon: 'mdi-chart-bar-stacked', lastValueOnly: false },
  { id: 'pie', kind: 'pie', labelKey: 'dashboards.chartType.pie', icon: 'mdi-chart-donut', lastValueOnly: false },
  { id: 'gauge', kind: 'gauge', labelKey: 'dashboards.chartType.gauge', icon: 'mdi-gauge', lastValueOnly: true },
  { id: 'kpi', kind: 'kpi', labelKey: 'dashboards.chartType.kpi', icon: 'mdi-numeric', lastValueOnly: true },
  { id: 'table', kind: 'table', labelKey: 'dashboards.chartType.table', icon: 'mdi-table-large', lastValueOnly: false },
]

export const DEFAULT_CHART_TYPE: ChartTypeId = 'line'

export function chartTypeOption(id: string): ChartTypeOption | null {
  return CHART_TYPES.find((option) => option.id === id) ?? null
}

/** Funciones de agregacion que acepta el servicio de datos, en el orden en que se ofrecen. */
export const AGGREGATIONS: { value: Aggregation; labelKey: string }[] = [
  { value: 'mean', labelKey: 'dashboards.aggregation.mean' },
  { value: 'max', labelKey: 'dashboards.aggregation.max' },
  { value: 'min', labelKey: 'dashboards.aggregation.min' },
  { value: 'sum', labelKey: 'dashboards.aggregation.sum' },
]

export const DEFAULT_AGGREGATION: Aggregation = 'mean'

/** El vacio significa «automatico»: lo decide resolveAggregation() por el rango consultado. */
export const INTERVALS: { value: string; labelKey: string }[] = [
  { value: '', labelKey: 'dashboards.interval.auto' },
  { value: 'PT1H', labelKey: 'dashboards.interval.hour' },
  { value: 'PT24H', labelKey: 'dashboards.interval.day' },
  { value: 'PT168H', labelKey: 'dashboards.interval.week' },
]
