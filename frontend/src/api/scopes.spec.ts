import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const get = vi.fn()

vi.mock('@/api/http', () => ({ http: { get } }))

describe('listDataScopes', () => {
  beforeEach(() => {
    get.mockReset()
    // El modulo memoriza la peticion en una variable de modulo: hay que recargarlo entre casos.
    vi.resetModules()
  })

  afterEach(() => vi.restoreAllMocks())

  const load = async () => (await import('./scopes')).listDataScopes()

  it('acepta la respuesta con el array en la raiz', async () => {
    get.mockResolvedValue({ data: [{ id: 1, name: '/', tenant: { name: 'gijon' } }] })
    await expect(load()).resolves.toEqual([{ id: '1', tenant: 'gijon', scope: '/' }])
  })

  it('acepta tambien la respuesta envuelta en {rows}, que es la del resto de listados', async () => {
    get.mockResolvedValue({ data: { rows: [{ id: 2, name: '/norte', tenant: { name: 'gijon' } }] } })
    await expect(load()).resolves.toEqual([{ id: '2', tenant: 'gijon', scope: '/norte' }])
  })

  it('devuelve lista vacia ante una forma inesperada, en lugar de romper la vista', async () => {
    get.mockResolvedValue({ data: { total: 0 } })
    await expect(load()).resolves.toEqual([])
  })

  it('descarta las filas sin espacio de datos o sin ambito', async () => {
    // El servidor rechaza un ambito sin su espacio de datos con un 400: ofrecerlo en el
    // desplegable seria ofrecer una combinacion que no se puede usar.
    get.mockResolvedValue({
      data: [
        { id: 1, name: '/', tenant: { name: 'gijon' } },
        { id: 2, name: '/sur', tenant: null },
        { id: 3, name: '', tenant: { name: 'gijon' } },
        { name: '/sin-id', tenant: { name: 'gijon' } },
      ],
    })
    const scopes = await load()
    expect(scopes.map((s) => s.id)).toEqual(['1'])
  })

  it('ordena por espacio de datos y luego por ambito, con las reglas del castellano', async () => {
    get.mockResolvedValue({
      data: [
        { id: 1, name: '/zona', tenant: { name: 'gijon' } },
        { id: 2, name: '/ambito', tenant: { name: 'gijon' } },
        { id: 3, name: '/', tenant: { name: 'avilas' } },
      ],
    })
    const scopes = await load()
    expect(scopes.map((s) => `${s.tenant}${s.scope}`)).toEqual([
      'avilas/',
      'gijon/ambito',
      'gijon/zona',
    ])
  })

  it('memoriza la respuesta: dos llamadas seguidas no piden dos veces el catalogo', async () => {
    get.mockResolvedValue({ data: [] })
    const { listDataScopes } = await import('./scopes')
    await Promise.all([listDataScopes(), listDataScopes()])
    expect(get).toHaveBeenCalledTimes(1)
  })

  it('un fallo descarta la memorizacion: el siguiente intento vuelve a preguntar', async () => {
    const { listDataScopes } = await import('./scopes')
    get.mockRejectedValueOnce(new Error('caida'))
    await expect(listDataScopes()).rejects.toThrow('caida')

    get.mockResolvedValue({ data: [{ id: 9, name: '/', tenant: { name: 'gijon' } }] })
    await expect(listDataScopes()).resolves.toHaveLength(1)
    expect(get).toHaveBeenCalledTimes(2)
  })
})

describe('dataScopeLabel', () => {
  it('el ambito raiz no aporta nada: se rotula solo con el espacio de datos', async () => {
    const { dataScopeLabel } = await import('./scopes')
    expect(dataScopeLabel({ id: '1', tenant: 'gijon', scope: '/' })).toBe('gijon')
  })

  it('un ambito con nombre va detras del espacio de datos', async () => {
    const { dataScopeLabel } = await import('./scopes')
    expect(dataScopeLabel({ id: '1', tenant: 'gijon', scope: '/norte' })).toBe('gijon · /norte')
  })
})
