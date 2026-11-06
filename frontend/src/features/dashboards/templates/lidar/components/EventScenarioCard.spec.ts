import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import { ApiError } from '@/api/http'
import type { Entity } from '@/types'
import { EVENT_CATALOG, type ScenarioEvent } from '../eventSimulation'

const fetchZoneSeries = vi.hoisted(() => vi.fn())
const listRegistry = vi.hoisted(() => vi.fn())
const registerEvent = vi.hoisted(() => vi.fn())

vi.mock('../data', async (original) => ({ ...(await original<typeof import('../data')>()), fetchZoneSeries }))
vi.mock('../predictionEvents', async (original) => ({
  ...(await original<typeof import('../predictionEvents')>()),
  listRegistry,
  registerEvent,
}))

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
  listRegistry.mockReset()
  registerEvent.mockReset()
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
    const values = series[1].points.map((p: { v: number | null }) => p.v)
    expect(values.slice(0, 4)).toEqual([Math.round(40 + peak), Math.round(50 + peak), Math.round(60 + peak / 2), 50])
    // Sin medidas de la zona no hay nada habitual que dibujar donde acaba la prevision.
    expect(values.slice(4).every((v: number | null) => v === null)).toBe(true)
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

  it('sin previsión futura lo dice, deja el formulario a la vista pero desactivado y no dibuja la gráfica', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([null, null]) })
    const wrapper = mountCard()
    await flushPromises()
    expect(wrapper.text()).toContain('No hay previsión para las próximas horas')
    expect(button(wrapper, 'Añadir evento').attributes('disabled')).toBeDefined()
    expect(wrapper.findComponent({ name: 'LineChart' }).exists()).toBe(false)
  })

  it('sin previsión futura dice cuál fue la última hora prevista', async () => {
    const last = new Date(Math.floor(Date.now() / HOUR_MS) * HOUR_MS - 4 * HOUR_MS).toISOString()
    fetchZoneSeries
      .mockResolvedValueOnce({ predicted: [] })
      .mockResolvedValueOnce({ predicted: [{ t: last, v: 12 }] })
    const wrapper = mountCard()
    await flushPromises()
    expect(wrapper.text()).toContain('La última hora prevista fue el')
    // La segunda consulta mira hacia atrás y pide solo el último valor.
    const [, , range, options] = fetchZoneSeries.mock.calls[1]
    expect(Date.parse(range.end)).toBeLessThanOrEqual(Date.now())
    expect(options).toMatchObject({ limit: 1 })
  })

  it('sin previsión el registro de eventos sigue disponible', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: [] })
    listRegistry.mockResolvedValue({ rows: [], canEdit: true })
    const wrapper = mount(EventScenarioCard, {
      props: { twin, predictedId: 'predictedPeopleCount', capacity: 100, zoneUrn: 'urn:ngsi-ld:Zone:Z01' },
      global: { plugins: [vuetify], stubs: { LineChart: true } },
      attachTo: document.body,
    })
    await flushPromises()
    expect(button(wrapper, 'Registrar un evento')).toBeDefined()
  })

  it('el inicio se elige por día y hora, y dice hasta cuándo se puede simular', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast(Array(48).fill(40)) })
    const wrapper = mountCard()
    await flushPromises()
    const select = (label: string) => wrapper.findAllComponents({ name: 'VSelect' }).find((s) => s.props('label') === label)!
    const days = select('Día').props('items') as { value: string }[]
    expect(days.length).toBeGreaterThanOrEqual(2)
    await select('Día').vm.$emit('update:modelValue', days[1].value)
    await flushPromises()
    const hoursOfDay = select('Hora de inicio').props('items') as { value: string }[]
    expect(hoursOfDay.every((item) => item.value.startsWith(days[1].value))).toBe(true)
    expect(select('Hora de inicio').props('modelValue')).toBe(hoursOfDay[0].value)
    expect(wrapper.text()).toContain('Se puede simular desde ahora hasta el')
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

describe('EventScenarioCard, registro de eventos', () => {
  const ZONE = 'urn:ngsi-ld:Zone:plaza'
  const tz = 'Europe/Madrid'
  const today = () => new Date(Date.now()).toLocaleDateString('sv-SE', { timeZone: tz })
  const marketToday = {
    id: '0:abc',
    date: today(),
    end_date: today(),
    event_type: 'market',
    device_ids: [ZONE],
    notes: '',
    start_hour: 0,
    end_hour: 24,
  }

  function mountWithRegistry(registered: ScenarioEvent[] = []) {
    return mount(EventScenarioCard, {
      props: { twin, predictedId: 'predictedPeopleCount', capacity: 100, registered, zoneUrn: ZONE, timeZone: tz },
      global: { plugins: [vuetify], stubs: { LineChart: true } },
      attachTo: document.body,
    })
  }

  it('lo registrado se suma al momento, sin esperar a que la previsión lo publique', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 50]) })
    listRegistry.mockResolvedValue({ rows: [marketToday], canEdit: false })
    const wrapper = mountWithRegistry()
    await flushPromises()

    expect(listRegistry).toHaveBeenCalledWith({ tenant: 'demo', scope: '/' })
    expect(wrapper.find('.v-chip').text()).toContain('Registrado: Mercado o feria')
    expect(wrapper.text()).toContain('Registro de eventos')
  })

  it('un evento simulado se registra con sus datos y deja de contarse como simulado', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 50, 60]) })
    listRegistry.mockResolvedValueOnce({ rows: [], canEdit: true })
    const wrapper = mountWithRegistry()
    await flushPromises()
    await button(wrapper, 'Añadir evento').trigger('click')
    await flushPromises()

    listRegistry.mockResolvedValue({ rows: [marketToday], canEdit: true })
    registerEvent.mockResolvedValue(marketToday)
    await wrapper.find('tbody button').trigger('click')
    await flushPromises()
    const dialog = document.querySelector('.v-overlay__content')!
    ;([...dialog.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Registrar') as HTMLButtonElement).click()
    await flushPromises()

    const [, body] = registerEvent.mock.calls[0]
    expect(body).toMatchObject({ event_type: 'concert', device_ids: [ZONE], date: today() })
    // Dos horas, salvo que empiece a las 23: el registro acaba como tarde a las 24.
    expect(body.end_hour).toBe(Math.min(24, body.start_hour + 2))
    const chips = wrapper.findAll('.v-chip').map((c) => c.text())
    expect(chips).toHaveLength(1)
    expect(chips[0]).toContain('Registrado')
  })

  it('sin permiso para leer el registro, sigue con lo que publicó la previsión', async () => {
    fetchZoneSeries.mockResolvedValue({ predicted: forecast([40, 50]) })
    listRegistry.mockRejectedValue(new ApiError('forbidden', 'Forbidden', 403))
    const published: ScenarioEvent = {
      id: -1,
      kind: 'food',
      weather: 'clear',
      intensity: 1,
      start: new Date(Math.floor(Date.now() / HOUR_MS) * HOUR_MS).toISOString(),
      hours: 2,
      registered: true,
    }
    const wrapper = mountWithRegistry([published])
    await flushPromises()

    expect(wrapper.find('.v-chip').text()).toContain('Registrado: Evento gastronómico')
    expect(wrapper.text()).not.toContain('Registro de eventos')
    expect(button(wrapper, 'Registrar')).toBeUndefined()
  })
})

