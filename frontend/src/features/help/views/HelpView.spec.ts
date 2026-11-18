import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import vuetify from '@/plugins/vuetify'
import { ApiError } from '@/api/http'

const api = vi.hoisted(() => ({ fetchManual: vi.fn() }))
vi.mock('../api/manual', () => api)

const { default: HelpView } = await import('./HelpView.vue')

const createObjectURL = vi.fn(() => 'blob:manual')
const revokeObjectURL = vi.fn()
let clickedDownload: string | null = null

beforeEach(() => {
  Object.assign(URL, { createObjectURL, revokeObjectURL })
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
    clickedDownload = this.download
  })
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.clearAllMocks()
  clickedDownload = null
  document.body.innerHTML = ''
})

async function mountHelp() {
  // La ayuda enlaza con otras pantallas; aquí basta con que esas rutas existan.
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: HelpView },
      { path: '/:other(.*)*', component: { template: '<div />' } },
    ],
  })
  const wrapper = mount(HelpView, {
    global: { plugins: [createPinia(), vuetify, router] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

const downloadButton = (wrapper: Awaited<ReturnType<typeof mountHelp>>) =>
  wrapper.findAll('button').find((b) => b.text().includes('Descargar manual (PDF)'))

describe('descargar el manual desde la ayuda', () => {
  it('descarga el PDF que sirve el backend', async () => {
    const pdf = new Blob(['%PDF-1.7'], { type: 'application/pdf' })
    api.fetchManual.mockResolvedValue(pdf)
    const wrapper = await mountHelp()

    await downloadButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(api.fetchManual).toHaveBeenCalledOnce()
    expect(createObjectURL).toHaveBeenCalledWith(pdf)
    expect(clickedDownload).toBe('manual-plataforma.pdf')
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:manual')
  })

  it('avisa de que el manual aún no está disponible cuando no se ha subido', async () => {
    api.fetchManual.mockRejectedValue(new ApiError('notFound', 'No documentation found.', 404))
    const wrapper = await mountHelp()

    await downloadButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('El manual todavía no está disponible.')
    expect(clickedDownload).toBeNull()
  })

  it('muestra el error del servidor si la descarga falla por otro motivo', async () => {
    api.fetchManual.mockRejectedValue(
      new ApiError('server', 'El servidor ha devuelto un error. Inténtalo de nuevo en unos minutos.', 500),
    )
    const wrapper = await mountHelp()

    await downloadButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('El servidor ha devuelto un error.')
  })
})
