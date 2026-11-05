import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import vuetify from '@/plugins/vuetify'
import type { Entity } from '@/types'

const listEntities = vi.hoisted(() => vi.fn())

vi.mock('../api/entities', () => ({
  listEntities,
  listDatamodels: vi.fn().mockResolvedValue([]),
  getLastDataTimes: vi.fn().mockResolvedValue({}),
}))

vi.mock('@/api/scopes', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/scopes')>()),
  listDataScopes: vi.fn().mockResolvedValue([]),
}))

const { default: EntitiesListView } = await import('./EntitiesListView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
})

const entity = (id: number, scope: string): Entity => ({
  id,
  name: `E${id}`,
  urn: `urn:ngsi-ld:Thing:E${id}`,
  datamodel: 'Thing',
  tenant: 'demo',
  scope,
})

async function mountList(rows: Entity[]) {
  listEntities.mockResolvedValue({ count: rows.length, rows })
  const wrapper = mount(EntitiesListView, { global: { plugins: [createPinia(), vuetify, router] } })
  await flushPromises()
  return wrapper
}

async function columnsFor(rows: Entity[]): Promise<string[]> {
  return (await mountList(rows)).findAll('th').map((th) => th.text())
}

afterEach(() => listEntities.mockReset())

describe('columna de ambito del listado de entidades', () => {
  it('no sale si todas las entidades estan en el ambito raiz', async () => {
    const columns = await columnsFor([entity(1, '/'), entity(2, '/')])
    expect(columns).toContain('Espacio de datos')
    expect(columns).not.toContain('Ámbito')
  })

  it('sale en cuanto una entidad esta en un ambito con nombre', async () => {
    const columns = await columnsFor([entity(1, '/'), entity(2, '/norte')])
    expect(columns).toContain('Ámbito')
  })
})

describe('orden del listado de entidades', () => {
  const header = (wrapper: Awaited<ReturnType<typeof mountList>>, title: string) =>
    wrapper.findAll('th').find((th) => th.text() === title)!

  const lastQuery = () => listEntities.mock.calls.at(-1)![0]

  it('sin pulsar nada no pide orden: el servidor usa el suyo', async () => {
    await mountList([entity(1, '/')])
    expect(lastQuery().orderBy).toBeUndefined()
  })

  it('pulsar una cabecera ordena por su columna, primero ascendente y luego descendente', async () => {
    const wrapper = await mountList([entity(1, '/')])

    await header(wrapper, 'Modelo de datos').trigger('click')
    await flushPromises()
    expect(lastQuery()).toMatchObject({ orderBy: 'datamodel', orderDirection: 'asc', page: 1 })

    await header(wrapper, 'Modelo de datos').trigger('click')
    await flushPromises()
    expect(lastQuery()).toMatchObject({ orderBy: 'datamodel', orderDirection: 'desc' })
  })

  it('el espacio de datos tambien se ordena', async () => {
    const wrapper = await mountList([entity(1, '/')])
    await header(wrapper, 'Espacio de datos').trigger('click')
    await flushPromises()
    expect(lastQuery()).toMatchObject({ orderBy: 'tenant', orderDirection: 'asc' })
  })

  it('el nombre se ordena en el servidor, que lo lee de la base de datos de tiempo real', async () => {
    const wrapper = await mountList([entity(1, '/')])
    await header(wrapper, 'Entidad').trigger('click')
    await flushPromises()
    expect(lastQuery()).toMatchObject({ orderBy: 'name', orderDirection: 'asc', page: 1 })
  })

  it('el ultimo dato se ordena con la clave que entiende el servidor, mas reciente primero al repetir', async () => {
    const wrapper = await mountList([entity(1, '/')])
    await header(wrapper, 'Último dato').trigger('click')
    await flushPromises()
    expect(lastQuery()).toMatchObject({ orderBy: 'last_data', orderDirection: 'asc' })

    await header(wrapper, 'Último dato').trigger('click')
    await flushPromises()
    expect(lastQuery()).toMatchObject({ orderBy: 'last_data', orderDirection: 'desc' })
  })
})
