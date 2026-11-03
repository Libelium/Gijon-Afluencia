import { describe, expect, it } from 'vitest'
import { matchRole } from './roles'

/** Atributos tal y como los publica cada entidad de zona. */
const ZONE = ['occupancy', 'confidence', 'case', 'smartspotSignal', 'smartspotDeltaPct', 'lidarSerial', 'smartspotSerial']

const metrics = (prefix: string) =>
  ['Count', 'ConcurrentMax', 'ConcurrentAvg', 'Entered', 'Exited', 'StayAvg', 'StationaryCount', 'Transitions'].map(
    (metric) => `${prefix}${metric}`,
  )
const SCAN = [...metrics('total'), ...metrics('adult'), ...metrics('vehicle')]

const PREDICTION = [
  'zoneId',
  'predictedOccupancy',
  'predictedOccupancyLower',
  'predictedOccupancyUpper',
  'horizonStep',
  'generatedAt',
]

describe('matchRole con la zona fusionada', () => {
  it('`occupancy` son las personas de la zona, no un porcentaje', () => {
    expect(matchRole(ZONE, 'occupancy')).toBe('occupancy')
    expect(matchRole(ZONE, 'ratio')).toBeNull()
  })

  it('no hay aforo publicado', () => {
    expect(matchRole(ZONE, 'capacity')).toBeNull()
  })
})

describe('matchRole con zonas que nombran explicitamente las personas', () => {
  // Esquema de las zonas de la demo: `occupancy` es una proporcion y las personas van aparte.
  const DEMO = ['occupancy', 'occupancyRatio', 'peopleCountInZone', 'maxCapacity', 'capacity', 'totalConcurrentMax']

  it('las personas son `peopleCountInZone`, no la `occupancy` fraccionaria', () => {
    expect(matchRole(DEMO, 'occupancy')).toBe('peopleCountInZone')
  })

  it('el porcentaje es `occupancyRatio` y el aforo `maxCapacity`', () => {
    expect(matchRole(DEMO, 'ratio')).toBe('occupancyRatio')
    expect(matchRole(DEMO, 'capacity')).toBe('maxCapacity')
  })
})

describe('matchRole con la analitica del sensor de barrido', () => {
  it('la ocupacion es la simultanea del total, no la afluencia acumulada de una etiqueta', () => {
    expect(matchRole(SCAN, 'occupancy')).toBe('totalConcurrentMax')
  })
})

describe('matchRole con la prevision', () => {
  it('reconoce la prevision y su banda', () => {
    expect(matchRole(PREDICTION, 'predicted')).toBe('predictedOccupancy')
    expect(matchRole(PREDICTION, 'predLower')).toBe('predictedOccupancyLower')
    expect(matchRole(PREDICTION, 'predUpper')).toBe('predictedOccupancyUpper')
  })

  it('la prevision no se confunde con la ocupacion medida', () => {
    expect(matchRole(PREDICTION, 'occupancy')).toBeNull()
  })
})

describe('matchRole, reglas generales', () => {
  it('`count` vale si se llama exactamente asi, nunca por contencion', () => {
    expect(matchRole(['count'], 'occupancy')).toBe('count')
    expect(matchRole(['adultCount'], 'occupancy')).toBeNull()
  })

  it('el resto de candidatos largos siguen casando por contencion', () => {
    expect(matchRole(['zone_peopleCount_now'], 'occupancy')).toBe('zone_peopleCount_now')
  })
})
