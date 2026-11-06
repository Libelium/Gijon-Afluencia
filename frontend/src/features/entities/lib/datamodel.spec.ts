import { describe, expect, it } from 'vitest'
import { datamodelOf } from '@/features/dashboards/templates/contract'
import { datamodelLabel } from './datamodel'

describe('datamodelLabel', () => {
  it('rotula en castellano los modelos de afluencia conocidos', () => {
    expect(datamodelLabel(datamodelOf('zone'))).toBe('Zona de afluencia')
    expect(datamodelLabel(datamodelOf('flowEvent'))).toBe('Visitas y recorridos')
    expect(datamodelLabel(datamodelOf('lidarDevice'))).toBe('Estado de los LIDAR')
  })

  it('un modelo desconocido conserva su nombre', () => {
    expect(datamodelLabel('WeatherObserved')).toBe('WeatherObserved')
    expect(datamodelLabel(null)).toBe('')
  })
})
