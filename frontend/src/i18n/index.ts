import base from './es'
import entities from '@/features/entities/i18n'
import map from '@/features/map/i18n'
import dashboards from '@/features/dashboards/i18n'
import alarms from '@/features/alarms/i18n'
import preferences from '@/features/preferences/i18n'
import customization from '@/features/customization/i18n'

/**
 * Cada feature aporta su fragmento y el nucleo los fusiona, de modo que ningun modulo
 * necesita editar un fichero compartido. Sustituible por vue-i18n sin tocar las vistas.
 */
const messages: Record<string, string> = {
  ...base,
  ...entities,
  ...map,
  ...dashboards,
  ...alarms,
  ...preferences,
  ...customization,
}

export function t(key: string, params?: Record<string, string | number>): string {
  const raw = messages[key]
  if (raw === undefined) {
    if (import.meta.env.DEV) console.warn(`[i18n] clave sin traducir: ${key}`)
    return key
  }
  if (!params) return raw
  return raw.replace(/\{(\w+)\}/g, (_, p: string) => String(params[p] ?? `{${p}}`))
}

export const locale = 'es-ES'
