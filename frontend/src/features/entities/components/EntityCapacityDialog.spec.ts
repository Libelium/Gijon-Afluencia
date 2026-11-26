import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import type { Entity } from '@/types'

const setMaxCapacity = vi.hoisted(() => vi.fn())

vi.mock('../api/entities', () => ({ setMaxCapacity }))

const { ApiError } = await import('@/api/http')
const { default: EntityCapacityDialog } = await import('./EntityCapacityDialog.vue')

const zone: Entity = {
  id: 25,
  name: 'Plaza de la Colegiata',
  urn: 'urn:ngsi-ld:CrowdFlowZone:P07',
  datamodel: 'CrowdFlowZone',
  tenant: 'pid_gijon',
  scope: '/',
}

async function openDialog(current: number | null = null) {
  const wrapper = mount(EntityCapacityDialog, {
    props: { modelValue: false, entity: zone, current },
    global: { plugins: [vuetify] },
    attachTo: document.body,
  })
  await wrapper.setProps({ modelValue: true })
  await flushPromises()
  return wrapper
}

const input = () => document.querySelector<HTMLInputElement>('.v-dialog input')!
const button = (label: string) =>
  [...document.querySelectorAll<HTMLButtonElement>('.v-dialog button')].find((b) => b.textContent?.includes(label))

async function type(value: string) {
  input().value = value
  input().dispatchEvent(new Event('input'))
  await flushPromises()
}

afterEach(() => {
  setMaxCapacity.mockReset()
  document.body.innerHTML = ''
})

describe('EntityCapacityDialog', () => {
  it('sin aforo parte vacio, sin opcion de quitarlo, y no deja guardar hasta escribir uno', async () => {
    await openDialog()
    expect(input().value).toBe('')
    expect(button('Quitar el aforo')).toBeUndefined()
    expect(button('Guardar')!.disabled).toBe(true)
  })

  it('solo admite un numero entero de personas mayor que cero', async () => {
    await openDialog()
    for (const value of ['0', '-5', '12,5', 'mucho']) {
      await type(value)
      expect(button('Guardar')!.disabled).toBe(true)
    }
    await type('220')
    expect(button('Guardar')!.disabled).toBe(false)
  })

  it('guarda el aforo y avisa con el valor nuevo', async () => {
    setMaxCapacity.mockResolvedValue(undefined)
    const wrapper = await openDialog(180)
    await type('220')
    button('Guardar')!.click()
    await flushPromises()
    expect(setMaxCapacity).toHaveBeenCalledWith(25, 220)
    expect(wrapper.emitted('saved')).toEqual([[220]])
  })

  it('con aforo, se puede quitar', async () => {
    setMaxCapacity.mockResolvedValue(undefined)
    const wrapper = await openDialog(180)
    button('Quitar el aforo')!.click()
    await flushPromises()
    expect(setMaxCapacity).toHaveBeenCalledWith(25, null)
    expect(wrapper.emitted('saved')).toEqual([[null]])
  })

  it('sin permiso lo explica en castellano', async () => {
    setMaxCapacity.mockRejectedValue(new ApiError('forbidden', 'You are not allowed to update entities', 403))
    await openDialog()
    await type('220')
    button('Guardar')!.click()
    await flushPromises()
    expect(document.querySelector('.v-dialog .v-alert')?.textContent).toContain('No tienes permiso')
  })
})
