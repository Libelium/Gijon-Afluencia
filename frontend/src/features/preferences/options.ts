import { t } from '@/i18n'

/** Nombres exactos que espera el backend: se envian tal cual en la ruta de la peticion. */
export const PREFERENCE_NAMES = [
  'language',
  'timeZone',
  'datetimeFormat',
  'numberFormat',
  'displayskinMode',
] as const

export type PreferenceName = (typeof PREFERENCE_NAMES)[number]

export type PreferenceValues = Record<PreferenceName, string>

export const DEFAULTS: PreferenceValues = {
  language: 'es',
  timeZone: 'Europe/Madrid',
  datetimeFormat: 'es-ES',
  numberFormat: 'es-ES',
  displayskinMode: 'system',
}

export interface Choice {
  value: string
  title: string
  icon?: string
}

export interface TimeZoneChoice {
  value: string
  title: string
}

export const LANGUAGES: Choice[] = [
  { value: 'es', title: 'preferences.language.es', icon: 'mdi-translate' },
  { value: 'en', title: 'preferences.language.en', icon: 'mdi-translate' },
]

export const DATETIME_FORMATS: Choice[] = [
  { value: 'es-ES', title: 'preferences.datetimeFormat.esES' },
  { value: 'en-US', title: 'preferences.datetimeFormat.enUS' },
  { value: 'ISO-8601', title: 'preferences.datetimeFormat.iso' },
]

export const NUMBER_FORMATS: Choice[] = [
  { value: 'es-ES', title: 'preferences.numberFormat.esES' },
  { value: 'en-EN', title: 'preferences.numberFormat.enEN' },
]

export const THEME_MODES: Choice[] = [
  { value: 'light', title: 'preferences.theme.light', icon: 'mdi-weather-sunny' },
  { value: 'dark', title: 'preferences.theme.dark', icon: 'mdi-weather-night' },
  { value: 'system', title: 'preferences.theme.system', icon: 'mdi-theme-light-dark' },
]

/** Las listas guardan claves de traduccion; se resuelven aqui para no repetir `t` en la plantilla. */
export function translated(choices: Choice[]): Choice[] {
  return choices.map((c) => ({ ...c, title: t(c.title) }))
}

/**
 * Un valor ya guardado que no figura en la lista se ofrece igualmente: si no, el desplegable
 * mostraria un codigo tecnico sin etiqueta y no habria forma de volver a el.
 */
export function withStored(choices: Choice[], value: string): Choice[] {
  if (!value || choices.some((c) => c.value === value)) return choices
  return [...choices, { value, title: t('preferences.unknownOption', { value }) }]
}

/** El tema solo puede ser uno de los tres modos: otro valor no se puede representar. */
export function themeModeOr(value: string | undefined, fallback: string): string {
  return THEME_MODES.some((m) => m.value === value) ? (value as string) : fallback
}

export function labelFor(name: PreferenceName): string {
  return t(`preferences.field.${name}`)
}

export function browserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || DEFAULTS.timeZone
  } catch {
    return DEFAULTS.timeZone
  }
}

export function timeZoneChoices(extra?: string): TimeZoneChoice[] {
  const zones = new Set<string>(Intl.supportedValuesOf('timeZone'))
  zones.add(DEFAULTS.timeZone)
  zones.add(browserTimeZone())
  if (extra) zones.add(extra)
  return [...zones].sort().map((value) => ({ value, title: value.replace(/_/g, ' ') }))
}

const offsets = new Map<string, string>()

/** Calcular el desfase de las 400+ zonas de golpe bloquea el hilo: se resuelve por zona y se memoiza. */
export function offsetLabel(zone: string): string {
  const cached = offsets.get(zone)
  if (cached) return cached
  let label = '—'
  try {
    const parts = new Intl.DateTimeFormat('es-ES', {
      timeZone: zone,
      timeZoneName: 'longOffset',
    }).formatToParts(new Date())
    label = parts.find((p) => p.type === 'timeZoneName')?.value || '—'
  } catch {
    label = '—'
  }
  offsets.set(zone, label)
  return label
}
