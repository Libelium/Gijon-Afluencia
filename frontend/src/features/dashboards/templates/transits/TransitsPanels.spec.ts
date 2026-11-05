import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import vuetify from '@/plugins/vuetify'
import type { FlowNode, FlowPair } from './pairs'
import type { Route } from './useTransits'
import TransitsPanels from './TransitsPanels.vue'

const node = (id: string, located = true): FlowNode => ({ id, label: `Punto ${id}`, lat: located ? 43.5 : null, lon: located ? -5.6 : null })
const NODES = [node('A'), node('B'), node('C'), node('D')]
const byId = new Map(NODES.map((n) => [n.id, n]))

function route(from: string, to: string, total: number): Route {
  const pair: FlowPair = {
    key: `${from}>${to}`,
    urn: `urn:ngsi-ld:Flow:${from}:${to}`,
    ref: { urn: `urn:ngsi-ld:Flow:${from}`, tenant: 'demo', scope: '/' },
    origin: byId.get(from)!,
    target: byId.get(to)!,
    label: `Punto ${from} → Punto ${to}`,
  }
  return { pair, points: [], total }
}

const ROUTES = [route('A', 'B', 60), route('B', 'A', 30), route('C', 'A', 10), route('B', 'C', 5)]

function mountPanels() {
  return mount(TransitsPanels, {
    props: { nodes: NODES, routes: ROUTES, totalSeries: [] },
    global: { plugins: [createPinia(), vuetify], stubs: { PointMap: true, LineChart: true } },
  })
}

const linkKeys = (wrapper: ReturnType<typeof mountPanels>) =>
  wrapper.findComponent({ name: 'PointMap' }).props('links').map((l: { key: string }) => l.key)

describe('TransitsPanels, recorridos de un punto', () => {
  it('sin elegir nada dibuja todos los recorridos, en arco, y el ranking general', () => {
    const wrapper = mountPanels()
    const links = wrapper.findComponent({ name: 'PointMap' }).props('links')
    expect(links.map((l: { key: string }) => l.key)).toEqual(['A>B', 'B>A', 'C>A', 'B>C'])
    expect(links.every((l: { curved?: boolean }) => l.curved)).toBe(true)
    expect(wrapper.text()).toContain('Diez recorridos principales')
  })

  it('el selector solo ofrece los puntos con recorridos', () => {
    const wrapper = mountPanels()
    const items = wrapper.findComponent({ name: 'VSelect' }).props('items').map((i: { title: string }) => i.title)
    expect(items).toEqual(['Todos los puntos', 'Punto A', 'Punto B', 'Punto C'])
  })

  it('al pulsar un punto deja solo sus recorridos y dice hacia dónde van y de dónde vienen', async () => {
    const wrapper = mountPanels()
    await wrapper.findComponent({ name: 'PointMap' }).vm.$emit('select', 'A')

    expect(linkKeys(wrapper)).toEqual(['A>B', 'B>A', 'C>A'])
    expect(wrapper.findComponent({ name: 'PointMap' }).props('selected')).toBe('A')
    expect(wrapper.text()).toContain('Recorridos de Punto A')
    const [out, into] = wrapper.findAll('table').map((table) => table.findAll('tbody tr').map((tr) => tr.text()))
    expect(out).toEqual(['Punto B60100 %'])
    // 30 de B y 10 de C: tres cuartos de lo que llega viene de B.
    expect(into).toEqual(['Punto B3075 %', 'Punto C1025 %'])
  })

  it('pulsar el mismo punto, o elegir «Todos los puntos», vuelve a verlo todo', async () => {
    const wrapper = mountPanels()
    const map = wrapper.findComponent({ name: 'PointMap' })
    await map.vm.$emit('select', 'B')
    expect(linkKeys(wrapper)).toEqual(['A>B', 'B>A', 'B>C'])
    await map.vm.$emit('select', 'B')
    expect(linkKeys(wrapper)).toHaveLength(4)

    await map.vm.$emit('select', 'C')
    await wrapper.findComponent({ name: 'VSelect' }).vm.$emit('update:modelValue', null)
    expect(linkKeys(wrapper)).toHaveLength(4)
    expect(wrapper.text()).toContain('Diez recorridos principales')
  })

  it('si el punto elegido deja de estar en el panel, se vuelve a ver todo', async () => {
    const wrapper = mountPanels()
    await wrapper.findComponent({ name: 'PointMap' }).vm.$emit('select', 'D')
    await wrapper.setProps({ nodes: NODES.filter((n) => n.id !== 'D') })
    expect(wrapper.findComponent({ name: 'PointMap' }).props('selected')).toBeNull()
  })
})
