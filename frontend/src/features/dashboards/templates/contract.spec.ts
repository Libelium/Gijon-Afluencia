import { describe, expect, it } from 'vitest'
import {
  datamodelOf,
  datamodelsOf,
  isPredictionEntity,
  keyOfTypeId,
  supportedTypeIds,
  typeIdOf,
} from './contract'

describe('isPredictionEntity', () => {
  const prediction = datamodelOf('zonePrediction')
  const zone = datamodelOf('zone')

  it('reconoce la prevision por su modelo de datos', () => {
    expect(isPredictionEntity({ datamodel: prediction })).toBe(true)
  })

  it('y, cuando solo se conoce el URN, por el tipo que lleva', () => {
    expect(isPredictionEntity({ urn: `urn:ngsi-ld:${prediction}:P13_pred` })).toBe(true)
  })

  it('una zona no es una prevision', () => {
    expect(isPredictionEntity({ urn: `urn:ngsi-ld:${zone}:P13`, datamodel: zone })).toBe(false)
  })

  it('sin entidad, o sin URN ni modelo, no hay prevision', () => {
    expect(isPredictionEntity(null)).toBe(false)
    expect(isPredictionEntity(undefined)).toBe(false)
    expect(isPredictionEntity({})).toBe(false)
  })
})

describe('identificadores de plantilla', () => {
  it('se resuelven en los dos sentidos, sin distinguir mayusculas', () => {
    expect(keyOfTypeId(typeIdOf('lidarPrediction').toUpperCase())).toBe('lidarPrediction')
    expect(keyOfTypeId('no existe')).toBeNull()
    expect(keyOfTypeId(null)).toBeNull()
  })

  it('el filtro del listado recibe todos los identificadores soportados', () => {
    expect(supportedTypeIds()).toContain(typeIdOf('transits'))
    expect(supportedTypeIds()).toHaveLength(9)
  })

  it('los modelos de datos se descodifican en el orden pedido', () => {
    expect(datamodelsOf(['zone', 'zonePrediction'])).toEqual([datamodelOf('zone'), datamodelOf('zonePrediction')])
  })
})
