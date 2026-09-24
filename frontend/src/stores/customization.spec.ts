import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ApiError } from '@/api/http'

// Solo se sustituyen las llamadas de red: `pickCustomization` es logica y se usa la real.
vi.mock('@/api/organization', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/organization')>()),
  getPreferences: vi.fn(),
  getPublicPreferences: vi.fn(),
}))

import { getPreferences, getPublicPreferences } from '@/api/organization'
import { useCustomizationStore } from './customization'

const FOOTER = '<p>Financiado por la Unión Europea</p>'

describe('carga de la personalizacion', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(getPreferences).mockReset()
    vi.mocked(getPublicPreferences).mockReset()
  })

  it('usa las preferencias de la organizacion cuando se pueden leer', async () => {
    vi.mocked(getPreferences).mockResolvedValue({ themeCustomFooter: FOOTER })

    const store = useCustomizationStore()
    await store.load(1)

    expect(store.footerHtml).toBe(FOOTER)
    expect(getPublicPreferences).not.toHaveBeenCalled()
  })

  /** Un usuario que no administra no puede leerlas: sin el respaldo se quedaba sin colores ni pie. */
  it('sin permiso sobre la organizacion recurre a las publicas', async () => {
    vi.mocked(getPreferences).mockRejectedValue(new ApiError('forbidden', 'no', 403))
    vi.mocked(getPublicPreferences).mockResolvedValue({ themeCustomFooter: FOOTER })

    const store = useCustomizationStore()
    await store.load(1)

    expect(getPublicPreferences).toHaveBeenCalledWith(1)
    expect(store.footerHtml).toBe(FOOTER)
  })

  it('cualquier otro fallo se propaga', async () => {
    vi.mocked(getPreferences).mockRejectedValue(new ApiError('server', 'boom', 500))

    await expect(useCustomizationStore().load(1)).rejects.toBeInstanceOf(ApiError)
    expect(getPublicPreferences).not.toHaveBeenCalled()
  })
})
