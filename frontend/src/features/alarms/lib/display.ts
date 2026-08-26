import { DateTime } from 'luxon'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import type { AlarmAction, AlarmRow, DateRange, RangePreset } from '../types'

/** Los booleanos del backend llegan como true, 1 o "t" segun el endpoint. */
export function asBool(value: unknown): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') return ['1', 'true', 't', 'yes'].includes(value.toLowerCase())
  return false
}

/**
 * Las fechas de los eventos llegan sin zona y con espacio en lugar de "T", formato que
 * el parser ISO rechaza. Se normaliza a UTC antes de darselo al formateador comun.
 */
export function normalizeIso(value?: string | null): string | null {
  if (!value) return null
  const trimmed = value.trim()
  if (!trimmed) return null
  const withSeparator = trimmed.replace(' ', 'T')
  return /(Z|[+-]\d{2}:?\d{2})$/.test(withSeparator) ? withSeparator : `${withSeparator}Z`
}

export function alarmTypeLabel(type?: string): string {
  if (type === 'basic') return t('alarms.type.basic')
  if (type === 'inactivity') return t('alarms.type.inactivity')
  return t('alarms.type.unknown')
}

export interface AlarmStatus {
  key: 'fired' | 'armed' | 'disabled'
  label: string
  hint: string
  icon: string
  /** Sin color el chip sale neutro, que es lo que corresponde a una alarma desactivada. */
  color?: 'error' | 'success'
}

/**
 * Estado de una alarma en un solo dato. «Habilitada» y «disparada» son propiedades
 * independientes en el backend y se confunden con facilidad: aqui se resuelven en los tres
 * estados que de verdad importan al leer un listado, por orden de precedencia.
 */
export function alarmStatus(alarm: Pick<AlarmRow, 'disabled' | 'up'>): AlarmStatus {
  if (asBool(alarm.disabled)) {
    return {
      key: 'disabled',
      label: t('alarms.state.disabled'),
      hint: t('alarms.state.disabledHint'),
      icon: 'mdi-bell-off-outline',
    }
  }
  if (asBool(alarm.up)) {
    return {
      key: 'fired',
      label: t('alarms.state.fired'),
      hint: t('alarms.state.firedHint'),
      icon: 'mdi-bell-ring-outline',
      color: 'error',
    }
  }
  return {
    key: 'armed',
    label: t('alarms.state.armed'),
    hint: t('alarms.state.armedHint'),
    icon: 'mdi-bell-check-outline',
    color: 'success',
  }
}

/** Fecha de ultima modificacion, sea del recurso serializado o del modelo en crudo. */
export function lastModified(alarm: AlarmRow): string | null {
  return normalizeIso(alarm.updatedAt ?? alarm.updated_at ?? null)
}

export function createdAt(alarm: AlarmRow): string | null {
  return normalizeIso(alarm.createdAt ?? alarm.created_at ?? null)
}

export function eventLevelColor(level?: string): string | undefined {
  const name = (level ?? '').toUpperCase()
  if (name.includes('ERROR') || name.includes('CRITICAL')) return 'error'
  if (name.includes('WARNING') || name.includes('WARN')) return 'warning'
  if (name.includes('INFO')) return 'info'
  return undefined
}

/** El nivel llega en ingles y en mayusculas; si no se reconoce se muestra tal cual. */
export function eventLevelLabel(level?: string): string {
  const name = (level ?? '').trim().toUpperCase()
  if (!name) return '—'
  if (name.includes('ERROR') || name.includes('CRITICAL')) return t('alarms.events.lvlError')
  if (name.includes('WARNING') || name.includes('WARN')) return t('alarms.events.lvlWarning')
  if (name.includes('INFO')) return t('alarms.events.lvlInfo')
  return name.charAt(0) + name.slice(1).toLowerCase()
}

const ACTION_KINDS: Record<string, { label: string; icon: string }> = {
  email: { label: 'alarms.action.email', icon: 'mdi-email-outline' },
  push: { label: 'alarms.action.push', icon: 'mdi-bell-ring-outline' },
  http_push: { label: 'alarms.action.httpPush', icon: 'mdi-webhook' },
  telegram: { label: 'alarms.action.telegram', icon: 'mdi-message-outline' },
  whatsapp: { label: 'alarms.action.whatsapp', icon: 'mdi-message-outline' },
  sms: { label: 'alarms.action.sms', icon: 'mdi-message-text-outline' },
  entity_command: { label: 'alarms.action.entityCommand', icon: 'mdi-console-line' },
}

export interface ActionChannel {
  label: string
  icon: string
  count: number
}

/** Solo el canal, sin destinatarios: el detalle de la alarma es de solo lectura. */
export function actionChannels(actions: AlarmAction[]): ActionChannel[] {
  const grouped = new Map<string, ActionChannel>()

  for (const action of actions) {
    const raw = (action.actionable_type ?? action.type ?? '').toLowerCase().replace(/^action_/, '')
    const kind = ACTION_KINDS[raw]
    const label = kind ? t(kind.label) : t('alarms.action.unknown')
    const current = grouped.get(label)
    if (current) current.count += 1
    else grouped.set(label, { label, icon: kind?.icon ?? 'mdi-bell-outline', count: 1 })
  }

  return [...grouped.values()]
}

export function rangeFromPreset(preset: RangePreset): DateRange {
  const end = DateTime.utc()
  const start =
    preset === '24h'
      ? end.minus({ hours: 24 })
      : preset === '7d'
        ? end.minus({ days: 7 })
        : end.minus({ days: 30 })
  return { start: start.toISO() ?? '', end: end.toISO() ?? '' }
}

/** El backend de eventos espera la fecha en UTC y sin sufijo de zona. */
export function toNaiveUtc(iso: string): string {
  const dt = DateTime.fromISO(iso, { zone: 'utc' })
  return dt.isValid ? dt.toFormat("yyyy-MM-dd'T'HH:mm:ss") : iso
}

export function humanDuration(seconds?: number): string | null {
  if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds <= 0) return null
  if (seconds < 60) return t('alarms.duration.seconds', { value: formatNumber(seconds) })
  if (seconds < 3600) return t('alarms.duration.minutes', { value: formatNumber(seconds / 60) })
  if (seconds < 86_400) return t('alarms.duration.hours', { value: formatNumber(seconds / 3600) })
  return t('alarms.duration.days', { value: formatNumber(seconds / 86_400) })
}
