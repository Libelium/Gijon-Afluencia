import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import type { Entity } from '@/types'
import type { PlacedEntity } from '../lib/geometry'
import MapFilters from './MapFilters.vue'

const placed = (id: number, name: string): PlacedEntity => ({
  entity: { id, name, urn: `urn:ngsi-ld:Thing:Z${id}`, datamodel: 'Thing' } as Entity,
  latLng: [43.54, -5.66],
})

function mountFilters(props: Record<string, unknown> = {}) {
  return mount(MapFilters, {
    props: { datamodels: [], withoutLocation: 0, search: '', ...props },
    global: { plugins: [vuetify] },
    attachTo: document.body,
  })
}

const input = () => document.querySelector<HTMLInputElement>('input')!
const items = () => [...document.querySelectorAll<HTMLElement>('.map-suggestions .v-list-item')]

async function type(wrapper: ReturnType<typeof mountFilters>, value: string) {
  input().value = value
  input().dispatchEvent(new Event('input'))
  await wrapper.setProps({ search: value })
  await flushPromises()
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('MapFilters, sugerencias del buscador', () => {
  it('al escribir enseña las entidades que coinciden, con su nombre y su modelo de datos', async () => {
    const wrapper = mountFilters({ suggestions: [placed(1, 'Plaza Mayor'), placed(2, 'Plaza de la Corrada')] })
    await type(wrapper, 'plaza')
    expect(items().map((el) => el.textContent?.trim())).toEqual(['Plaza MayorThing', 'Plaza de la CorradaThing'])
  })

  it('sin nombre, la sugerencia lleva el final del identificador', async () => {
    const wrapper = mountFilters({ suggestions: [placed(7, '')] })
    await type(wrapper, 'z7')
    expect(items()[0].textContent).toContain('Z7')
  })

  it('con una sola letra no abre el desplegable', async () => {
    const wrapper = mountFilters({ suggestions: [placed(1, 'Plaza Mayor')] })
    await type(wrapper, 'p')
    expect(items()).toHaveLength(0)
  })

  it('mientras busca lo dice, y si no hay coincidencias con ubicación también', async () => {
    const wrapper = mountFilters({ suggestions: [], suggestionsLoading: true })
    await type(wrapper, 'plaza')
    expect(items()[0].textContent).toContain('Buscando coincidencias')
    await wrapper.setProps({ suggestionsLoading: false })
    expect(items()[0].textContent).toContain('Ninguna entidad con ubicación')
    expect(items()[0].classList).toContain('v-list-item--disabled')
  })

  it('al elegir una entidad la entrega, cierra el desplegable y no cambia el texto del filtro', async () => {
    const target = placed(2, 'Plaza de la Corrada')
    const wrapper = mountFilters({ suggestions: [placed(1, 'Plaza Mayor'), target] })
    await type(wrapper, 'plaza')
    items()[1].click()
    await flushPromises()
    expect(wrapper.emitted('pick')).toEqual([[target]])
    expect(wrapper.emitted('update:search')?.at(-1)).toEqual(['plaza'])
    expect(document.querySelector('.map-suggestions')?.closest('.v-overlay--active')).toBeNull()
  })

  it('al vaciar el buscador se cierra el desplegable', async () => {
    const wrapper = mountFilters({ suggestions: [placed(1, 'Plaza Mayor')] })
    await type(wrapper, 'plaza')
    expect(items()).toHaveLength(1)
    await type(wrapper, '')
    expect(document.querySelector('.map-suggestions')?.closest('.v-overlay--active')).toBeNull()
  })
})
