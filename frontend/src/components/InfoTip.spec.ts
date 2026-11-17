import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import InfoTip from './InfoTip.vue'

describe('InfoTip', () => {
  it('es un botón con nombre accesible, al que se llega con el teclado', () => {
    const wrapper = mount(InfoTip, { props: { label: 'Información sobre Visitas' }, global: { plugins: [vuetify] } })
    const button = wrapper.find('button')
    expect(button.exists()).toBe(true)
    expect(button.attributes('aria-label')).toBe('Información sobre Visitas')
  })

  it('pulsarlo no navega: no pasa el clic a la fila que lo contiene', async () => {
    const onRow = vi.fn()
    const Row = defineComponent(() => () => h('div', { onClick: onRow }, [h(InfoTip, { label: 'i' })]))
    const wrapper = mount(Row, { global: { plugins: [vuetify] } })
    await wrapper.find('button').trigger('click')
    expect(onRow).not.toHaveBeenCalled()
  })
})
