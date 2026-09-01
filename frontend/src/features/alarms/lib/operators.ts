import { t } from '@/i18n'
import type { ConditionOperator } from '../types'

/**
 * Operadores de umbral que acepta el servidor, con el numero de valores que pide cada uno.
 * La aridad se declara aqui y no en la vista porque de ella depende tanto cuantos campos se
 * pintan como cuantos se envian: si divergen, el servidor guarda un intervalo a medias.
 */
export interface OperatorOption {
  value: ConditionOperator
  labelKey: string
  /** Numero de valores del umbral: uno, salvo los operadores que definen un intervalo. */
  arity: 1 | 2
}

export const OPERATORS: readonly OperatorOption[] = [
  { value: 'gt', labelKey: 'alarms.form.op.gt', arity: 1 },
  { value: 'ge', labelKey: 'alarms.form.op.ge', arity: 1 },
  { value: 'lt', labelKey: 'alarms.form.op.lt', arity: 1 },
  { value: 'le', labelKey: 'alarms.form.op.le', arity: 1 },
  { value: 'eq', labelKey: 'alarms.form.op.eq', arity: 1 },
  { value: 'ne', labelKey: 'alarms.form.op.ne', arity: 1 },
  { value: 'between', labelKey: 'alarms.form.op.between', arity: 2 },
  { value: 'not_between', labelKey: 'alarms.form.op.notBetween', arity: 2 },
] as const

export const DEFAULT_OPERATOR: ConditionOperator = 'gt'

export function operatorArity(value: ConditionOperator): 1 | 2 {
  return OPERATORS.find((operator) => operator.value === value)?.arity ?? 1
}

/** Opciones ya rotuladas para un desplegable. */
export function operatorItems(): { value: ConditionOperator; title: string }[] {
  return OPERATORS.map((operator) => ({ value: operator.value, title: t(operator.labelKey) }))
}

/** Multiplicadores a segundos de las unidades que ofrece el plazo de inactividad. */
export const TIMEOUT_UNITS = [
  { value: 60, labelKey: 'alarms.form.unitMinutes' },
  { value: 3600, labelKey: 'alarms.form.unitHours' },
  { value: 86_400, labelKey: 'alarms.form.unitDays' },
] as const

export const DEFAULT_TIMEOUT_UNIT = 60
