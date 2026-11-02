import { beforeEach, describe, expect, it, vi } from 'vitest'

const http = vi.hoisted(() => ({ post: vi.fn(), patch: vi.fn() }))

vi.mock('@/api/http', () => ({ http }))

const { canUpdateEntity, renameEntity } = await import('./entities')

beforeEach(() => {
  http.post.mockReset()
  http.patch.mockReset().mockResolvedValue({ data: {} })
})

describe('renameEntity', () => {
  it('guarda el nombre como la propiedad `name` de la entidad', async () => {
    await renameEntity(453, 'Plaza Mayor')
    expect(http.patch).toHaveBeenCalledWith('/entities/453/properties', { name: 'Plaza Mayor' })
  })
})

describe('canUpdateEntity', () => {
  const ref = { urn: 'urn:ngsi-ld:Thing:P13_pred', tenant: 'demo', scope: '/' }

  it('pregunta al listado con el filtro de permiso de modificacion, en su espacio y ambito', async () => {
    http.post.mockResolvedValue({ data: { count: 1, rows: [] } })
    await expect(canUpdateEntity(ref)).resolves.toBe(true)
    expect(http.post).toHaveBeenCalledWith(
      '/entities/paginate',
      expect.objectContaining({ onlyCanUpdate: true, tenant: 'demo', scope: '/', paginationSize: 1 }),
    )
  })

  it('escapa los comodines del LIKE: `_` no debe casar con cualquier caracter', async () => {
    http.post.mockResolvedValue({ data: { count: 1, rows: [] } })
    await canUpdateEntity({ ...ref, urn: 'urn:ngsi-ld:Thing:100%_a\\b' })
    expect(http.post.mock.calls[0][1].urn).toBe('urn:ngsi-ld:Thing:100\\%\\_a\\\\b')
  })

  it('si la entidad no pasa el filtro, no se puede modificar', async () => {
    http.post.mockResolvedValue({ data: { count: 0, rows: [] } })
    await expect(canUpdateEntity(ref)).resolves.toBe(false)
  })
})
