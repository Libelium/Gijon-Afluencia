import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Entity, Panel } from '@/types'
import { datamodelOf } from '../templates/contract'
import { fetchPanelData } from './panelData'

const { post } = vi.hoisted(() => ({ post: vi.fn() }))

vi.mock('@/api/http', () => ({ http: { post } }))

const NOW = '2026-10-27T12:00:00Z'

const prediction: Partial<Entity> = {
  urn: `urn:ngsi-ld:${datamodelOf('zonePrediction')}:P13_pred`,
  datamodel: datamodelOf('zonePrediction'),
  tenant: 'demo',
  scope: '/',
}

const zone: Partial<Entity> = {
  urn: `urn:ngsi-ld:${datamodelOf('zone')}:P13`,
  datamodel: datamodelOf('zone'),
  tenant: 'demo',
  scope: '/',
}

const panel = (type: string, entity: Partial<Entity>): Panel => ({
  id: 1,
  chart: { type },
  series: [{ entity, measure: { id: 'predictedOccupancy', name: 'Prevision' } }],
})

/** Opciones de la primera peticion `/timeseries` que salio. */
const sent = () => post.mock.calls[0][1][0].options

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(NOW))
  post.mockReset()
  post.mockResolvedValue({ data: [] })
})

afterEach(() => vi.useRealTimers())

describe('fetchPanelData con previsiones', () => {
  it('una grafica de lineas de una prevision pide tambien las horas futuras', async () => {
    await fetchPanelData(panel('line', prediction), '24h', 'UTC')
    expect(sent()).toMatchObject({
      start_date: '2026-10-26T12:00:00Z',
      end_date: '2026-10-28T12:00:00Z',
      order: 'desc',
      tenant: 'demo',
    })
  })

  it('el resto de entidades se queda en «ahora»', async () => {
    await fetchPanelData(panel('line', zone), '24h', 'UTC')
    expect(sent().end_date).toBe(NOW)
  })

  it('un grafico de ultimo valor de una prevision tambien: muestra la hora en curso', async () => {
    await fetchPanelData(panel('kpi', prediction), '24h', 'UTC')
    expect(sent()).toMatchObject({ end_date: NOW, limit: 1 })
    expect(sent().aggregation).toBeUndefined()
  })

  it('devuelve los puntos futuros y los ordena de antiguo a reciente', async () => {
    post.mockResolvedValue({
      data: [
        {
          time_series: [
            {
              device_id: prediction.urn,
              measure_id: 'predictedOccupancy',
              values: [
                { timestamp: '2026-10-28T10:00:00', value: 140 },
                { timestamp: '2026-10-27T10:00:00', value: '95' },
                { value: 1 },
              ],
            },
          ],
        },
      ],
    })
    const { series } = await fetchPanelData(panel('line', prediction), '24h', 'UTC')
    expect(series[0].points).toEqual([
      { t: '2026-10-27T10:00:00', v: 95 },
      { t: '2026-10-28T10:00:00', v: 140 },
    ])
  })

  it('un panel sin series consultables no llama al servidor', async () => {
    const empty: Panel = { id: 2, chart: { type: 'line' }, series: [{ measure: { id: 'x' } }] }
    await expect(fetchPanelData(empty, '24h')).resolves.toEqual({ series: [] })
    expect(post).not.toHaveBeenCalled()
  })
})
