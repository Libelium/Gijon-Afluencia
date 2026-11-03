import { beforeEach, describe, expect, it, vi } from 'vitest'

const post = vi.hoisted(() => vi.fn())

vi.mock('@/api/http', () => ({ http: { post } }))

const { listEntities } = await import('./entities')

describe('listEntities', () => {
  beforeEach(() => post.mockReset().mockResolvedValue({ data: { count: 0, rows: [] } }))

  const body = () => post.mock.calls[0][1]

  it('sin orden no manda los parametros de orden', async () => {
    await listEntities({ page: 1, paginationSize: 25 })
    expect(body()).not.toHaveProperty('orderBy')
    expect(body()).not.toHaveProperty('orderDirection')
  })

  it('manda la columna y el sentido como texto, que es lo que lee el servidor', async () => {
    await listEntities({ page: 1, paginationSize: 25, orderBy: 'datamodel', orderDirection: 'desc' })
    expect(body()).toMatchObject({ orderBy: 'datamodel', orderDirection: 'desc' })
  })

  it('una columna sin sentido se ordena ascendente', async () => {
    await listEntities({ page: 1, paginationSize: 25, orderBy: 'tenant' })
    expect(body()).toMatchObject({ orderBy: 'tenant', orderDirection: 'asc' })
  })
})
