import { describe, expect, it } from 'vitest'
import {
  fromInactivityCondition,
  fromThresholdCondition,
  toBulkInactivityCondition,
  toBulkThresholdCondition,
} from './draft'
import type { InactivityCondition, ThresholdCondition } from '../types'

const entity = {
  id: 7,
  name: 'Sensor centro',
  urn: 'urn:ngsi-ld:CrowdFlowObserved:SPT0001_CFO',
  datamodel: 'CrowdFlowObserved',
  tenant: 'pid_gijon',
  scope: '/',
}

describe('fromThresholdCondition', () => {
  it('reconstruye entidad, medida, operador y los dos extremos de un intervalo', () => {
    const condition: ThresholdCondition = {
      id: 12,
      entity,
      measure: { id: 'r_cfo_countm', name: 'Personas' },
      condition: 'between',
      threshold: [10, 20],
      period: null,
    }

    const draft = fromThresholdCondition(condition)

    expect(draft.id).toBe(12)
    expect(draft.entity).toMatchObject({ id: 7, urn: entity.urn, tenant: 'pid_gijon', scope: '/' })
    expect(draft.measure).toEqual({ id: 'r_cfo_countm', name: 'Personas' })
    expect(draft.operator).toBe('between')
    expect(draft.from).toBe('10')
    expect(draft.to).toBe('20')
  })

  it('un operador de un solo valor deja el segundo extremo vacio', () => {
    const condition: ThresholdCondition = {
      entity,
      measure: { id: 'r_cfo_countm', name: 'Personas' },
      condition: 'gt',
      threshold: [5],
    }

    const draft = fromThresholdCondition(condition)

    expect(draft.from).toBe('5')
    expect(draft.to).toBe('')
    expect(draft.id).toBeUndefined()
  })

  it('conserva la restriccion horaria que el formulario no edita', () => {
    const period = [{ week_days: [1, 2, 3], hours: [['08:00', '20:00']] }]
    const condition: ThresholdCondition = {
      id: 1,
      entity,
      measure: { id: 'm', name: 'M' },
      condition: 'gt',
      threshold: [1],
      period,
    }

    expect(fromThresholdCondition(condition).period).toEqual(period)
  })
})

describe('toBulkThresholdCondition', () => {
  it('produce la forma anidada y mantiene el id al editar una condicion existente', () => {
    const draft = fromThresholdCondition({
      id: 3,
      entity,
      measure: { id: 'm', name: 'M' },
      condition: 'between',
      threshold: [1, 2],
      period: null,
    })

    expect(toBulkThresholdCondition(draft)).toEqual({
      id: 3,
      entity: { id: 7 },
      measure: { id: 'm' },
      condition: 'between',
      threshold: [1, 2],
      period: null,
    })
  })

  it('no incluye id cuando la condicion es nueva', () => {
    const draft = fromThresholdCondition({
      entity,
      measure: { id: 'm', name: 'M' },
      condition: 'gt',
      threshold: [9],
    })

    const bulk = toBulkThresholdCondition(draft)
    expect('id' in bulk).toBe(false)
    expect(bulk.threshold).toEqual([9])
  })
})

describe('fromInactivityCondition', () => {
  it('elige la mayor unidad exacta para el plazo', () => {
    expect(fromInactivityCondition(inactivity(86_400))).toMatchObject({ timeout: '1', timeoutUnit: 86_400 })
    expect(fromInactivityCondition(inactivity(7_200))).toMatchObject({ timeout: '2', timeoutUnit: 3_600 })
    expect(fromInactivityCondition(inactivity(300))).toMatchObject({ timeout: '5', timeoutUnit: 60 })
  })

  it('cuando no hay unidad exacta cae a minutos con valor fraccionario', () => {
    expect(fromInactivityCondition(inactivity(90))).toMatchObject({ timeout: '1.5', timeoutUnit: 60 })
  })

  it('un plazo de cero deja el campo vacio', () => {
    expect(fromInactivityCondition(inactivity(0)).timeout).toBe('')
  })
})

describe('toBulkInactivityCondition', () => {
  it('manda la medida como cadena cuando la hay', () => {
    const draft = fromInactivityCondition({ id: 4, entity, measure: { id: 'm', name: 'M' }, timeoutS: 600 })
    expect(toBulkInactivityCondition(draft)).toEqual({
      id: 4,
      entity: { id: 7 },
      measure: 'm',
      timeoutS: 600,
    })
  })

  it('sin medida manda null y sin id no lo incluye', () => {
    const draft = fromInactivityCondition({ entity, timeoutS: 120 })
    const bulk = toBulkInactivityCondition(draft)
    expect(bulk.measure).toBeNull()
    expect('id' in bulk).toBe(false)
  })
})

function inactivity(timeoutS: number): InactivityCondition {
  return { entity, measure: { id: 'm', name: 'M' }, timeoutS }
}
