import type { EntityOption } from '@/features/dashboards/api/catalog'
import { localizeMeasure } from '@/lib/measureCatalog'
import type { Measure } from '@/types'
import { DEFAULT_OPERATOR, DEFAULT_TIMEOUT_UNIT, TIMEOUT_UNITS, operatorArity } from './operators'
import type {
  AlarmAction,
  AlarmTrigger,
  AlarmType,
  BulkInactivityCondition,
  BulkThresholdCondition,
  ConditionOperator,
  ConditionPeriod,
  EmailActionContent,
  InactivityCondition,
  MeasureRef,
  NewEmailAction,
  NewInactivityCondition,
  NewThresholdCondition,
  ThresholdCondition,
} from '../types'

/**
 * Una condicion mientras se edita. Es lo que se pinta, no lo que se envia: guarda los umbrales
 * como texto porque un campo a medio escribir («-», «1,») no es un numero, y el plazo separado
 * en cantidad y unidad porque el servidor solo entiende segundos.
 */
export interface ConditionDraft {
  /** Identidad estable de la fila: sin ella, borrar una condicion reordena las demas. */
  key: number
  /** Id de la condicion ya guardada cuando se edita; ausente en una condicion nueva. */
  id?: number
  entity: EntityOption | null
  measure: Measure | null
  operator: ConditionOperator
  from: string
  to: string
  timeout: string
  timeoutUnit: number
  /** Restriccion horaria que el formulario no edita: se conserva tal cual al guardar. */
  period?: ConditionPeriod[] | null
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

function toEntityOption(entity: ThresholdCondition['entity']): EntityOption | null {
  if (!entity || entity.id == null) return null
  return {
    id: entity.id,
    name: entity.name ?? entity.urn ?? String(entity.id),
    urn: entity.urn ?? '',
    tenant: entity.tenant ?? '',
    scope: entity.scope ?? '',
    datamodel: entity.datamodel ?? '',
  }
}

/** La medida guardada llega solo con id y nombre; la tarjeta la completa (unidades) al cargar. */
function toMeasure(measure: MeasureRef | null | undefined): Measure | null {
  if (!measure || !measure.id) return null
  return localizeMeasure({ id: measure.id, name: measure.name ?? measure.id })
}

/** Expresa un plazo en segundos como cantidad + unidad, eligiendo la mayor unidad exacta. */
function splitTimeout(seconds: number): { timeout: string; unit: number } {
  const units = TIMEOUT_UNITS.map((u) => u.value).sort((a, b) => b - a)
  for (const unit of units) {
    if (seconds > 0 && seconds % unit === 0) return { timeout: String(seconds / unit), unit }
  }
  return { timeout: seconds ? String(seconds / DEFAULT_TIMEOUT_UNIT) : '', unit: DEFAULT_TIMEOUT_UNIT }
}

/** Reconstruye el borrador de una condicion de umbral ya guardada, para poder editarla. */
export function fromThresholdCondition(condition: ThresholdCondition): ConditionDraft {
  const threshold = Array.isArray(condition.threshold) ? condition.threshold : []
  return {
    ...newConditionDraft(),
    id: condition.id,
    entity: toEntityOption(condition.entity),
    measure: toMeasure(condition.measure),
    operator: (condition.condition as ConditionOperator) || DEFAULT_OPERATOR,
    from: threshold[0] != null ? String(threshold[0]) : '',
    to: threshold[1] != null ? String(threshold[1]) : '',
    period: condition.period ?? null,
  }
}

/** Reconstruye el borrador de una condicion de inactividad ya guardada. */
export function fromInactivityCondition(condition: InactivityCondition): ConditionDraft {
  const { timeout, unit } = splitTimeout(condition.timeoutS ?? 0)
  return {
    ...newConditionDraft(),
    id: condition.id,
    entity: toEntityOption(condition.entity),
    measure: toMeasure(condition.measure),
    timeout,
    timeoutUnit: unit,
  }
}

export function toBulkThresholdCondition(draft: ConditionDraft): BulkThresholdCondition {
  const base = toThresholdCondition(draft)
  const condition: BulkThresholdCondition = {
    entity: { id: base.entityId },
    measure: { id: base.measure },
    condition: base.condition,
    threshold: base.threshold,
    period: draft.period ?? null,
  }
  if (draft.id != null) condition.id = draft.id
  return condition
}

export function toBulkInactivityCondition(draft: ConditionDraft): BulkInactivityCondition {
  const base = toInactivityCondition(draft)
  const condition: BulkInactivityCondition = {
    entity: { id: base.entityId },
    measure: base.measure ?? null,
    timeoutS: base.timeoutS,
  }
  if (draft.id != null) condition.id = draft.id
  return condition
}

/**
 * Un aviso por correo mientras se edita en el formulario. `actionId` solo lo tienen los que ya
 * existen: sirve para saber, al guardar, cuales hay que borrar y cuales crear.
 */
export interface EmailAvisoDraft {
  key: number
  actionId?: number
  to: string[]
  subject: string
  body: string
  trigger: AlarmTrigger
}

let nextAvisoKey = 0

export function newEmailAvisoDraft(): EmailAvisoDraft {
  return { key: ++nextAvisoKey, to: [], subject: '', body: '', trigger: 'up' }
}

/** Validacion minima de un correo: suficiente para evitar erratas, sin pelearse con el RFC. */
export function isEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}

/** Un aviso esta listo para enviarse cuando tiene destinatarios validos, asunto y cuerpo. */
export function avisoComplete(draft: EmailAvisoDraft): boolean {
  return (
    draft.to.length > 0 &&
    draft.to.every((address) => isEmail(address)) &&
    !!draft.subject.trim() &&
    !!draft.body.trim()
  )
}

/** Reconstruye el borrador de un aviso por correo ya guardado, para listarlo y poder quitarlo. */
export function fromEmailAction(action: AlarmAction): EmailAvisoDraft {
  const content = (action.actionable_content ?? {}) as Partial<EmailActionContent>
  return {
    ...newEmailAvisoDraft(),
    actionId: action.action_id,
    to: Array.isArray(content.to) ? content.to.filter((item): item is string => typeof item === 'string') : [],
    subject: typeof content.subject === 'string' ? content.subject : '',
    body: typeof content.body === 'string' ? content.body : '',
    trigger: action.type === 'down' ? 'down' : 'up',
  }
}

export function toNewEmailAction(draft: EmailAvisoDraft): NewEmailAction {
  return { to: draft.to, subject: draft.subject, body: draft.body, trigger: draft.trigger }
}
