/**
 * Lectura de configuracion con dos origenes, en este orden:
 *
 *  1. `window.__APP_CONFIG__`, que el contenedor escribe en `config.js` al arrancar.
 *  2. Las variables `VITE_*` incrustadas al compilar.
 *
 * Por que hace falta: Vite sustituye `import.meta.env.VITE_*` por literales durante la
 * compilacion, asi que una imagen construida para un entorno no serviria para otro. Leyendo
 * primero de `window.__APP_CONFIG__` la misma imagen vale para todos los entornos, y en
 * desarrollo se sigue usando el `.env` de siempre porque ese objeto llega vacio.
 *
 * Nada de lo que se lea aqui es secreto: `config.js` lo descarga cualquier visitante.
 */
export type ConfigKey =
  | 'VITE_API_BASE_URL'
  | 'VITE_OIDC_URL'
  | 'VITE_OIDC_REALM'
  | 'VITE_OIDC_CLIENT_ID'
  | 'VITE_OIDC_REDIRECT_URI'
  | 'VITE_MAP_TILES_URL'
  | 'VITE_MAP_TILES_ATTRIBUTION'
  | 'VITE_MAP_DEFAULT_CENTER'
  | 'VITE_MAP_DEFAULT_ZOOM'
  | 'VITE_REALTIME_URL'
  | 'VITE_DATA_SCOPE_PREFERENCE_KEY'
  | 'VITE_ALARM_ENTITY_TYPE'

const runtime: Partial<Record<ConfigKey, string>> =
  (typeof window !== 'undefined' && window.__APP_CONFIG__) || {}

const build = import.meta.env as unknown as Partial<Record<ConfigKey, string>>

/** Valor de configuracion, o la cadena vacia si no esta definido en ningun origen. */
export function env(key: ConfigKey, fallback = ''): string {
  const value = runtime[key] ?? build[key]
  return value === undefined || value === '' ? fallback : value
}

export function envNumber(key: ConfigKey, fallback: number): number {
  const parsed = Number(env(key))
  return Number.isFinite(parsed) ? parsed : fallback
}

/** Claves obligatorias que no estan definidas. Sirve para avisar en el arranque. */
export function missingRequired(): ConfigKey[] {
  const required: ConfigKey[] = [
    'VITE_API_BASE_URL',
    'VITE_OIDC_URL',
    'VITE_OIDC_REALM',
    'VITE_OIDC_CLIENT_ID',
  ]
  return required.filter((key) => !env(key))
}
