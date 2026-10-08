import { afterEach, describe, expect, it, vi } from 'vitest'
import { Browser, tileLayer } from 'leaflet'
import { MAX_ZOOM, tilesForTheme } from './mapConfig'

// Nivel que Leaflet pide al proveedor con el mapa en `zoom`, tras sus ajustes de retina.
function requestedZoom(isDark: boolean, zoom: number) {
  const tiles = tilesForTheme(isDark)
  const layer = tileLayer(tiles.url, tiles.options) as unknown as {
    options: { maxZoom: number; zoomOffset: number }
    _clampZoom: (zoom: number) => number
  }
  return { layerMaxZoom: layer.options.maxZoom, url: layer._clampZoom(zoom) + layer.options.zoomOffset }
}

const retina = Browser.retina

afterEach(() => {
  ;(Browser as { retina: boolean }).retina = retina
  vi.unstubAllEnvs()
})

describe.each([false, true])('tilesForTheme con retina=%s', (isRetina) => {
  it('pide teselas hasta el zoom maximo sin pasarse de el', () => {
    ;(Browser as { retina: boolean }).retina = isRetina
    expect(requestedZoom(false, MAX_ZOOM)).toEqual({ layerMaxZoom: MAX_ZOOM, url: MAX_ZOOM })
    expect(requestedZoom(true, MAX_ZOOM)).toEqual({ layerMaxZoom: MAX_ZOOM, url: MAX_ZOOM })
  })
})

describe('tilesForTheme en tema oscuro', () => {
  it('sin URL oscura reutiliza la base clara y la oscurece', () => {
    vi.stubEnv('VITE_MAP_TILES_URL_DARK', '')
    const dark = tilesForTheme(true)
    const light = tilesForTheme(false)
    expect(dark.url).toBe(light.url)
    expect(dark.attribution).toBe(light.attribution)
    expect(dark.darken).toBe(true)
    expect(light.darken).toBe(false)
  })

  it('con URL oscura propia la usa tal cual, sin filtro y con su atribucion', () => {
    vi.stubEnv('VITE_MAP_TILES_URL_DARK', 'https://tiles.example/{z}/{x}/{y}.png')
    vi.stubEnv('VITE_MAP_TILES_ATTRIBUTION_DARK', 'Ejemplo')
    expect(tilesForTheme(true)).toMatchObject({
      url: 'https://tiles.example/{z}/{x}/{y}.png',
      attribution: 'Ejemplo',
      darken: false,
    })
  })
})
