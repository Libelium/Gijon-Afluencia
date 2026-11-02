import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import type { Entity } from '@/types'

const renameEntity = vi.hoisted(() => vi.fn())

vi.mock('../api/entities', () => ({ renameEntity }))

const { ApiError } = await import('@/api/http')
const { default: EntityRenameDialog } = await import('./EntityRenameDialog.vue')

const entity: Entity = {
  id: 453,
  name: 'Plaza Mayor (previsión)',
  urn: 'urn:ngsi-ld:Thing:P13_pred',
  datamodel: 'Thing',
  tenant: 'demo',
  scope: '/',
}

async function openDialog(target: Entity = entity) {
  const wrapper = mount(EntityRenameDialog, {
    props: { modelValue: false, entity: target },
    global: { plugins: [vuetify] },
    attachTo: document.body,
  })
  await wrapper.setProps({ modelValue: true })
  await flushPromises()
  return wrapper
}

const input = () => document.querySelector<HTMLInputElement>('.v-dialog input')!
const saveButton = () =>
  [...document.querySelectorAll<HTMLButtonElement>('.v-dialog button')].find((b) => b.textContent?.includes('Guardar'))!

async function type(value: string) {
  input().value = value
  input().dispatchEvent(new Event('input'))
  await flushPromises()
}

afterEach(() => {
  renameEntity.mockReset()
  document.body.innerHTML = ''
})

describe('EntityRenameDialog', () => {
  it('abre con el nombre actual y no deja guardar sin cambios', async () => {
    await openDialog()
    expect(input().value).toBe('Plaza Mayor (previsión)')
    expect(saveButton().disabled).toBe(true)
  })

  it('sin nombre propio parte del final del identificador, que es lo que se ve hoy', async () => {
    await openDialog({ ...entity, name: '' })
    expect(input().value).toBe('P13_pred')
  })

  it('no deja guardar un nombre en blanco', async () => {
    await openDialog()
    await type('   ')
    expect(saveButton().disabled).toBe(true)
  })

  it('guarda el nombre sin espacios sobrantes y avisa a la ficha', async () => {
    renameEntity.mockResolvedValue(undefined)
    const wrapper = await openDialog()
    await type('  Plaza Mayor  ')
    saveButton().click()
    await flushPromises()
    expect(renameEntity).toHaveBeenCalledWith(453, 'Plaza Mayor')
    expect(wrapper.emitted('saved')).toEqual([['Plaza Mayor']])
    expect(wrapper.emitted('update:modelValue')).toEqual([[false]])
  })

  it('sin permiso explica el motivo en castellano, no el mensaje del servidor', async () => {
    renameEntity.mockRejectedValue(new ApiError('forbidden', 'You are not allowed to update entities', 403))
    const wrapper = await openDialog()
    await type('Otro nombre')
    saveButton().click()
    await flushPromises()
    expect(document.querySelector('.v-dialog .v-alert')?.textContent).toContain(
      'No tienes permiso para cambiar el nombre de esta entidad.',
    )
    expect(wrapper.emitted('saved')).toBeUndefined()
  })
})
