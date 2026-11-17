import { describe, expect, it } from 'vitest'
import { datamodelOf } from '@/features/dashboards/templates/contract'
import { datamodelInfo, datamodelLabel } from './datamodel'

describe('datamodelLabel', () => {
  it('rotula en castellano los modelos de afluencia conocidos', () => {
    expect(datamodelLabel(datamodelOf('zone'))).toBe('Zona de afluencia (combinada)')
    expect(datamodelLabel(datamodelOf('flowEvent'))).toBe('Visitas y recorridos')
    expect(datamodelLabel(datamodelOf('lidarDevice'))).toBe('Estado de los LIDAR')
  })

  it('un modelo desconocido conserva su nombre', () => {
    expect(datamodelLabel('WeatherObserved')).toBe('WeatherObserved')
    expect(datamodelLabel(null)).toBe('')
  })
})

describe('datamodelInfo', () => {
  it('distingue la zona combinada de la de solo LIDAR y dice de dónde salen sus datos', () => {
    const combined = datamodelInfo(datamodelOf('zone'))!
    const lidar = datamodelInfo(datamodelOf('zoneScan'))!
    expect(combined.source).toMatch(/LIDAR y los sensores WiFi\/BLE/)
    expect(combined.description).toMatch(/tenga los sensores que tenga/)
    expect(lidar.label).toBe('Zona de afluencia (solo LIDAR)')
    expect(lidar.description).toMatch(/sin los sensores WiFi\/BLE/)
  })

  it('todos los modelos conocidos tienen descripción y origen; uno desconocido, nada', () => {
    for (const key of ['zone', 'zoneScan', 'zonePrediction', 'flowObserved', 'rawEvent', 'flowEvent', 'lidarObserved', 'lidarDevice'] as const) {
      const info = datamodelInfo(datamodelOf(key))
      expect(info?.description, key).toBeTruthy()
      expect(info?.source, key).toBeTruthy()
    }
    expect(datamodelInfo('WeatherObserved')).toBeNull()
  })
})
