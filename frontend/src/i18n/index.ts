import base from './es'
import entities from '@/features/entities/i18n'
import map from '@/features/map/i18n'
import dashboards from '@/features/dashboards/i18n'
import alarms from '@/features/alarms/i18n'
import preferences from '@/features/preferences/i18n'
import customization from '@/features/customization/i18n'
import accessibility from '@/features/accessibility/i18n'

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
  ...accessibility,
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

/**
 * Idioma de la interfaz.
 *
 * La aplicacion tiene UN diccionario, en castellano, y el idioma de la pagina se declara a
 * partir de el —no como literal suelto en `index.html`— para que las dos cosas no puedan
 * separarse (WCAG 3.1.1, hallazgo GDTIS-PT01-ACC-005).
 *
 * La preferencia de usuario «Idioma» NO cambia esto: gobierna los textos que genera el servidor
 * (correos de aviso), y por eso su rotulo lo dice. El dia que exista un segundo diccionario,
 * este par de constantes pasa a derivarse de la preferencia y `applyDocumentLanguage` se llama
 * tambien al cambiarla; hasta entonces, declarar «es» es la unica opcion veraz.
 */
export const language = 'es'
export const locale = 'es-ES'

/** Escribe el idioma en `<html lang>`. Se llama una vez, al arrancar. */
export function applyDocumentLanguage(): void {
  document.documentElement.lang = language
}
