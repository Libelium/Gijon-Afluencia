import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import type { Entity } from '@/types'
import { EVENT_CATALOG, type ScenarioEvent } from '../eventSimulation'

const fetchZoneSeries = vi.hoisted(() => vi.fn())

vi.mock('../data', async (original) => ({ ...(await original<typeof import('../data')>()), fetchZoneSeries }))

const { default: EventScenarioCard } = await import('./EventScenarioCard.vue')

const HOUR_MS = 3_600_000
const twin = {
  id: 453,
  name: 'Plaza Mayor (previsión)',
  urn: 'urn:ngsi-ld:Thing:plaza_mayor_pred',
  datamodel: 'Thing',
  tenant: 'demo',
  scope: '/',
} as Entity

/** Prevision por horas desde la hora en curso, como la que devuelve el servidor. */
function forecast(values: (number | null)[]) {
  const first = Math.floor(Date.now() / HOUR_MS) * HOUR_MS
  return values.map((v, i) => ({ t: new Date(first + i * HOUR_MS).toISOString(), v }))
}

function mountCard(capacity: number | null = 100, registered: ScenarioEvent[] = [], zoneName?: string) {
  return mount(EventScenarioCard, {
    props: { twin, predictedId: 'predictedPeopleCount', capacity, registered, zoneName },
    global: { plugins: [vuetify], stubs: { LineChart: true } },
    attachTo: document.body,
  })
}

const button = (wrapper: ReturnType<typeof mountCard>, label: string) =>
  wrapper.findAll('button').find((b) => b.text().includes(label))!

const concertShare = EVENT_CATALOG.find((s) => s.kind === 'concert')!.peakShare

afterEach(() => {
  fetchZoneSeries.mockReset()
  document.body.innerHTML = ''
})

