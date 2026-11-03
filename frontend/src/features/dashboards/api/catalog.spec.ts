import { describe, expect, it } from 'vitest'
import { datamodelOf } from '../templates/contract'
import { rankOptions, type EntityOption } from './catalog'

const option = (id: number, datamodel: string, tail: string): EntityOption => ({
  id,
  name: tail,
  urn: `urn:ngsi-ld:${datamodel}:${tail}`,
  tenant: 'demo',
  scope: '/',
  datamodel,
})

const events = datamodelOf('flowEvent')
const counts = datamodelOf('flowObserved')
const people = datamodelOf('peopleCount')

describe('rankOptions', () => {
  it('ofrece antes las entidades del modelo preferido y deja las previsiones al final', () => {
    const rows = [
      option(1, counts, 'S1_CFO'),
      option(2, events, 'S2_CFE_pred'),
      option(3, people, 'P1'),
      option(4, events, 'S2_CFE'),
      option(5, events, 'S3_CFE'),
      option(6, counts, 'S1_CFO_pred'),
    ]
    expect(rankOptions(rows, [events, counts, people]).map((r) => r.id)).toEqual([4, 5, 1, 3, 2, 6])
  })

  it('las de un modelo que la plantilla no declara van detrás de las declaradas', () => {
    const rows = [option(1, 'Other', 'X'), option(2, counts, 'S1_CFO')]
    expect(rankOptions(rows, [counts]).map((r) => r.id)).toEqual([2, 1])
  })

  it('sin modelos declarados conserva el orden del servidor', () => {
    const rows = [option(3, counts, 'A'), option(1, events, 'B'), option(2, people, 'C')]
    expect(rankOptions(rows, []).map((r) => r.id)).toEqual([3, 1, 2])
  })
})
