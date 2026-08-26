import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { getToken, logout, refreshToken } from '@/auth/keycloak'
import { env } from '@/lib/env'

export type ApiErrorKind = 'network' | 'auth' | 'forbidden' | 'notFound' | 'validation' | 'server' | 'unknown'

/** Los fallos se propagan como excepcion. Devolver null haria indistinguible "sin datos" de "ha fallado". */
export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status?: number
  readonly details?: unknown

  constructor(kind: ApiErrorKind, message: string, status?: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.details = details
  }
}

const MESSAGES: Record<ApiErrorKind, string> = {
  network: 'No se ha podido contactar con el servidor. Revisa tu conexión.',
  auth: 'Tu sesión ha caducado. Vuelve a iniciar sesión.',
  forbidden: 'No tienes permiso para realizar esta acción.',
  notFound: 'No se ha encontrado el recurso solicitado.',
  validation: 'Los datos enviados no son válidos.',
  server: 'El servidor ha devuelto un error. Inténtalo de nuevo en unos minutos.',
  unknown: 'Se ha producido un error inesperado.',
}

export const errorMessage = (e: unknown): string =>
  e instanceof ApiError ? (e.message || MESSAGES[e.kind]) : MESSAGES.unknown

function classify(status?: number): ApiErrorKind {
  if (!status) return 'network'
  if (status === 401) return 'auth'
  if (status === 403) return 'forbidden'
  if (status === 404) return 'notFound'
  if (status === 422 || status === 400) return 'validation'
  if (status >= 500) return 'server'
  return 'unknown'
}

function serverMessage(data: unknown): string | undefined {
  if (data && typeof data === 'object') {
    const d = data as Record<string, unknown>
    if (typeof d.message === 'string' && d.message) return d.message
    if (typeof d.error === 'string' && d.error) return d.error
  }
  return undefined
}

export const http = axios.create({
  baseURL: `${env('VITE_API_BASE_URL')}/api/V1`,
  timeout: 60_000,
})

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

type Retriable = AxiosRequestConfig & { _retried?: boolean }

http.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const status = error.response?.status
    const config = error.config as Retriable | undefined

    // Un unico reintento tras refrescar: si el refresco no basta, la sesion se cierra.
    if (status === 401 && config && !config._retried) {
      config._retried = true
      try {
        await refreshToken()
        return http.request(config)
      } catch {
        logout()
      }
    }

    const kind = classify(status)
    if (kind === 'auth') logout()

    throw new ApiError(
      kind,
      serverMessage(error.response?.data) ?? MESSAGES[kind],
      status,
      error.response?.data,
    )
  },
)
