import { beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * `http.ts` construye el cliente OIDC al evaluarse su modulo, asi que la sesion se sustituye
 * antes de importarlo: lo que se prueba aqui es la POLITICA DE ERRORES —la traduccion de un
 * codigo HTTP a algo que un usuario pueda leer y a lo que la interfaz pueda reaccionar—, no la
 * autenticacion.
 */
const logout = vi.fn()
const refreshToken = vi.fn()

vi.mock('@/auth/keycloak', () => ({
  getToken: () => 'token-de-prueba',
  logout,
  refreshToken,
}))

const { ApiError, errorMessage } = await import('./http')

beforeEach(() => {
  logout.mockReset()
  refreshToken.mockReset()
})

describe('ApiError', () => {
  it('conserva la clase, el codigo y el cuerpo para que la vista pueda decidir', () => {
    const error = new ApiError('forbidden', 'Sin permiso', 403, { detail: 'x' })
    expect(error).toBeInstanceOf(Error)
    expect(error.name).toBe('ApiError')
    expect(error.kind).toBe('forbidden')
    expect(error.status).toBe(403)
    expect(error.details).toEqual({ detail: 'x' })
  })
})

describe('errorMessage', () => {
  it('prefiere el mensaje del servidor cuando lo hay', () => {
    expect(errorMessage(new ApiError('validation', 'El nombre ya existe', 422))).toBe(
      'El nombre ya existe',
    )
  })

  it('cae al mensaje propio de la clase de error si el servidor no dice nada', () => {
    expect(errorMessage(new ApiError('network', ''))).toContain('No se ha podido contactar')
    expect(errorMessage(new ApiError('auth', ''))).toContain('sesión ha caducado')
    expect(errorMessage(new ApiError('forbidden', ''))).toContain('permiso')
    expect(errorMessage(new ApiError('notFound', ''))).toContain('No se ha encontrado')
    expect(errorMessage(new ApiError('server', ''))).toContain('servidor')
  })

  it('nunca deja escapar un error ajeno sin traducir a la interfaz', () => {
    // Un `TypeError` de la propia aplicacion no puede acabar pintado tal cual en pantalla.
    expect(errorMessage(new TypeError('undefined is not a function'))).toBe(
      'Se ha producido un error inesperado.',
    )
    expect(errorMessage(null)).toBe('Se ha producido un error inesperado.')
    expect(errorMessage('cadena suelta')).toBe('Se ha producido un error inesperado.')
  })
})
