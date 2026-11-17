import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import { localizeMeasure } from '@/lib/measureCatalog'
import MeasureExplanation from './MeasureExplanation.vue'

const text = (id: string, name = id) =>
  mount(MeasureExplanation, { props: { measure: localizeMeasure({ id, name }) }, global: { plugins: [vuetify] } }).text()

describe('MeasureExplanation', () => {
  it('explica la medida y cómo se calcula, sin mostrar la variable', () => {
    const shown = text('visits', 'Visits')
    expect(shown).toContain('Visitas')
    expect(shown).toContain('Cómo se calcula:')
    expect(shown).not.toContain('visits')
  })

  it('una autodescriptiva lleva descripción pero no cálculo', () => {
    const shown = text('latitude')
    expect(shown).toContain('norte-sur')
    expect(shown).not.toContain('Cómo se calcula')
  })

  it('una medida desconocida lo dice y da la variable, que es lo único que hay', () => {
    expect(text('mystery', 'Mystery')).toContain('Sin descripción en la plataforma. Variable: mystery')
  })
})
