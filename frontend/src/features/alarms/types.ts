import type { Alarm, SeriesPoint } from '@/types'

/** Operadores admitidos por el backend en las condiciones por umbral. */
export type ConditionOperator = 'gt' | 'ge' | 'lt' | 'le' | 'eq' | 'ne' | 'between' | 'not_between'

/** Combinacion de condiciones de una alarma. */
export type AlarmFunction = 'AND' | 'OR' | 'XOR'

/**
 * El listado devuelve el modelo en crudo (snake_case) y el detalle el recurso serializado
 * (camelCase), asi que ambas variantes son opcionales y se leen con tolerancia.
 */
export interface AlarmRow extends Alarm {
  function?: string
  updatedAt?: string
  created_at?: string
  updated_at?: string
}

export interface ConditionEntity {
  id?: number
  name?: string
  urn?: string
  datamodel?: string
  tenant?: string | null
  scope?: string | null
}

export interface MeasureRef {
  id?: string
  name?: string
}

/** Restriccion temporal opcional de una condicion. */
export interface ConditionPeriod {
  months?: number[]
  month_days?: number[]
  week_days?: number[]
  hours?: Array<string[] | number[] | number | string>
  day?: number
}

export interface ThresholdCondition {
  id?: number
  alarmId?: number
  entity?: ConditionEntity | null
  measure?: MeasureRef | null
  condition?: string
  threshold?: Array<string | number>
  period?: ConditionPeriod[] | null
}

export interface InactivityCondition {
  id?: number
  alarmId?: number
  entity?: ConditionEntity | null
  measure?: MeasureRef | null
  timeoutS?: number
}

export interface AlarmDetail extends AlarmRow {
  conditions?: ThresholdCondition[] | null
  inactivityConditions?: InactivityCondition[] | null
}

export interface AlarmAction {
  type?: string
  action_id?: number
  actionable_id?: number
  actionable_type?: string
  actionable_content?: Record<string, unknown>
}

export type EventLevel = 'ALL' | 'INFO' | 'WARNING' | 'ERROR'

export type RangePreset = '24h' | '7d' | '30d'

/** Intervalo en ISO 8601 UTC. */
export interface DateRange {
  start: string
  end: string
}

/**
 * El historico de estado depende de identificadores del despliegue: si no se pueden
 * resolver se dice por que, en lugar de mostrar un grafico vacio sin explicacion.
 */
export type StatusSeries =
  | { state: 'ok'; points: SeriesPoint[] }
  | { state: 'unconfigured' }
  | { state: 'unresolved' }

/** Tipos de alarma que admite el servidor. */
export type AlarmType = 'basic' | 'inactivity'

/**
 * Condiciones tal y como las espera POST /alarms: en el alta viajan dentro de la alarma y con
 * nombres en camelCase, no como los devuelve el detalle.
 */
export interface NewThresholdCondition {
  entityId: number
  measure: string
  condition: ConditionOperator
  threshold: number[]
}

export interface NewInactivityCondition {
  entityId: number
  measure?: string
  timeoutS: number
}

/**
 * Alta de una alarma. `up` es el estado de disparo, no configuracion: una alarma recien creada
 * nace en reposo. `function` es obligatorio para el servidor incluso cuando hay una sola
 * condicion o la alarma es de inactividad, donde no combina nada.
 */
export interface NewAlarm {
  name: string
  type: AlarmType
  function: AlarmFunction
  up: boolean
  disabled: boolean
  conditions: Array<NewThresholdCondition | NewInactivityCondition>
}
