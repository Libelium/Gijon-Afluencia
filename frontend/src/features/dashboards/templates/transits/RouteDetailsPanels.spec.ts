import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import type { RouteDetail } from './routeDetails'
import RouteDetailsPanels from './RouteDetailsPanels.vue'

const detail = (label: string, average: number | null, maximum: number | null, tourist: number | null = null): RouteDetail => ({
  key: label,
  label,
  averageMinutes: average,
  maximumMinutes: maximum,
  visitors: { tourist, resident: tourist === null ? null : 4, shortTerm: tourist === null ? null : 1 },
})

function mountPanels(details: RouteDetail[], withVisitors = true, error: string | null = null) {
  return mount(RouteDetailsPanels, {
    props: { details, withVisitors, error },
    global: { plugins: [vuetify], stubs: { BarChart: true } },
  })
}

describe('RouteDetailsPanels', () => {
  it('dibuja la duración media y la máxima de cada recorrido, en minutos', () => {
    const wrapper = mountPanels([detail('A → B', 12, 55, 30), detail('B → A', 8.5, 20, 3)])
    const chart = wrapper.findAllComponents({ name: 'BarChart' })[0]
    expect(chart.props('units')).toBe('min')
    expect(chart.props('categoryTitle')).toBe('Recorrido')
    expect(chart.props('series')).toEqual([
      { name: 'Duración media', units: 'min', points: [{ t: 'A → B', v: 12 }, { t: 'B → A', v: 8.5 }] },
      { name: 'Duración máxima', units: 'min', points: [{ t: 'A → B', v: 55 }, { t: 'B → A', v: 20 }] },
    ])
    expect(wrapper.text()).toContain('ninguna duración llega a 60 minutos')
  })

  it('reparte los tránsitos por tipo de visitante, apilados, solo en la avanzada', () => {
    const wrapper = mountPanels([detail('A → B', 12, 55, 30)])
    const visitors = wrapper.findAllComponents({ name: 'BarChart' })[1]
    expect(visitors.props('stacked')).toBe(true)
    expect(visitors.props('series').map((s: { name: string; points: { v: number }[] }) => [s.name, s.points[0].v])).toEqual([
      ['Turistas', 30],
      ['Residentes', 4],
      ['Corta estancia', 1],
    ])
    expect(mountPanels([detail('A → B', 12, 55, 30)], false).findAllComponents({ name: 'BarChart' })).toHaveLength(1)
  })

  it('dos recorridos con el mismo rótulo no se juntan en una barra', () => {
    const wrapper = mountPanels([detail('A → B', 1, 2), detail('A → B', 3, 4)], false)
    const points = wrapper.findComponent({ name: 'BarChart' }).props('series')[0].points
    expect(points.map((p: { t: string }) => p.t)).toEqual(['A → B', 'A → B (2)'])
  })

  it('sin duraciones ni tipos lo dice en cada panel', () => {
    const wrapper = mountPanels([detail('A → B', null, null)])
    expect(wrapper.text()).toContain('Los recorridos no publican su duración')
    expect(wrapper.text()).toContain('Los recorridos no publican el tipo de visitante')
    expect(wrapper.findAllComponents({ name: 'BarChart' })).toHaveLength(0)
  })

  it('si la carga ha fallado, enseña el error en lugar de las gráficas', () => {
    const wrapper = mountPanels([], true, 'No se ha podido contactar con el servidor.')
    expect(wrapper.text()).toContain('No se ha podido contactar con el servidor.')
  })
})
