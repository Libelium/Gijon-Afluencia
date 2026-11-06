import { describe, expect, it } from 'vitest'
import { localizeMeasure, measureInfo, measureName, measureValueLabel } from './measureCatalog'

describe('measureInfo', () => {
  it('traduce sin distinguir mayusculas, y solo describe lo que no se explica solo', () => {
    expect(measureInfo('latitude')).toEqual({ name: 'Latitud' })
    expect(measureInfo('predictedOccupancy')?.name).toBe('Ocupación prevista')
    expect(measureInfo('PREDICTEDOCCUPANCY')?.description).toMatch(/a la vez/)
  })

  it('un campo en bruto del Smart Spot se traduce como su nombre del datamodel', () => {
    expect(measureInfo('r_cfo_countm')).toEqual(measureInfo('peopleCountMediumInterval'))
  })

  it('compone grupo de visitante y metrica, y anade como se clasifica el grupo', () => {
    const info = measureInfo('touristaverageVisitDuration')
    expect(info?.name).toBe('Duración media de la visita (turistas)')
    expect(info?.description).toMatch(/en segundos\. Turistas: vistos 1 o 2 días/)
    // Las ETL escriben el mismo atributo con mayusculas distintas.
    expect(measureInfo('shortTermVisitorAverageVisitDuration')?.name).toBe(
      'Duración media de la visita (corta estancia)',
    )
    expect(measureInfo('residentcount')?.name).toBe('Recuento (residentes)')
  })

  it('compone el periodo, tambien detras de un grupo puesto tras `new`', () => {
    expect(measureInfo('uniqueVisitorsBiweekly')?.name).toBe('Visitantes únicos (quincenal)')
    expect(measureInfo('newUniqueVisitorsWeekly')?.name).toBe('Visitantes únicos nuevos (semanal)')
    expect(measureInfo('newResidentUniqueVisitorsMonthly')?.name).toBe('Residentes nuevos (mensual)')
    expect(measureInfo('newTouristUniqueVisitorsDaily')?.name).toBe('Turistas nuevos (diario)')
  })

  it('las metricas del LIDAR llevan la etiqueta salvo en el total', () => {
    expect(measureInfo('totalConcurrentMax')?.name).toBe('Máximo a la vez')
    expect(measureInfo('adultCount')?.name).toBe('Objetos detectados (adultos)')
    expect(measureInfo('vehicleStayP90')?.description).toMatch(/en segundos/)
  })

  it('lo que no conoce lo deja sin traducir', () => {
    expect(measureInfo('peopleCountCommuter')).toBeNull()
    expect(measureInfo('daily')).toBeNull()
    expect(measureInfo('touristSomethingElse')).toBeNull()
    expect(measureInfo('')).toBeNull()
  })
})

describe('measureName', () => {
  it('usa el nombre que tenga si la medida no esta en el catalogo', () => {
    expect(measureName('visits')).toBe('Visitas')
    expect(measureName('mystery', 'Mystery')).toBe('Mystery')
    expect(measureName('mystery')).toBe('mystery')
  })
})

describe('localizeMeasure', () => {
  it('conserva el nombre del servidor para las heuristicas en ingles', () => {
    expect(localizeMeasure({ id: 'r_cfo_countm', name: 'People count medium', units: 'u' })).toEqual({
      id: 'r_cfo_countm',
      name: 'Dispositivos detectados (intervalo medio)',
      sourceName: 'People count medium',
      description: expect.stringMatching(/de 2 a 5 minutos/),
      units: 'u',
    })
    expect(localizeMeasure({ id: 'mystery', name: 'Mystery' })).toEqual({
      id: 'mystery',
      name: 'Mystery',
      sourceName: 'Mystery',
    })
  })
})

describe('measureValueLabel', () => {
  it('traduce los valores fijos que publica la fusion, y deja el resto tal cual', () => {
    expect(measureValueLabel('case', 'lidar_only')).toBe('Solo LIDAR')
    expect(measureValueLabel('confidence', ' Estimated ')).toBe('Estimada con WiFi/BLE')
    expect(measureValueLabel('confidence', 'otra cosa')).toBeNull()
    expect(measureValueLabel('name', 'mixed')).toBeNull()
    expect(measureValueLabel('case', 3)).toBeNull()
    // Lo que publica pre con otros nombres: rotulos genericos, valen para zona y prevision.
    expect(measureValueLabel('confidenceLevel', 'estimated')).toBe('Estimada')
    expect(measureValueLabel('caseType', 'mixed')).toBe('Mixta')
  })
})
