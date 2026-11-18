import { describe, expect, it } from 'vitest'
import type { Measure } from '@/types'
import { categoryItemsFor, categoryOptions, detectCategories, pickMeasure, type CategoryOption } from './discovery'

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

// Lo que publican en pre los Smart Spot de los cuadros de clasificacion (`<serie>_CFO`).
const SMART_SPOT = measures(
  'count',
  'occupancy',
  'peopleCount',
  'peopleCountCommuter',
  'peopleCountLongInterval',
  'peopleCountMediumInterval',
  'peopleCountResident',
  'peopleCountShortInterval',
  'peopleCountTourist',
  'peopleCountVisitor',
)

// Y las entidades de eventos de la ETL de un sensor con recorridos (`<serie>_CFE`), entera.
const ETL_EVENTS_FULL = [
  ...ETL_EVENTS,
  ...measures(
    'latitude',
    'longitude',
    'minimumVisitDuration',
    'maximumVisitDuration',
    'minimumTransitDuration',
    'maximumTransitDuration',
    'shortTermVisitorCount',
    'shortTermVisitorAverageVisitDuration',
    'shortTermVisitorMaximumVisitDuration',
    'shortTermVisitorMinimumTransitDuration',
    'uniqueVisitorsBiweekly',
    'uniqueVisitorsMonthly',
  ),
]

const values = (options: { value: string }[]) => options.map((o) => o.value).sort()
const grouped = (options: CategoryOption[]) => options.filter((o) => !o.family.startsWith('alone:'))
const alone = (options: CategoryOption[]) => options.filter((o) => o.family.startsWith('alone:'))

describe('categoryOptions', () => {
  it('en los Smart Spot junta el reparto por tipo de visitante; totales y ventanas van solos; la ocupación no', () => {
    const options = categoryOptions(SMART_SPOT)
    expect(values(grouped(options))).toEqual([
      'peopleCountCommuter',
      'peopleCountResident',
      'peopleCountTourist',
      'peopleCountVisitor',
    ])
    expect(values(alone(options))).toEqual([
      'count',
      'peopleCount',
      'peopleCountLongInterval',
      'peopleCountMediumInterval',
      'peopleCountShortInterval',
    ])
    expect(values(options)).not.toContain('occupancy')
  })

  it('en la ETL junta los recuentos por tipo de visitante y deja fuera duraciones y coordenadas', () => {
    const options = categoryOptions(ETL_EVENTS_FULL)
    expect(values(grouped(options))).toEqual([
      'residentCount',
      'shortTermVisitorCount',
      'shortTermVisitorUniqueVisitors',
      'shortTermVisitorVisits',
      'touristCount',
    ])
    expect(values(alone(options))).toEqual(
      [
        'count',
        'newResidentUniqueVisitorsBiweekly',
        'newResidentUniqueVisitorsDaily',
        'newResidentUniqueVisitorsMonthly',
        'newTouristUniqueVisitorsBiweekly',
        'newTouristUniqueVisitorsDaily',
        'newTouristUniqueVisitorsMonthly',
        'newUniqueVisitorsDaily',
        'uniqueVisitors',
        'uniqueVisitorsBiweekly',
        'uniqueVisitorsDaily',
        'uniqueVisitorsMonthly',
        'visits',
      ].sort(),
    )
    for (const id of ['latitude', 'longitude', 'averageVisitDuration', 'maximumVisitDuration', 'shortTermVisitorAverageVisitDuration']) {
      expect(values(options)).not.toContain(id)
    }
  })

  it('agrupa cada parte con las de su mismo total, y cada recuento suelto aparte', () => {
    const family = (id: string) => categoryOptions(ETL_EVENTS_FULL).find((o) => o.value === id)?.family
    expect(family('touristCount')).toBe(family('shortTermVisitorCount'))
    expect(family('touristCount')).not.toBe(family('shortTermVisitorVisits'))
    expect(family('shortTermVisitorVisits')).not.toBe(family('shortTermVisitorUniqueVisitors'))
    expect(family('uniqueVisitorsDaily')).not.toBe(family('uniqueVisitorsMonthly'))
  })

  it('pone primero los repartos y después lo que va solo', () => {
    const options = categoryOptions(SMART_SPOT)
    const firstAlone = options.findIndex((o) => o.family.startsWith('alone:'))
    expect(options.slice(firstAlone).every((o) => o.family.startsWith('alone:'))).toBe(true)
  })

  it('en el LIDAR reparte por clase; las métricas de una clase no son un reparto', () => {
    const lidar = measures(
      'totalCount',
      'adultCount',
      'vehicleCount',
      'adultEntered',
      'vehicleEntered',
      'adultConcurrentMax',
      'adultStayAvg',
      'adultSpeedAvg',
    )
    const options = categoryOptions(lidar)
    expect(values(grouped(options))).toEqual(['adultCount', 'adultEntered', 'vehicleCount', 'vehicleEntered'])
    expect(values(alone(options))).toEqual(['totalCount'])
    expect(categoryItemsFor(options, ['adultCount']).map((o) => o.value)).toEqual(['adultCount', 'vehicleCount'])
  })

  it('un reparto por sufijo de algo que no se cuenta no se ofrece', () => {
    expect(categoryOptions(measures('dwellTime_male', 'dwellTime_female'))).toEqual([])
    expect(values(categoryOptions(measures('peopleCount_male', 'peopleCount_female')))).toEqual([
      'peopleCount_female',
      'peopleCount_male',
    ])
  })

  it('usa el nombre y las unidades de la medida', () => {
    const [option] = categoryOptions([
      { id: 'touristCount', name: 'Recuento (turistas)', units: 'personas', value_type: 'double', value: 1 } as unknown as Measure,
    ])
    expect(option.title).toBe('Recuento (turistas) (personas)')
  })
})

describe('categoryItemsFor', () => {
  const options = categoryOptions(ETL_EVENTS_FULL)

  it('sin nada elegido ofrece todas', () => {
    expect(categoryItemsFor(options, [])).toEqual(options)
  })

  it('con algo elegido deja solo las partes de su mismo total', () => {
    expect(values(categoryItemsFor(options, ['touristCount']))).toEqual([
      'residentCount',
      'shortTermVisitorCount',
      'touristCount',
    ])
  })

  it('un recuento suelto se elige solo: no se junta con nada', () => {
    const smartSpot = categoryOptions(SMART_SPOT)
    expect(values(categoryItemsFor(smartSpot, ['peopleCountLongInterval']))).toEqual(['peopleCountLongInterval'])
    expect(values(categoryItemsFor(options, ['uniqueVisitorsDaily']))).toEqual(['uniqueVisitorsDaily'])
    expect(values(categoryItemsFor(options, ['count']))).toEqual(['count'])
  })

  it('una elección que ya no se ofrece no restringe nada', () => {
    expect(categoryItemsFor(options, ['maximumVisitDuration'])).toEqual(options)
  })
})
