import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import vuetify from '@/plugins/vuetify'
import { useChartHeight } from '../charts/expanded'
import ExpandButton from './ExpandButton.vue'
import ExpandFrame from './ExpandFrame.vue'

/** Grafica de prueba: rotula el alto que le toca. */
const Probe = defineComponent({
  setup() {
    const height = useChartHeight(() => 280)
    return () => h('span', { class: 'probe' }, String(height.value))
  },
})

function mountFrame() {
  return mount(ExpandFrame, {
    props: { label: 'Ocupación' },
    slots: {
      default: ({ expanded, toggle }: { expanded: boolean; toggle: () => void }) => [
        h(ExpandButton, { expanded, onToggle: toggle }),
        h(Probe),
      ],
    },
    attachTo: document.body,
    global: { plugins: [vuetify] },
  })
}

describe('ExpandFrame', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    document.documentElement.classList.remove('expand-frame-open')
  })

  it('amplia la tarjeta como dialogo, agranda sus graficas y Escape la devuelve con el foco al boton', async () => {
    window.innerHeight = 1000
    const wrapper = mountFrame()
    const button = () => document.body.querySelector<HTMLButtonElement>('button')!
    expect(document.body.querySelector('.probe')?.textContent).toBe('280')

    button().focus()
    button().click()
    await nextTick()
    await nextTick()

    const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')
    expect(dialog?.getAttribute('aria-label')).toBe('Ocupación')
    expect(dialog?.getAttribute('aria-modal')).toBe('true')
    expect(button().getAttribute('aria-label')).toBe('Volver al tamaño normal')
    expect(Number(document.body.querySelector('.probe')?.textContent)).toBeGreaterThan(280)
    expect(document.documentElement.classList.contains('expand-frame-open')).toBe(true)

    dialog!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await nextTick()
    await nextTick()

    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(document.body.querySelector('.probe')?.textContent).toBe('280')
    expect(document.documentElement.classList.contains('expand-frame-open')).toBe(false)
    expect(document.activeElement).toBe(button())
    wrapper.unmount()
  })
})