describe('EventScenarioCard, lo habitual donde no hay previsión', () => {
  const zoneEntity = {
    id: 12,
    name: 'Zona',
    urn: 'urn:ngsi-ld:Zone:plaza',
    datamodel: 'Zone',
    tenant: 'demo',
    scope: '/',
  } as Entity

  /** Cuatro semanas medidas, hasta la hora en curso, con 30 personas a cualquier hora. */
  function history(value: number) {
    const first = Math.floor(Date.now() / HOUR_MS) * HOUR_MS - 28 * 24 * HOUR_MS
    return Array.from({ length: 28 * 24 }, (_, i) => ({ t: new Date(first + i * HOUR_MS).toISOString(), v: value }))
  }

  function mountWithZone() {
    return mount(EventScenarioCard, {
      props: { twin, predictedId: 'predictedPeopleCount', capacity: 100, zone: zoneEntity, measuredId: 'peopleCount', timeZone: 'UTC' },
      global: { plugins: [vuetify], stubs: { LineChart: true } },
      attachTo: document.body,
    })
  }

  it('pide las cuatro últimas semanas medidas de la zona, hasta la hora en curso', async () => {
    fetchZoneSeries.mockImplementation(async (_ref, specs) => (specs[0].key === 'predicted' ? { predicted: forecast([40]) } : { measured: [] }))
    mountWithZone()
    await flushPromises()

    const [ref, specs, range, options] = fetchZoneSeries.mock.calls.find(([, s]) => s[0].key === 'measured')!
    expect(ref.urn).toBe(zoneEntity.urn)
    expect(specs).toEqual([{ key: 'measured', fn: 'mean', measureId: 'peopleCount' }])
    expect(options).toEqual({ forceInterval: 'PT1H' })
    expect((Date.parse(range.end) - Date.parse(range.start)) / HOUR_MS).toBe(28 * 24)
    expect(Date.parse(range.end)).toBe(Math.floor(Date.now() / HOUR_MS) * HOUR_MS)
  })

  it('después del primer día simula sobre lo habitual y lo dice', async () => {
    fetchZoneSeries.mockImplementation(async (_ref, specs) =>
      specs[0].key === 'predicted' ? { predicted: forecast(Array(24).fill(40)) } : { measured: history(30) },
    )
    const wrapper = mountWithZone()
    await flushPromises()
    await wrapper.findAllComponents({ name: 'VSelect' }).find((s) => s.props('label') === 'Días')!.vm.$emit('update:modelValue', 3)
    await button(wrapper, 'Añadir evento').trigger('click')
    await flushPromises()

    const series = wrapper.findComponent({ name: 'LineChart' }).props('series')
    expect(series.map((s: { name: string }) => s.name)).toEqual(['Prevista', 'Habitual (sin previsión)', 'Con eventos', 'Aforo'])
    const [forecastLine, usualLine, withEvents] = series.map((s: { points: { v: number | null }[] }) => s.points.map((p) => p.v))
    expect(forecastLine[23]).toBe(40)
    expect(forecastLine[24]).toBeNull()
    expect([usualLine[22], usualLine[23], usualLine[24], usualLine[167]]).toEqual([null, 40, 30, 30])
    // El concierto del segundo día se suma a lo habitual: 30 personas, no las 40 previstas.
    expect(withEvents[24]).toBe(Math.round(30 + 100 * concertShare))
    expect(wrapper.text()).toContain('La previsión cubre el primer día')
  })

  it('sin medidas de la zona, sigue con la previsión sola', async () => {
    fetchZoneSeries.mockImplementation(async (_ref, specs) => {
      if (specs[0].key === 'measured') throw new Error('caído')
      return { predicted: forecast([40, 50]) }
    })
    const wrapper = mountWithZone()
    await flushPromises()

    expect(wrapper.text()).not.toContain('error')
    expect(button(wrapper, 'Añadir evento')).toBeDefined()
    expect(wrapper.text()).not.toContain('La previsión cubre el primer día')
  })
})
