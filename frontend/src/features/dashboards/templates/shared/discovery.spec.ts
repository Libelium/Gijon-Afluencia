import { describe, expect, it } from 'vitest'
import type { Measure } from '@/types'
import { detectCategories, pickMeasure } from './discovery'

const measures = (...ids: string[]): Measure[] =>
  ids.map((id) => ({ id, name: id, value_type: 'double', value: 1 }) as unknown as Measure)

// Lo que publica en pre la entidad de eventos de la ETL de un sensor (`<serie>_CFE`).
const ETL_EVENTS = measures(
  'averageVisitDuration',
  'visits',
  'uniqueVisitors',
  'shortTermVisitorVisits',
  'shortTermVisitorUniqueVisitors',
  'averageTransitDuration',
  'count',
  'touristCount',
  'residentCount',
  'uniqueVisitorsDaily',
  'newUniqueVisitorsDaily',
  'newResidentUniqueVisitorsDaily',
  'newTouristUniqueVisitorsDaily',
  'newResidentUniqueVisitorsBiweekly',
  'newTouristUniqueVisitorsBiweekly',
  'newResidentUniqueVisitorsMonthly',
  'newTouristUniqueVisitorsMonthly',
)

describe('pickMeasure, aforo', () => {
  it('en las entidades de eventos de la ETL el aforo son las personas distintas, no los tránsitos', () => {
    expect(pickMeasure(ETL_EVENTS, 'occupancy')).toBe('uniqueVisitors')
  })

  it('el conteo de personas sigue por delante cuando existe', () => {
    expect(pickMeasure(measures('count', 'uniqueVisitors', 'peopleCount'), 'occupancy')).toBe('peopleCount')
  })

  it('sin otra candidata, `count` sigue valiendo', () => {
    expect(pickMeasure(measures('count'), 'occupancy')).toBe('count')
  })
})

describe('detectCategories', () => {
  it('los periodos de agregación no son categorías', () => {
    const periods = measures(
      'newResidentUniqueVisitorsDaily',
      'newResidentUniqueVisitorsBiweekly',
      'newResidentUniqueVisitorsMonthly',
    )
    expect(detectCategories(periods).categories).toEqual([])
  })

  it('reparte las entidades de eventos de la ETL en turistas, residentes y corta estancia', () => {
    const all = [...ETL_EVENTS, ...measures('touristUniqueVisitors', 'residentUniqueVisitors')]
    expect(detectCategories(all).categories).toEqual([
      { measureId: 'touristUniqueVisitors', label: 'Turistas', order: 0 },
      { measureId: 'residentUniqueVisitors', label: 'Residentes', order: 1 },
      { measureId: 'shortTermVisitorUniqueVisitors', label: 'Corta estancia', order: 2 },
    ])
  })

  it('con solo una parte del reparto, cada tipo conserva su orden', () => {
    expect(detectCategories(ETL_EVENTS).categories).toEqual([
      { measureId: 'shortTermVisitorUniqueVisitors', label: 'Corta estancia', order: 2 },
    ])
  })

  it('sigue reconociendo las categorías por sufijo', () => {
    const { categories } = detectCategories(measures('peopleCount_male', 'peopleCount_female'))
    expect(categories.map((c) => c.label).sort()).toEqual(['Hombres', 'Mujeres'])
  })
})
