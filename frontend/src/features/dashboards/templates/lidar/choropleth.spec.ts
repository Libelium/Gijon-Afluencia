import { describe, expect, it } from 'vitest'
import { aforoColor, aforoLevel, AFORO_SCALE, darken } from '../../palette'
import { deviceUrn, polygonOf, ratioOf, summarize, timeSteps, twinUrn, valueAt, zoneSerials, type ZoneState } from './choropleth'

describe('aforoLevel', () => {
  it('un tramo por cada 20 % del aforo, y lo que pasa del 80 % es el ultimo', () => {
    expect(aforoLevel(0)).toBe(0)
    expect(aforoLevel(0.19)).toBe(0)
    expect(aforoLevel(0.2)).toBe(1)
    expect(aforoLevel(0.79)).toBe(3)
    expect(aforoLevel(0.8)).toBe(4)
    expect(aforoLevel(1.4)).toBe(4)
    expect(aforoLevel(Number.NaN)).toBe(0)
    expect(aforoColor(0.5)).toBe(AFORO_SCALE[2])
  })
})

describe('polygonOf', () => {
  it('pasa el contorno de GeoJSON a [lat, lon] y descarta lo que no es poligono', () => {
    const polygon = polygonOf({
      type: 'Polygon',
      coordinates: [
        [
          [-5.66, 43.54],
          [-5.65, 43.54],
          [-5.65, 43.55],
          [-5.66, 43.54],
        ],
      ],
    })
    expect(polygon?.[0]).toEqual([43.54, -5.66])
    expect(polygonOf({ type: 'Point', coordinates: [-5.66, 43.54] })).toBeNull()
    expect(polygonOf(undefined)).toBeNull()
    expect(polygonOf({ type: 'Polygon', coordinates: [[[-5.66, 43.54]]] })).toBeNull()
  })
})

describe('ratioOf', () => {
  it('sin aforo o sin lectura no hay proporcion', () => {
    expect(ratioOf(30, 120)).toBe(0.25)
    expect(ratioOf(30, null)).toBeNull()
    expect(ratioOf(30, 0)).toBeNull()
    expect(ratioOf(null, 120)).toBeNull()
  })
})

describe('series por horas', () => {
  const a = [
    { t: '2026-11-17T10:00:00Z', v: 4 },
    { t: '2026-11-17T11:00:00Z', v: null },
  ]
  const b = [
    { t: '2026-11-17T09:00:00Z', v: 9 },
    { t: '2026-11-17T10:00:00Z', v: 2 },
  ]

  it('junta las horas con lectura, en orden, y lee el valor de cada una', () => {
    expect(timeSteps([a, b])).toEqual(['2026-11-17T09:00:00Z', '2026-11-17T10:00:00Z'])
    expect(valueAt(a, '2026-11-17T10:00:00Z')).toBe(4)
    expect(valueAt(a, '2026-11-17T09:00:00Z')).toBeNull()
  })
})

describe('summarize', () => {
  const zone = (id: number, value: number | null, capacity: number | null): ZoneState => ({
    id,
    name: `Z${id}`,
    polygon: null,
    value,
    capacity,
    ratio: ratioOf(value, capacity),
  })

  it('suma personas y aforos solo de las zonas que publican aforo', () => {
    const summary = summarize([zone(1, 90, 100), zone(2, 10, 100), zone(3, 500, null), zone(4, null, 50)])
    expect(summary.combinedRatio).toBe(0.5)
    expect(summary.nearFull).toBe(1)
    expect(summary.fullest?.id).toBe(1)
  })

  it('sin aforos no hay nada que resumir', () => {
    expect(summarize([zone(1, 5, null)])).toEqual({ combinedRatio: null, nearFull: 0, fullest: null })
  })
})

describe('dispositivos de la zona', () => {
  it('lee las listas de serie que publica la fusion, en texto JSON o ya como lista', () => {
    expect(
      zoneSerials([
        { id: 'lidarSerial', value: '["L1", "L2"]' },
        { id: 'smartspotSerial', value: ['SS5'] },
      ]),
    ).toEqual({ lidar: ['L1', 'L2'], smartspot: ['SS5'] })
    expect(zoneSerials([{ id: 'lidarSerial', value: '[]' }])).toEqual({ lidar: [], smartspot: [] })
    expect(zoneSerials([{ id: 'smartspotSerial', value: 'SS9' }]).smartspot).toEqual(['SS9'])
  })

  it('el Smart Spot se situa con su entidad de conteos y el LIDAR con la de sus metricas', () => {
    const models = { smartspot: 'CrowdFlowObserved', lidar: 'CrowdFlowLidarObserved' }
    expect(deviceUrn('smartspot', 'SS5', models)).toBe('urn:ngsi-ld:CrowdFlowObserved:SS5_CFO')
    expect(deviceUrn('lidar', 'L1', models)).toBe('urn:ngsi-ld:CrowdFlowLidarObserved:L1')
  })
})

describe('darken', () => {
  it('mezcla el color con negro en la proporcion pedida', () => {
    expect(darken('#FC8D59', 0)).toBe('#FC8D59')
    expect(darken('#FC8D59', 1)).toBe('#000000')
    expect(darken('#FFFFFF', 0.5)).toBe('#808080')
  })
})

describe('twinUrn', () => {
  it('cambia el modelo de datos y conserva el id de la zona', () => {
    expect(twinUrn('urn:ngsi-ld:CrowdFlowZone:P03', 'CrowdFlowZone', 'CrowdFlowLidarZone')).toBe(
      'urn:ngsi-ld:CrowdFlowLidarZone:P03',
    )
    expect(twinUrn('urn:ngsi-ld:Otra:P03', 'CrowdFlowZone', 'CrowdFlowLidarZone')).toBeNull()
  })
})
