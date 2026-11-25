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

describe('fetchPanelData con las horas anomalas de una zona', () => {
  const sensor: Partial<Entity> = {
    urn: `urn:ngsi-ld:${datamodelOf('flowObserved')}:SPT0001_CFO`,
    datamodel: datamodelOf('flowObserved'),
    tenant: 'demo',
    scope: '/',
  }

  const occupancyPanel = (type: string, entity: Partial<Entity> = zone, measure = 'occupancy'): Panel => ({
    id: 3,
    chart: { type },
    series: [{ entity, measure: { id: measure, name: 'Ocupacion', units: 'personas' } }],
  })

  const envelope = (urn: string | undefined, measure: string, values: { timestamp: string; value: number }[]) => ({
    time_series: [{ device_id: urn, measure_id: measure, values }],
  })

  /** Responde a cada peticion segun la medida que pide: la ocupacion o las marcas. */
  const answer = (flags: { timestamp: string; value: number }[]) =>
    post.mockImplementation(async (_url: string, body: { measure_ids: string[] }[]) => ({
      data: body.map((request) =>
        request.measure_ids[0] === 'isOutlier'
          ? envelope(zone.urn, 'isOutlier', flags)
          : envelope(zone.urn, 'occupancy', [
              { timestamp: '2026-10-27T09:00:00Z', value: 40 },
              { timestamp: '2026-10-27T10:00:00Z', value: 300 },
              { timestamp: '2026-10-27T11:00:00Z', value: 45 },
            ]),
      ),
    }))

  it('una linea con la ocupacion de una zona pide sus marcas con la misma ventana y por maximo', async () => {
    await fetchPanelData(occupancyPanel('line'), '7d', 'UTC')
    expect(post).toHaveBeenCalledTimes(2)
    const [line] = post.mock.calls[0][1]
    const [flags] = post.mock.calls[1][1]
    expect(flags.device_ids).toEqual([zone.urn])
    expect(flags.measure_ids).toEqual(['isOutlier'])
    expect(flags.options).toMatchObject({
      start_date: line.options.start_date,
      end_date: line.options.end_date,
      tenant: 'demo',
      scope: '/',
      aggregation: { type: 'max', interval: line.options.aggregation.interval },
    })
  })

  it('las horas marcadas salen como puntos sueltos sobre la linea', async () => {
    answer([
      { timestamp: '2026-10-27T10:00:00Z', value: 1 },
      { timestamp: '2026-10-27T11:00:00Z', value: 0 },
    ])
    const { series } = await fetchPanelData(occupancyPanel('line'), '24h', 'UTC')
    expect(series).toHaveLength(2)
    expect(series[1]).toEqual({
      name: 'Anomalía',
      units: 'personas',
      markers: true,
      points: [
        { t: '2026-10-27T09:00:00Z', v: null },
        { t: '2026-10-27T10:00:00Z', v: 300 },
        { t: '2026-10-27T11:00:00Z', v: null },
      ],
    })
  })

  it('sin ninguna hora marcada no añade la serie', async () => {
    answer([{ timestamp: '2026-10-27T10:00:00Z', value: 0 }])
    const { series } = await fetchPanelData(occupancyPanel('line'), '24h', 'UTC')
    expect(series).toHaveLength(1)
  })

  it('si la peticion de las marcas falla, la linea se pinta igual', async () => {
    post.mockImplementation(async (_url: string, body: { measure_ids: string[] }[]) => {
      if (body[0].measure_ids[0] === 'isOutlier') throw new Error('400')
      return { data: [envelope(zone.urn, 'occupancy', [{ timestamp: '2026-10-27T10:00:00Z', value: 300 }])] }
    })
    const { series } = await fetchPanelData(occupancyPanel('line'), '24h', 'UTC')
    expect(series).toHaveLength(1)
    expect(series[0].points).toEqual([{ t: '2026-10-27T10:00:00Z', v: 300 }])
  })

  it('la misma zona pintada dos veces lleva una sola serie de marcas', async () => {
    answer([{ timestamp: '2026-10-27T10:00:00Z', value: 1 }])
    const twice: Panel = {
      id: 4,
      chart: { type: 'line' },
      series: [
        { entity: zone, measure: { id: 'occupancy' }, grouping_function: 'mean' },
        { entity: zone, measure: { id: 'occupancy' }, grouping_function: 'max' },
      ],
    }
    const { series } = await fetchPanelData(twice, '24h', 'UTC')
    expect(post.mock.calls[1][1]).toHaveLength(1)
    expect(series.filter((serie) => serie.markers)).toHaveLength(1)
  })

  it('con varias entidades, la serie de marcas lleva el nombre de la zona', async () => {
    answer([{ timestamp: '2026-10-27T10:00:00Z', value: 1 }])
    const mixed: Panel = {
      id: 5,
      chart: { type: 'line' },
      series: [
        { entity: { ...zone, name: 'Plaza Mayor' }, measure: { id: 'occupancy' } },
        { entity: sensor, measure: { id: 'peopleCount' } },
      ],
    }
    const { series } = await fetchPanelData(mixed, '24h', 'UTC')
    expect(series.map((serie) => serie.name)).toContain('Plaza Mayor · Anomalía')
  })

  it.each([
    ['otro tipo de grafico', occupancyPanel('bar')],
    ['un grafico de ultimo valor', occupancyPanel('kpi')],
    ['un sensor que no es una zona', occupancyPanel('line', sensor, 'peopleCount')],
    ['una medida de la zona que no es su ocupacion', occupancyPanel('line', zone, 'dwellTime')],
    ['una prevision de la zona', occupancyPanel('line', prediction, 'predictedOccupancy')],
  ])('no pide marcas con %s', async (_case, target) => {
    await fetchPanelData(target, '24h', 'UTC')
    expect(post).toHaveBeenCalledTimes(1)
  })
})
