import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import vuetify from '@/plugins/vuetify'
import { useUiStore } from '@/stores/ui'
import ZoneMapCard, { type ZoneMarker } from './ZoneMapCard.vue'

/**
 * El mapa de Leaflet no se puede pintar en jsdom, y vue-leaflet carga Leaflet por su cuenta (con
 * sus iconos) aunque los componentes esten sustituidos. Se reemplaza el modulo entero: lo que se
 * prueba es la lista de zonas, que es la alternativa textual del mapa, y el contenedor.
 */
vi.mock('@vue-leaflet/vue-leaflet', () => {
  const slot = { template: '<div><slot /></div>' }
  return { LMap: slot, LTileLayer: slot, LPolygon: slot, LCircleMarker: slot, LTooltip: slot }
})

const marker = (over: Partial<ZoneMarker>): ZoneMarker => ({
  id: 1,
  name: 'Paseo',
  value: 45,
  ratio: 0.5,
  latLng: [43.54, -5.66],
  polygon: null,
  selected: false,
  ...over,
})

function mountCard(markers: ZoneMarker[], theme: 'light' | 'dark' = 'light') {
  const pinia = createPinia()
  setActivePinia(pinia)
  useUiStore().theme = theme
  return mount(ZoneMapCard, { props: { markers }, global: { plugins: [pinia, vuetify] } })
}

describe('ZoneMapCard', () => {
  it('con aforo rotula personas y porcentaje', () => {
    const text = mountCard([marker({})]).text()
    expect(text).toContain('45')
    expect(text).toContain('%')
  })

  it('con la escala relativa a la zona mas llena no rotula ningun porcentaje', () => {
    const text = mountCard([marker({ ratio: 1, relative: true })]).text()
    expect(text).toContain('45')
    expect(text).not.toContain('%')
  })

  it('en tema oscuro aplica el mismo filtro de teselas que el resto de mapas', () => {
    expect(mountCard([marker({})], 'dark').find('.map-tiles--dark').exists()).toBe(true)
    expect(mountCard([marker({})], 'light').find('.map-tiles--dark').exists()).toBe(false)
  })
})
