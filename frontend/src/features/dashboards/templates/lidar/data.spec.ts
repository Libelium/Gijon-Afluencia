import { describe, expect, it } from 'vitest'
import type { Entity, Measure } from '@/types'
import { datamodelOf } from '../contract'
import { describeZone, predictionModel, zoneEntities, zoneModel } from './data'

let nextId = 1

function entity(key: 'zone' | 'zoneScan' | 'zonePrediction' | 'flowObserved', tail: string): Entity {
  const datamodel = datamodelOf(key)
  return { id: nextId++, name: tail, urn: `urn:ngsi-ld:${datamodel}:${tail}`, datamodel, tenant: 'demo', scope: '/' }
}

const measure = (id: string, value: unknown): Measure => ({ id, name: id, value })

describe('modelos', () => {
  it('la zona de las plantillas es la fusionada, la que se ofrece al configurar el panel', () => {
    expect(zoneModel()).toBe(datamodelOf('zone'))
    expect(predictionModel()).toBe(datamodelOf('zonePrediction'))
  })
})

describe('zoneEntities', () => {
  it('con zonas fusionadas asignadas no avisa de nada y deja fuera las previsiones', () => {
    const zone = entity('zone', 'P13')
    expect(zoneEntities([zone, entity('zonePrediction', 'P13_pred')])).toEqual({
      zones: [zone],
      usedFallback: false,
    })
  })

  it('prefiere la zona fusionada a la analitica del sensor de barrido', () => {
    const zone = entity('zone', 'P01')
    expect(zoneEntities([entity('zoneScan', 'Z01'), zone]).zones).toEqual([zone])
  })

  it('si solo hay analitica del sensor de barrido, la usa sin aviso', () => {
    const scan = entity('zoneScan', 'Z01')
    expect(zoneEntities([scan])).toEqual({ zones: [scan], usedFallback: false })
  })

  it('sin ninguna de las dos usa lo asignado, avisando, pero nunca una prevision', () => {
    const other = entity('flowObserved', 'S1_CFO')
    expect(zoneEntities([other, entity('zonePrediction', 'P13_pred')])).toEqual({
      zones: [other],
      usedFallback: true,
    })
  })

  it('un panel vacio no avisa', () => {
    expect(zoneEntities([])).toEqual({ zones: [], usedFallback: false })
  })
})

describe('describeZone con la zona fusionada', () => {
  const profile = describeZone([
    measure('occupancy', 45),
    measure('smartspotDeltaPct', 12),
    measure('smartspotSignal', 30),
    measure('confidence', 'measured'),
    measure('case', 'mixed'),
  ])

  it('la ocupacion actual son las 45 personas, sin recurrir a otra medida', () => {
    expect(profile.occupancy?.id).toBe('occupancy')
    expect(profile.occupancyIsFallback).toBe(false)
    expect(profile.current).toBe(45)
  })

  it('sin aforo no inventa un porcentaje', () => {
    expect(profile.capacity).toBeNull()
    expect(profile.ratio).toBeNull()
  })

  it('con aforo el porcentaje sale de las personas sobre el aforo', () => {
    const withCapacity = describeZone([measure('occupancy', 45), measure('maxCapacity', 90)])
    expect(withCapacity.ratio).toBe(0.5)
  })
})

describe('describeZone con zonas que nombran explicitamente las personas', () => {
  it('usa `peopleCountInZone` como personas y no la `occupancy` fraccionaria', () => {
    const profile = describeZone([
      measure('occupancy', 0.15),
      measure('occupancyRatio', 0.49),
      measure('peopleCountInZone', 84),
      measure('maxCapacity', 168),
    ])
    expect(profile.current).toBe(84)
    expect(profile.capacity).toBe(168)
    expect(profile.ratio).toBe(0.5)
  })
})
