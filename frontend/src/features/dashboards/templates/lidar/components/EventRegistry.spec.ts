import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import { ApiError } from '@/api/http'
import type { RegistryEvent } from '../predictionEvents'

const listRegistry = vi.hoisted(() => vi.fn())
const registerEvent = vi.hoisted(() => vi.fn())
const deleteRegistryEvent = vi.hoisted(() => vi.fn())

vi.mock('../predictionEvents', async (original) => ({
  ...(await original<typeof import('../predictionEvents')>()),
  listRegistry,
  registerEvent,
  deleteRegistryEvent,
}))

const { default: EventRegistry } = await import('./EventRegistry.vue')

const ZONE = 'urn:ngsi-ld:Zone:plaza'
const OTHER = 'urn:ngsi-ld:Zone:muelle'
const target = { tenant: 'demo', scope: '/' }

const event = (over: Partial<RegistryEvent> = {}): RegistryEvent => ({
  id: '0:abc',
  date: '2027-12-14',
  end_date: '2027-12-20',
  event_type: 'market',
  device_ids: [ZONE],
  notes: 'Navidad',
  start_hour: 10,
  end_hour: 21,
  ...over,
})

function mountRegistry() {
  return mount(EventRegistry, {
    props: { target, zoneUrn: ZONE, zoneName: 'Plaza', timeZone: 'Europe/Madrid' },
    global: { plugins: [vuetify] },
    attachTo: document.body,
  })
}

const buttonIn = (root: ParentNode, label: string) =>
  [...root.querySelectorAll('button')].find((b) => b.textContent?.includes(label)) as HTMLButtonElement | undefined

afterEach(() => {
  listRegistry.mockReset()
  registerEvent.mockReset()
  deleteRegistryEvent.mockReset()
  document.body.innerHTML = ''
})

describe('EventRegistry', () => {
  it('enseña los eventos de la zona y los de todas, no los de otras zonas', async () => {
    listRegistry.mockResolvedValue({
      rows: [
        event(),
        event({ id: '1:def', date: '2027-12-31', end_date: '2027-12-31', event_type: 'concert', device_ids: [], notes: '' }),
        event({ id: '2:ghi', device_ids: [OTHER], notes: 'Solo en el muelle' }),
      ],
      canEdit: false,
    })
    const wrapper = mountRegistry()
    await flushPromises()

    expect(listRegistry).toHaveBeenCalledWith(target)
    const rows = wrapper.findAll('tbody tr').map((tr) => tr.text())
    expect(rows).toHaveLength(2)
    expect(rows[0]).toContain('14/12/2027 – 20/12/2027')
    expect(rows[0]).toContain('Mercado o feria')
    expect(rows[0]).toContain('10:00 – 21:00')
    expect(rows[0]).toContain('Esta zona')
    expect(rows[1]).toContain('31/12/2027')
    expect(rows[1]).toContain('Todas las zonas')
    expect(wrapper.text()).not.toContain('Solo en el muelle')
    // Quien solo puede leer no ve ni el alta ni el borrado.
    expect(buttonIn(document.body, 'Registrar un evento')).toBeUndefined()
    expect(wrapper.find('tbody button').exists()).toBe(false)
    expect(wrapper.emitted('loaded')![0]).toEqual([{ rows: expect.any(Array), canEdit: false }])
  })

  it('sin permiso de lectura no enseña nada y avisa con null', async () => {
    listRegistry.mockRejectedValue(new ApiError('forbidden', 'Forbidden', 403))
    const wrapper = mountRegistry()
    await flushPromises()
    expect(wrapper.find('section').exists()).toBe(false)
    expect(wrapper.emitted('loaded')![0]).toEqual([null])
  })

  it('registra un evento nuevo con el formulario y vuelve a cargar', async () => {
    listRegistry.mockResolvedValue({ rows: [], canEdit: true })
    registerEvent.mockResolvedValue(event())
    const wrapper = mountRegistry()
    await flushPromises()
    expect(wrapper.text()).toContain('No hay eventos registrados para esta zona')

    buttonIn(document.body, 'Registrar un evento')!.click()
    await flushPromises()
    const dialog = document.querySelector('.v-overlay__content')!
    expect(dialog.textContent).toContain('Registrar un evento')
    buttonIn(dialog, 'Registrar')!.click()
    await flushPromises()

    const [sent, body] = registerEvent.mock.calls[0]
    expect(sent).toEqual(target)
    expect(body).toMatchObject({ event_type: 'market', device_ids: [ZONE], start_hour: 10, end_hour: 21 })
    expect(listRegistry).toHaveBeenCalledTimes(2)
    expect(wrapper.emitted('registered')).toHaveLength(1)
  })

  it('avisa de que un evento de hoy o antes obliga a reentrenar', async () => {
    listRegistry.mockResolvedValue({ rows: [], canEdit: true })
    mountRegistry()
    await flushPromises()
    buttonIn(document.body, 'Registrar un evento')!.click()
    await flushPromises()
    // El formulario vacío propone hoy.
    expect(document.querySelector('.v-overlay__content')!.textContent).toContain('lo reentrenará entero')
  })

  it('borra un evento después de confirmarlo', async () => {
    listRegistry.mockResolvedValue({ rows: [event()], canEdit: true })
    deleteRegistryEvent.mockResolvedValue(undefined)
    const wrapper = mountRegistry()
    await flushPromises()

    await wrapper.find('tbody button').trigger('click')
    await flushPromises()
    buttonIn(document.querySelector('.v-overlay__content')!, 'Borrar')!.click()
    await flushPromises()

    expect(deleteRegistryEvent).toHaveBeenCalledWith(target, '0:abc')
    expect(listRegistry).toHaveBeenCalledTimes(2)
  })

  it('si alguien lo cambió entretanto, no borra, vuelve a cargar y lo dice', async () => {
    listRegistry.mockResolvedValue({ rows: [event()], canEdit: true })
    deleteRegistryEvent.mockRejectedValue(new ApiError('unknown', 'Conflict', 409))
    const wrapper = mountRegistry()
    await flushPromises()

    await wrapper.find('tbody button').trigger('click')
    await flushPromises()
    buttonIn(document.querySelector('.v-overlay__content')!, 'Borrar')!.click()
    await flushPromises()

    expect(listRegistry).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('El registro había cambiado')
  })
})
