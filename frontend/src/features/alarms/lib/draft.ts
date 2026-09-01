import type { EntityOption } from '@/features/dashboards/api/catalog'
import type { Measure } from '@/types'
import { DEFAULT_OPERATOR, DEFAULT_TIMEOUT_UNIT, operatorArity } from './operators'
import type {
  AlarmType,
  ConditionOperator,
  NewInactivityCondition,
  NewThresholdCondition,
} from '../types'

/**
 * Una condicion mientras se edita. Es lo que se pinta, no lo que se envia: guarda los umbrales
 * como texto porque un campo a medio escribir («-», «1,») no es un numero, y el plazo separado
 * en cantidad y unidad porque el servidor solo entiende segundos.
 */
export interface ConditionDraft {
  /** Identidad estable de la fila: sin ella, borrar una condicion reordena las demas. */
  key: number
  entity: EntityOption | null
  measure: Measure | null
  operator: ConditionOperator
  from: string
  to: string
  timeout: string
  timeoutUnit: number
}

let nextKey = 0

export function newConditionDraft(): ConditionDraft {
  return {
    key: ++nextKey,
    entity: null,
    measure: null,
    operator: DEFAULT_OPERATOR,
    from: '',
    to: '',
    timeout: '',
    timeoutUnit: DEFAULT_TIMEOUT_UNIT,
  }
}

/**
 * Lee un numero escrito a mano. Se admite la coma decimal porque es la que produce el teclado
 * de quien escribe en espanol, y rechazarla obligaria a teclear un separador que no usa.
 */
export function parseNumber(value: string): number | null {
  const text = value.trim().replace(',', '.')
  if (!text) return null
  const numeric = Number(text)
  return Number.isFinite(numeric) ? numeric : null
}

/** Una condicion esta completa cuando se puede enviar sin que el servidor la rechace. */
export function conditionComplete(draft: ConditionDraft, type: AlarmType): boolean {
  if (!draft.entity) return false

  if (type === 'inactivity') {
    const timeout = parseNumber(draft.timeout)
    return timeout !== null && timeout > 0
  }

  if (!draft.measure) return false
  if (parseNumber(draft.from) === null) return false
  return operatorArity(draft.operator) === 1 || parseNumber(draft.to) !== null
}

export function toThresholdCondition(draft: ConditionDraft): NewThresholdCondition {
  const from = parseNumber(draft.from) ?? 0
  const threshold =
    operatorArity(draft.operator) === 2 ? [from, parseNumber(draft.to) ?? 0] : [from]

  return {
    entityId: draft.entity!.id,
    measure: draft.measure!.id,
    condition: draft.operator,
    threshold,
  }
}

export function toInactivityCondition(draft: ConditionDraft): NewInactivityCondition {
  const condition: NewInactivityCondition = {
    entityId: draft.entity!.id,
    // El servidor almacena segundos enteros: la cantidad y la unidad solo existen en el formulario.
    timeoutS: Math.round((parseNumber(draft.timeout) ?? 0) * draft.timeoutUnit),
  }

  // La medida es opcional en inactividad: sin ella se vigila que la entidad envie cualquier dato.
  if (draft.measure) condition.measure = draft.measure.id

  return condition
}