describe('EventScenarioCard', () => {
  it('pide la previsión por horas de toda la semana que publica', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 50, 60]) })
    mountCard()
    await flushPromises()
    const [ref, specs, range, options] = fetchZoneSeries.mock.calls[0]
    expect(ref.urn).toBe(twin.urn)
    expect(specs).toEqual([{ key: 'predicted', fn: 'mean', measureId: 'predictedPeopleCount' }])
    expect(options).toEqual({ forceInterval: 'PT1H' })
    const hours = (Date.parse(range.end) - Date.parse(range.start)) / HOUR_MS
    // Desde el comienzo de la hora en curso hasta una semana después de ahora.
    expect(hours).toBeGreaterThanOrEqual(7 * 24)
    expect(hours).toBeLessThan(7 * 24 + 1)
  })

  it('el título dice la zona que se simula', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40]) })
    const wrapper = mountCard(100, [], 'Plaza Norte')
    await flushPromises()
    expect(wrapper.text()).toContain('Simulación de escenarios — Plaza Norte')
  })

  it('la duración llega a las 24 horas: un día entero', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40]) })
    const wrapper = mountCard()
    await flushPromises()
    const items = wrapper.findAllComponents({ name: 'VSelect' }).find((s) => s.props('label') === 'Duración')!.props('items')
    expect(items.at(-1)).toEqual({ title: '24 h', value: 24 })
  })

  it('un evento de varios días se suma cada día a la misma hora', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast(Array(72).fill(40)) })
    const wrapper = mountCard()
    await flushPromises()
    const daysSelect = wrapper.findAllComponents({ name: 'VSelect' }).find((s) => s.props('label') === 'Días')!
    await daysSelect.vm.$emit('update:modelValue', 3)
    await button(wrapper, 'Añadir evento').trigger('click')
    await flushPromises()

    const points = wrapper.findComponent({ name: 'LineChart' }).props('series')[1].points
    const full = Math.round(40 + 100 * concertShare)
    expect([0, 1, 24, 25, 48, 49].map((i) => points[i].v)).toEqual(Array(6).fill(full))
    expect(points[12].v).toBe(40)
    expect(wrapper.find('.v-chip').text()).toContain('3 días')
  })

  it('sin eventos enseña solo la previsión y el aforo', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 50, 60]) })
    const wrapper = mountCard()
    await flushPromises()
    expect(wrapper.text()).toContain('Añade un evento')
    const series = wrapper.findComponent({ name: 'LineChart' }).props('series')
    expect(series.map((s: { name: string }) => s.name)).toEqual(['Prevista', 'Aforo'])
  })

  it('al añadir un evento suma su gente, la cuenta en el resumen y sale en la tabla', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 50, 60, 50]) })
    const wrapper = mountCard()
    await flushPromises()
    await button(wrapper, 'Añadir evento').trigger('click')
    await flushPromises()

    const series = wrapper.findComponent({ name: 'LineChart' }).props('series')
    expect(series.map((s: { name: string }) => s.name)).toEqual(['Prevista', 'Con eventos', 'Aforo'])
    // Concierto de dos horas desde la hora en curso: pleno en las dos primeras, a medias en la tercera.
    const peak = 100 * concertShare
    expect(series[1].points.map((p: { v: number }) => p.v)).toEqual([
      Math.round(40 + peak),
      Math.round(50 + peak),
      Math.round(60 + peak / 2),
      50,
    ])
    expect(wrapper.find('.v-chip').text()).toContain('Concierto')
    expect(wrapper.find('tbody').text()).toContain(`+${Math.round(peak)}`)
    expect(wrapper.text()).toContain('Horas por encima del aforo')
  })

  it('se pueden quitar los eventos uno a uno o todos', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 50, 60]) })
    const wrapper = mountCard()
    await flushPromises()
    await button(wrapper, 'Añadir evento').trigger('click')
    await button(wrapper, 'Añadir evento').trigger('click')
    expect(wrapper.findAll('.v-chip')).toHaveLength(2)
    await wrapper.find('.v-chip__close').trigger('click')
    expect(wrapper.findAll('.v-chip')).toHaveLength(1)
    await button(wrapper, 'Limpiar').trigger('click')
    expect(wrapper.findAll('.v-chip')).toHaveLength(0)
  })

  it('sin aforo publicado, se refiere al máximo previsto y no cuenta horas por encima', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 80]) })
    const wrapper = mountCard(null)
    await flushPromises()
    await button(wrapper, 'Añadir evento').trigger('click')
    expect(wrapper.find('tbody').text()).toContain(`+${Math.round(80 * concertShare)}`)
    expect(wrapper.text()).toContain('La zona no publica su aforo')
    const series = wrapper.findComponent({ name: 'LineChart' }).props('series')
    expect(series.map((s: { name: string }) => s.name)).toEqual(['Prevista', 'Con eventos'])
  })

  it('sin previsión futura lo dice y no ofrece el formulario', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([null, null]) })
    const wrapper = mountCard()
    await flushPromises()
    expect(wrapper.text()).toContain('No hay previsión para las próximas horas')
    expect(button(wrapper, 'Añadir evento')).toBeUndefined()
  })

  it('si falla la petición lo dice y deja reintentar', async () => {
    fetchZoneSeries.mockRejectedValueOnce(new Error('caído')).mockResolvedValue({ predicted: forecast([40]) })
    const wrapper = mountCard()
    await flushPromises()
    expect(wrapper.text()).toContain('error')
    await button(wrapper, 'Reintentar').trigger('click')
    await flushPromises()
    expect(fetchZoneSeries).toHaveBeenCalledTimes(2)
    expect(button(wrapper, 'Añadir evento')).toBeDefined()
  })
})

describe('EventScenarioCard, eventos registrados', () => {
  const registeredAt = (hour: number): ScenarioEvent => ({
    id: -1,
    kind: 'market',
    weather: 'clear',
    intensity: 1,
    start: new Date(Math.floor(Date.now() / HOUR_MS) * HOUR_MS + hour * HOUR_MS).toISOString(),
    hours: 2,
    registered: true,
    notes: 'Mercado de prueba',
  })
  const marketShare = EVENT_CATALOG.find((s) => s.kind === 'market')!.peakShare

  it('se suman desde el principio, se marcan como registrados y no se pueden quitar', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 50, 60, 50]) })
    const wrapper = mountCard(100, [registeredAt(0)])
    await flushPromises()

    const chip = wrapper.find('.v-chip')
    expect(chip.text()).toContain('Registrado: Mercado o feria')
    expect(chip.find('.v-chip__close').exists()).toBe(false)
    expect(wrapper.text()).toContain('el modelo no aprende de los días con evento')
    const series = wrapper.findComponent({ name: 'LineChart' }).props('series')
    expect(series[1].points[0].v).toBe(Math.round(40 + 100 * marketShare))
  })

  it('«Limpiar» quita lo simulado y deja lo registrado', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 50, 60]) })
    const wrapper = mountCard(100, [registeredAt(0)])
    await flushPromises()
    await button(wrapper, 'Añadir evento').trigger('click')
    expect(wrapper.findAll('.v-chip')).toHaveLength(2)
    await button(wrapper, 'Limpiar').trigger('click')
    expect(wrapper.findAll('.v-chip')).toHaveLength(1)
    expect(wrapper.find('.v-chip').text()).toContain('Registrado')
  })
})
