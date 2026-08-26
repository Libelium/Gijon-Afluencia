import { t } from '@/i18n'
import { formatNumber, urnTail } from '@/lib/format'
import { humanDuration } from './display'
import type {
  ConditionEntity,
  ConditionPeriod,
  InactivityCondition,
  MeasureRef,
  ThresholdCondition,
} from '../types'

/**
 * Traduccion de las condiciones a lenguaje natural. Las frases se construyen aqui y se
 * pintan por interpolacion de texto: los nombres vienen del backend sin sanear.
 */

const WEEK_DAYS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

function joinList(parts: string[]): string {
  if (parts.length <= 1) return parts[0] ?? ''
  return `${parts.slice(0, -1).join(', ')} y ${parts[parts.length - 1]}`
}

function capitalize(text: string): string {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text
}

function measureLabel(measure?: MeasureRef | null): string {
  const raw = measure?.name?.trim() || measure?.id?.trim() || ''
  return raw ? capitalize(raw) : '—'
}

function entityLabel(entity?: ConditionEntity | null): string {
  const name = entity?.name?.trim()
  if (name) return name
  const tail = entity?.urn ? urnTail(entity.urn) : ''
  return tail && tail !== '—' ? tail : '—'
}

function thresholdValue(threshold: Array<string | number> | undefined, index: number): string {
  const raw = threshold?.[index]
  if (raw === undefined || raw === null || raw === '') return t('alarms.cond.unknownValue')
  const numeric = typeof raw === 'number' ? raw : Number(raw)
  return Number.isFinite(numeric) ? formatNumber(numeric, 3) : String(raw)
}

function operatorPhrase(condition: ThresholdCondition): string {
  const value = thresholdValue(condition.threshold, 0)
  switch (condition.condition) {
    case 'gt':
      return t('alarms.cond.op.gt', { value })
    case 'ge':
      return t('alarms.cond.op.ge', { value })
    case 'lt':
      return t('alarms.cond.op.lt', { value })
    case 'le':
      return t('alarms.cond.op.le', { value })
    case 'eq':
      return t('alarms.cond.op.eq', { value })
    case 'ne':
      return t('alarms.cond.op.ne', { value })
    case 'between':
      return t('alarms.cond.op.between', { from: value, to: thresholdValue(condition.threshold, 1) })
    case 'not_between':
      return t('alarms.cond.op.notBetween', {
        from: value,
        to: thresholdValue(condition.threshold, 1),
      })
    default:
      return t('alarms.cond.op.unknown')
  }
}

function hourLabel(value: unknown): string | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return `${String(value).padStart(2, '0')}:00`
  }
  if (typeof value === 'string' && value.trim()) return value.trim().slice(0, 5)
  return null
}

function hoursPhrase(hours: ConditionPeriod['hours']): string | null {
  if (!Array.isArray(hours) || hours.length === 0) return null

  const ranges: string[] = []
  const single: string[] = []

  for (const entry of hours) {
    if (Array.isArray(entry)) {
      const from = hourLabel(entry[0])
      const to = hourLabel(entry[1])
      if (from && to) ranges.push(t('alarms.cond.periodHours', { from, to }))
      else if (from) single.push(from)
      continue
    }
    const label = hourLabel(entry)
    if (label) single.push(label)
  }

  if (ranges.length) return joinList(ranges)
  if (single.length) return t('alarms.cond.periodHoursList', { hours: joinList(single) })
  return null
}

function daysPhrase(period: ConditionPeriod): string | null {
  const indexes: number[] = []

  if (Array.isArray(period.week_days)) {
    for (const day of period.week_days) {
      if (typeof day === 'number' && day >= 0 && day <= 6) indexes.push(day)
    }
  } else if (typeof period.day === 'number' && period.day >= 1 && period.day <= 7) {
    indexes.push(period.day - 1)
  }

  if (!indexes.length) return null
  const names = indexes.map((i) => WEEK_DAYS[i]).filter(Boolean)
  return names.length ? t('alarms.cond.periodDays', { days: joinList(names) }) : null
}

/** Restriccion horaria de la condicion, si el backend la trae en un formato reconocible. */
export function periodPhrase(periods?: ConditionPeriod[] | null): string | null {
  if (!Array.isArray(periods) || periods.length === 0) return null

  const period = periods[0]
  if (!period || typeof period !== 'object') return null

  const parts = [daysPhrase(period), hoursPhrase(period.hours)].filter(Boolean) as string[]
  return parts.length ? t('alarms.cond.period', { when: parts.join(' ') }) : null
}

/**
 * La condicion se entrega partida en sujeto y operador para poder destacar el operador al
 * pintarla. Se interpola como texto, nunca como HTML: los nombres vienen del backend sin sanear.
 */
export interface ConditionLine {
  key: string
  kind: 'threshold' | 'inactivity'
  icon: string
  subject: string
  operator: string
  period: string | null
}

function join(measure: string, entity: string): string {
  if (measure !== '—' && entity !== '—') return t('alarms.cond.subject', { measure, entity })
  return measure !== '—' ? measure : entity
}

function thresholdLine(condition: ThresholdCondition, index: number): ConditionLine {
  return {
    key: `threshold-${condition.id ?? index}`,
    kind: 'threshold',
    icon: 'mdi-tune-variant',
    subject: join(measureLabel(condition.measure), entityLabel(condition.entity)),
    operator: operatorPhrase(condition),
    period: periodPhrase(condition.period),
  }
}

function inactivityLine(condition: InactivityCondition, index: number): ConditionLine {
  const entity = entityLabel(condition.entity)
  const raw = condition.measure?.name?.trim() || condition.measure?.id?.trim() || ''
  const duration = humanDuration(condition.timeoutS)

  return {
    key: `inactivity-${condition.id ?? index}`,
    kind: 'inactivity',
    icon: 'mdi-timer-sand-empty',
    subject: raw
      ? t('alarms.cond.inactivitySubject', { measure: capitalize(raw), entity })
      : t('alarms.cond.inactivitySubjectNoMeasure', { entity }),
    operator: duration
      ? t('alarms.cond.inactivityFor', { duration })
      : t('alarms.cond.inactivityAnyTimeout'),
    period: null,
  }
}

export function conditionLines(
  thresholds: ThresholdCondition[],
  inactivity: InactivityCondition[],
): ConditionLine[] {
  return [...thresholds.map(thresholdLine), ...inactivity.map(inactivityLine)]
}

export function conditionsIntro(fn: string | undefined, count: number): string {
  if (count <= 1) return t('alarms.cond.single')
  if (fn === 'OR') return t('alarms.cond.any')
  if (fn === 'XOR') return t('alarms.cond.one')
  return t('alarms.cond.all')
}
