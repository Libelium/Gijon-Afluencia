import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import vuetify from '@/plugins/vuetify'
import type { Entity } from '@/types'

const api = vi.hoisted(() => ({
  getEntity: vi.fn(),
  getEntityMeasures: vi.fn(),
  canUpdateEntity: vi.fn(),
  renameEntity: vi.fn(),
  latestTimestamp: () => null,
}))

vi.mock('../api/entities', () => api)

const { default: EntityDetailView } = await import('./EntityDetailView.vue')

const entity: Entity = {
  id: 453,
  name: 'Plaza Mayor (previsión)',
  urn: 'urn:ngsi-ld:Thing:P13_pred',
  datamodel: 'Thing',
  tenant: 'demo',
  scope: '/',
}

async function mountDetail(canUpdate: boolean | Error) {
  api.getEntity.mockResolvedValue({ ...entity })
  api.getEntityMeasures.mockResolvedValue([])
  if (canUpdate instanceof Error) api.canUpdateEntity.mockRejectedValue(canUpdate)
  else api.canUpdateEntity.mockResolvedValue(canUpdate)
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/entidades', component: { template: '<div />' } },
      { path: '/entidades/:id', component: EntityDetailView },
    ],
  })
  await router.push('/entidades/453')
  const wrapper = mount(EntityDetailView, {
    global: { plugins: [createPinia(), vuetify, router] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

const renameButton = (wrapper: Awaited<ReturnType<typeof mountDetail>>) =>
  wrapper.findAll('button').find((b) => b.text().includes('Renombrar'))

afterEach(() => {
  vi.clearAllMocks()
  document.body.innerHTML = ''
})

describe('renombrar desde la ficha de entidad', () => {
  it('quien puede modificar la entidad ve el boton', async () => {
    const wrapper = await mountDetail(true)
    expect(api.canUpdateEntity).toHaveBeenCalledWith({ urn: entity.urn, tenant: 'demo', scope: '/' })
    expect(renameButton(wrapper)).toBeDefined()
  })

  it('quien no puede, no lo ve', async () => {
    const wrapper = await mountDetail(false)
    expect(renameButton(wrapper)).toBeUndefined()
  })

  it('si no se puede saber, tampoco se ofrece', async () => {
    const wrapper = await mountDetail(new Error('caida'))
    expect(renameButton(wrapper)).toBeUndefined()
  })

  it('al guardar, el titulo pasa a ser el nombre nuevo', async () => {
    api.renameEntity.mockResolvedValue(undefined)
    const wrapper = await mountDetail(true)
    await renameButton(wrapper)!.trigger('click')
    await flushPromises()
    const input = document.querySelector<HTMLInputElement>('.v-dialog input')!
    input.value = 'Plaza Mayor'
    input.dispatchEvent(new Event('input'))
    await flushPromises()
    ;[...document.querySelectorAll<HTMLButtonElement>('.v-dialog button')].find((b) => b.textContent?.includes('Guardar'))!.click()
    await flushPromises()
    expect(api.renameEntity).toHaveBeenCalledWith(453, 'Plaza Mayor')
    expect(wrapper.find('h1').text()).toBe('Plaza Mayor')
  })
})
