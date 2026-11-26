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
  setMaxCapacity: vi.fn(),
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

async function mountDetail(canUpdate: boolean | Error, target: Entity = entity, measures: unknown[] = []) {
  api.getEntity.mockResolvedValue({ ...target })
  api.getEntityMeasures.mockResolvedValue(measures)
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

describe('aforo maximo desde la ficha de una zona', () => {
  const zone: Entity = { ...entity, name: 'Plaza de la Colegiata', urn: 'urn:ngsi-ld:CrowdFlowZone:P07', datamodel: 'CrowdFlowZone' }
  const capacityButton = (wrapper: Awaited<ReturnType<typeof mountDetail>>) =>
    wrapper.findAll('button').find((b) => b.text().includes('Aforo máximo'))

  it('una zona que se puede modificar ofrece editar su aforo', async () => {
    expect(capacityButton(await mountDetail(true, zone))).toBeDefined()
    expect(capacityButton(await mountDetail(true, { ...zone, datamodel: 'CrowdFlowLidarZone' }))).toBeDefined()
  })

  it('otra entidad, o quien no puede modificarla, no lo ve', async () => {
    expect(capacityButton(await mountDetail(true))).toBeUndefined()
    expect(capacityButton(await mountDetail(false, zone))).toBeUndefined()
  })

  it('el dialogo parte del aforo que ya tiene la zona', async () => {
    const wrapper = await mountDetail(true, zone, [{ id: 'maxCapacity', name: 'maxCapacity', value: 220 }])
    await capacityButton(wrapper)!.trigger('click')
    await flushPromises()
    expect(document.querySelector<HTMLInputElement>('.v-dialog input')!.value).toBe('220')
  })
})
