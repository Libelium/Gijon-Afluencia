import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { VSelect, VTextField } from 'vuetify/components'
import vuetify from '@/plugins/vuetify'
import RangeSelector from './RangeSelector.vue'

function mountSelector(props: Record<string, unknown>) {
  return mount(RangeSelector, { props: { preset: '24h', timeZone: 'Europe/Madrid', ...props }, global: { plugins: [vuetify] } })
}

// VSelect lleva dentro su propio VTextField: los de fecha son los de `type="date"`.
const dateFields = (wrapper: ReturnType<typeof mountSelector>) =>
  wrapper.findAllComponents(VTextField).filter((field) => field.props('type') === 'date')

const values = (wrapper: ReturnType<typeof mountSelector>) =>
  (wrapper.findComponent(VSelect).props('items') as { value: string }[]).map((item) => item.value)

describe('RangeSelector', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-10-27T12:30:00Z'))
  })
  afterEach(() => vi.useRealTimers())

  it('sin v-model:custom solo ofrece los preajustes', () => {
    expect(values(mountSelector({}))).not.toContain('custom')
  })

  it('con v-model:custom ofrece «Personalizado» y parte de la ventana que se esta viendo', async () => {
    const wrapper = mountSelector({ preset: '7d', custom: null })
    expect(values(wrapper)).toContain('custom')

    await wrapper.findComponent(VSelect).vm.$emit('update:modelValue', 'custom')

    expect(dateFields(wrapper).map((field) => field.props('modelValue'))).toEqual(['2026-10-20', '2026-10-27'])
    expect(wrapper.emitted('update:custom')?.at(-1)).toEqual([
      { start: '2026-10-19T22:00:00Z', end: '2026-10-27T23:00:00Z' },
    ])
  })

  it('al volver a un preajuste borra el rango personalizado', async () => {
    const wrapper = mountSelector({ custom: { start: '2026-10-19T22:00:00Z', end: '2026-10-27T23:00:00Z' } })
    expect(wrapper.findComponent(VSelect).props('modelValue')).toBe('custom')

    await wrapper.findComponent(VSelect).vm.$emit('update:modelValue', '30d')

    expect(wrapper.emitted('update:custom')?.at(-1)).toEqual([null])
    expect(wrapper.emitted('update:preset')?.at(-1)).toEqual(['30d'])
    expect(dateFields(wrapper)).toHaveLength(0)
  })

  it('si el padre borra el rango vuelve al preajuste', async () => {
    const wrapper = mountSelector({ custom: { start: '2026-10-19T22:00:00Z', end: '2026-10-27T23:00:00Z' } })
    await wrapper.setProps({ custom: null })
    expect(wrapper.findComponent(VSelect).props('modelValue')).toBe('24h')
    expect(dateFields(wrapper)).toHaveLength(0)
  })

  it('un rango al reves avisa y no se emite', async () => {
    const wrapper = mountSelector({ custom: { start: '2026-10-19T22:00:00Z', end: '2026-10-27T23:00:00Z' } })
    const emitted = wrapper.emitted('update:custom')?.length ?? 0

    await dateFields(wrapper)[0].vm.$emit('update:modelValue', '2026-11-01')

    expect(wrapper.emitted('update:custom')?.length ?? 0).toBe(emitted)
    expect(wrapper.text()).toContain('no puede pasar de 366 días')
  })
})
