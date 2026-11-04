import { describe, expect, it } from 'vitest'
import { datamodelOf } from './contract'
import { TEMPLATES, datamodelNames } from './registry'

describe('modelos de datos de las plantillas de aforo', () => {
  it('las cuatro sugieren primero la entidad de eventos de la ETL y siguen admitiendo los conteos', () => {
    for (const key of ['occupancy', 'classification', 'classificationAdvanced', 'heatmap'] as const) {
      expect(datamodelNames(TEMPLATES[key])[0]).toBe(datamodelOf('flowEvent'))
      expect(datamodelNames(TEMPLATES[key])).toContain(datamodelOf('flowObserved'))
    }
  })
})
