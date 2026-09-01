import { afterEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import vuetify from '@/plugins/vuetify'
import AppShell from './AppShell.vue'

/**
 * Verificacion del enlace de salto al contenido (WCAG 2.4.1, hallazgo GDTIS-PT01-ACC-003).
 *
 * Lo que hace util a un enlace de salto no es existir, sino tres cosas concretas: ser el PRIMER
 * elemento del recorrido de teclado, apuntar a algo que existe, y mover el foco de verdad al
 * activarlo. Un enlace de salto que no hace lo tercero se ve bien en una revision de codigo y no
 * sirve de nada al usarlo, asi que se comprueba en el DOM.
 */

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div>contenido</div>' } }],
})

async function mountShell() {
  router.push('/')
  await router.isReady()
  const wrapper = mount(AppShell, {
    global: { plugins: [createPinia(), vuetify, router] },
    attachTo: document.body,
  })
  await nextTick()
  return wrapper
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('enlace de salto al contenido', () => {
  it('es el primer elemento enfocable de la pagina', async () => {
    const wrapper = await mountShell()

    const root = wrapper.element as HTMLElement
    const focusable = Array.from(
      root.querySelectorAll('a[href], button, [tabindex]:not([tabindex="-1"]), input, select'),
    ) as HTMLElement[]
    expect(focusable.length).toBeGreaterThan(1)
    expect(focusable[0].textContent).toContain('Saltar al contenido principal')

    wrapper.unmount()
  })

  it('apunta a un elemento que existe y es enfocable por programa', async () => {
    const wrapper = await mountShell()

    const link = wrapper.find('a.skip-link')
    const target = link.attributes('href')?.replace('#', '') ?? ''
    const main = (wrapper.element as HTMLElement).querySelector(`#${target}`)

    expect(main, 'el destino del enlace de salto debe existir').not.toBeNull()
    // `-1` lo hace enfocable por programa sin meterlo en el recorrido de tabulacion.
    expect(main?.getAttribute('tabindex')).toBe('-1')

    wrapper.unmount()
  })

  it('al activarlo el foco pasa al contenido, y no solo cambia la URL', async () => {
    const wrapper = await mountShell()
    const before = router.currentRoute.value.fullPath

    await wrapper.find('a.skip-link').trigger('click')

    const main = (wrapper.element as HTMLElement).querySelector('#contenido-principal')
    expect(document.activeElement).toBe(main)
    // El salto no debe dejar el ancla pegada a la ruta: el enrutador usa historial.
    expect(router.currentRoute.value.fullPath).toBe(before)

    wrapper.unmount()
  })
})
