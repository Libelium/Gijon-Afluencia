import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import ConfidenceChip from './ConfidenceChip.vue'

const text = (value: unknown) => mount(ConfidenceChip, { props: { value }, global: { plugins: [vuetify] } }).text()

describe('ConfidenceChip', () => {
  it('rotula como se obtuvo la cifra, que es lo que publica la fusion', () => {
    expect(text('measured')).toBe('Medida')
    expect(text('estimated_uncalibrated')).toBe('Estimada sin calibrar')
  })

  it('sigue entendiendo grados y proporciones', () => {
    expect(text('high')).toBe('Alta')
    expect(text(0.5)).toBe('50 %')
  })
})
