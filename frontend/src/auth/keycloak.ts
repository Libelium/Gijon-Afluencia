import Keycloak from 'keycloak-js'
import { env } from '@/lib/env'

const kc = new Keycloak({
  url: env('VITE_OIDC_URL'),
  realm: env('VITE_OIDC_REALM'),
  clientId: env('VITE_OIDC_CLIENT_ID'),
})

let initialised = false
let refreshTimer: number | undefined

const INTENDED_KEY = 'pidgijon.intendedPath'

/**
 * El proveedor de identidad solo admite URIs de retorno dadas de alta. Se usa siempre la misma
 * ruta publica de callback y la aplicacion recuerda a donde queria ir el usuario.
 */
function redirectUri(): string {
  return env('VITE_OIDC_REDIRECT_URI') || `${window.location.origin}/login`
}

export function rememberIntendedPath(path: string): void {
  if (path && !path.startsWith('/login')) sessionStorage.setItem(INTENDED_KEY, path)
}

export function takeIntendedPath(): string | null {
  const p = sessionStorage.getItem(INTENDED_KEY)
  sessionStorage.removeItem(INTENDED_KEY)
  return p
}

/**
 * Se inicializa SIEMPRE el cliente OIDC: reconstruir la sesion desde localStorage deja la
 * instancia sin inicializar, incapaz de refrescar, y el primer 401 expulsa al usuario.
 */
export async function initAuth(isPublicRoute: boolean): Promise<boolean> {
  if (initialised) return kc.authenticated ?? false
  initialised = true

  if (!isPublicRoute) rememberIntendedPath(window.location.pathname + window.location.search)

  const authenticated = await kc.init({
    onLoad: isPublicRoute ? 'check-sso' : 'login-required',
    pkceMethod: 'S256',
    checkLoginIframe: false,
    redirectUri: redirectUri(),
  })

  if (authenticated) startRefreshTimer()
  return authenticated
}

function startRefreshTimer() {
  window.clearInterval(refreshTimer)
  refreshTimer = window.setInterval(() => {
    kc.updateToken(70).catch(() => logout())
  }, 60_000)
}

/** Refresco compartido: N peticiones que reciben 401 a la vez esperan al mismo refresco. */
let inFlight: Promise<boolean> | null = null

export function refreshToken(): Promise<boolean> {
  if (!inFlight) {
    inFlight = kc
      .updateToken(-1)
      .then((renewed) => renewed)
      .finally(() => {
        inFlight = null
      })
  }
  return inFlight
}

export const getToken = (): string | undefined => kc.token
export const isAuthenticated = (): boolean => kc.authenticated ?? false
export const login = (intendedPath?: string): Promise<void> => {
  if (intendedPath) rememberIntendedPath(intendedPath)
  return kc.login({ redirectUri: redirectUri() }) as Promise<void>
}

export function logout(): void {
  window.clearInterval(refreshTimer)
  void kc.logout({ redirectUri: `${window.location.origin}/login` })
}

export function tokenClaims(): Record<string, unknown> {
  return (kc.tokenParsed ?? {}) as Record<string, unknown>
}
