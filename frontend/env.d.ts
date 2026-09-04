/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_OIDC_URL: string
  readonly VITE_OIDC_REALM: string
  readonly VITE_OIDC_CLIENT_ID: string
  readonly VITE_OIDC_REDIRECT_URI?: string
  readonly VITE_MAP_TILES_URL: string
  readonly VITE_MAP_TILES_URL_DARK?: string
  readonly VITE_MAP_TILES_ATTRIBUTION: string
  readonly VITE_MAP_TILES_ATTRIBUTION_DARK?: string
  readonly VITE_MAP_DEFAULT_CENTER: string
  readonly VITE_MAP_DEFAULT_ZOOM: string
  readonly VITE_REALTIME_URL?: string
  /** Identificadores tecnicos del backend. No son marca. Ver src/api/platform-contract.ts */
  readonly VITE_DATA_SCOPE_PREFERENCE_KEY?: string
  readonly VITE_ALARM_ENTITY_TYPE?: string
  /** Via de contacto de accesibilidad del organismo titular (RD 1112/2018). */
  readonly VITE_ACCESSIBILITY_CONTACT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/**
 * Configuracion inyectada por el contenedor en /config.js. Se lee con los ayudantes de
 * `src/lib/env.ts`, que caen en las variables de compilacion cuando no esta definida.
 */
interface Window {
  __APP_CONFIG__?: Record<string, string>
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}
