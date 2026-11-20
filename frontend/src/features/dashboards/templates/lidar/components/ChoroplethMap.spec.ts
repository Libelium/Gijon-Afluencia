import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import vuetify from '@/plugins/vuetify'
import type { ZoneState } from '../choropleth'
import ChoroplethMap from './ChoroplethMap.vue'

// Leaflet no se pinta en jsdom: se prueba la lista de zonas, que es la alternativa del mapa.
vi.mock('@vue-leaflet/vue-leaflet', () => {
  const slot = { template: '<div><slot /></div>' }
  return { LMap: slot, LTileLayer: slot, LPolygon: slot, LCircleMarker: slot, LTooltip: slot }
})

const square: [number, number][] = [
  [43.54, -5.66],
  [43.54, -5.65],
  [43.55, -5.65],
]

const zone = (over: Partial<ZoneState>): ZoneState => ({
  id: 1,
  name: 'Paseo',
  polygon: square,
  value: 45,
  capacity: 100,
  ratio: 0.45,
  ...over,
})

function mountMap(zones: ZoneState[], selectedId: number | null = null) {
  setActivePinia(createPinia())
  return mount(ChoroplethMap, { props: { zones, selectedId }, global: { plugins: [createPinia(), vuetify] } })
}

describe('ChoroplethMap', () => {
  it('cada zona dice su ocupacion en personas y en porcentaje del aforo', () => {
    const text = mountMap([zone({}), zone({ id: 2, name: 'Playa', ratio: null, capacity: null })]).text()
    expect(text).toMatch(/Paseo\s*45 personas · 45 %/)
    expect(text).toMatch(/Playa\s*45 personas/)
    expect(text).not.toMatch(/Playa\s*45 personas ·/)
  })

  it('las zonas sin poligono siguen en la lista, avisando de que no se pintan', () => {
    expect(mountMap([zone({ polygon: null })]).text()).toContain('sin polígono')
  })

  it('la leyenda es la escala continua del calor, con el aviso de las zonas sin aforo', () => {
    const wrapper = mountMap([zone({})])
    const text = wrapper.text()
    expect(text).toContain('100 % del aforo o más')
    expect(text).toContain('Sin aforo: no se colorea')
    // Ya no hay modo por tramos que elegir.
    expect(wrapper.findAll('button').some((button) => button.text() === 'Zonas')).toBe(false)
  })

  it('elegir una zona en la lista la selecciona', async () => {
    const wrapper = mountMap([zone({}), zone({ id: 2, name: 'Playa' })], 1)
    const buttons = wrapper.findAll('button[aria-pressed]')
    expect(buttons[0].attributes('aria-pressed')).toBe('true')
    await buttons[1].trigger('click')
    expect(wrapper.emitted('select')).toEqual([[2]])
  })
})

describe('ChoroplethMap, dispositivos', () => {
  const device = { key: 'd1', kind: 'lidar' as const, serial: 'L1', zoneId: 1, zoneName: 'Paseo', lat: 43.545, lon: -5.655 }

  it('el interruptor oculta los dispositivos y su leyenda, y lo recuerda', async () => {
    localStorage.removeItem('choropleth.showDevices')
    const wrapper = mountMap([zone({})])
    await wrapper.setProps({ devices: [device] })
    expect(wrapper.findAll('.choropleth__device')).toHaveLength(1)

    await wrapper.find('input[type="checkbox"]').setValue(false)
    expect(wrapper.findAll('.choropleth__device')).toHaveLength(0)
    expect(localStorage.getItem('choropleth.showDevices')).toBe('false')
    localStorage.removeItem('choropleth.showDevices')
  })

  it('sin dispositivos no hay interruptor', () => {
    expect(mountMap([zone({})]).find('input[type="checkbox"]').exists()).toBe(false)
  })
})
