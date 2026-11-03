import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import vuetify from '@/plugins/vuetify'
import { datamodelOf } from '@/features/dashboards/templates/contract'
import type { EntityRef, Measure } from '@/types'
import MeasureHistoryDialog from './MeasureHistoryDialog.vue'

const { getMeasureHistory } = vi.hoisted(() => ({ getMeasureHistory: vi.fn() }))

vi.mock('../api/history', () => ({ getMeasureHistory }))

const NOW = '2026-10-27T12:00:00Z'

const measure: Measure = { id: 'predictedOccupancy', name: 'Predicted Occupancy' }

const refOf = (datamodel: string, id: string): EntityRef => ({
  urn: `urn:ngsi-ld:${datamodel}:${id}`,
  tenant: 'demo',
  scope: '/',
})

/** Abre el dialogo como lo hace la ficha y devuelve la ventana que pidio al servidor. */
async function requestedRange(entityRef: EntityRef) {
  const wrapper = mount(MeasureHistoryDialog, {
    props: { modelValue: false, measure, entityRef, timeZone: 'UTC' },
    global: { plugins: [createPinia(), vuetify] },
    attachTo: document.body,
  })
  await wrapper.setProps({ modelValue: true })
  await flushPromises()
  const range = getMeasureHistory.mock.calls[0][2]
  wrapper.unmount()
  return range
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(NOW))
  getMeasureHistory.mockReset()
  getMeasureHistory.mockResolvedValue({ points: [], aggregation: null })
})

afterEach(() => vi.useRealTimers())

describe('MeasureHistoryDialog', () => {
  it('en una prevision pide tambien las horas futuras', async () => {
    const range = await requestedRange(refOf(datamodelOf('zonePrediction'), 'P13_pred'))
    expect(range).toEqual({ start: '2026-10-26T12:00:00Z', end: '2026-10-28T12:00:00Z' })
  })

  it('en el resto de entidades la ventana acaba en «ahora»', async () => {
    const range = await requestedRange(refOf(datamodelOf('zone'), 'P13'))
    expect(range.end).toBe(NOW)
  })

  it('el «ultimo dato» de una prevision es el de ahora, no la hora prevista mas lejana', async () => {
    getMeasureHistory.mockResolvedValue({
      points: [
        { t: '2026-10-27T11:00:00Z', v: 95 },
        { t: '2026-10-28T11:00:00Z', v: 140 },
      ],
      aggregation: null,
    })
    const wrapper = mount(MeasureHistoryDialog, {
      props: { modelValue: false, measure, entityRef: refOf(datamodelOf('zonePrediction'), 'P13_pred'), timeZone: 'UTC' },
      global: { plugins: [createPinia(), vuetify] },
      attachTo: document.body,
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()
    // El rotulo, no la tabla alternativa: esa lista todos los puntos, tambien los previstos.
    const caption = [...document.body.querySelectorAll('span')].find((el) =>
      el.textContent?.startsWith('Último:'),
    )?.textContent
    wrapper.unmount()
    expect(caption).toContain('95')
    expect(caption).not.toContain('140')
  })
})
