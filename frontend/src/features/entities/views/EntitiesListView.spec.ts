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

async function columnsFor(rows: Entity[]): Promise<string[]> {
  listEntities.mockResolvedValue({ count: rows.length, rows })
  const wrapper = mount(EntitiesListView, { global: { plugins: [createPinia(), vuetify, router] } })
  await flushPromises()
  return wrapper.findAll('th').map((th) => th.text())
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
