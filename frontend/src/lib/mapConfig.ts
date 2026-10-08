import { Browser } from 'leaflet'
import { env, envNumber } from './env'

/**
 * Configuracion de cartografia en un solo sitio, leida con `env()` para que se pueda cambiar
 * en el despliegue sin reconstruir la imagen. Ningun proveedor por defecto exige credencial:
 * la aplicacion tiene que poder mostrar el mapa sin secretos.
 */
const DEFAULT_TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const DEFAULT_ATTRIBUTION = '&copy; colaboradores de OpenStreetMap'

export const MAX_ZOOM = 19

export const tilesUrl = (): string => env('VITE_MAP_TILES_URL', DEFAULT_TILES)

// Vacia por defecto: el tema oscuro reutiliza la base clara con el filtro `.map-tiles--dark` (app.scss).
export const tilesUrlDark = (): string => env('VITE_MAP_TILES_URL_DARK')

/** La atribucion es obligatoria por los terminos de uso del proveedor de teselas. */
export const tilesAttribution = (): string => env('VITE_MAP_TILES_ATTRIBUTION', DEFAULT_ATTRIBUTION)

export const tilesAttributionDark = (): string => env('VITE_MAP_TILES_ATTRIBUTION_DARK')

export interface TileLayerConfig {
  url: string
  attribution: string
  /** La capa es la clara y hay que oscurecerla con la clase `map-tiles--dark`. */
  darken: boolean
  options: { maxZoom: number; maxNativeZoom: number; detectRetina: boolean }
}

/** La URL, la atribucion y las opciones de capa que corresponden al tema en uso. */
export function tilesForTheme(isDark: boolean): TileLayerConfig {
  const darkUrl = isDark ? tilesUrlDark() : ''
  // En retina `detectRetina` resta 1 al maxZoom de la capa y suma 1 al nivel pedido, pero no corrige
  // maxNativeZoom: sin compensarlo la capa se vaciaria en el zoom maximo y pediria niveles inexistentes.
  const retina = Browser.retina ? 1 : 0
  return {
    url: darkUrl || tilesUrl(),
    attribution: darkUrl ? tilesAttributionDark() : tilesAttribution(),
    darken: isDark && !darkUrl,
    options: { maxZoom: MAX_ZOOM + retina, maxNativeZoom: MAX_ZOOM - retina, detectRetina: true },
  }
}

export const defaultZoom = (): number => envNumber('VITE_MAP_DEFAULT_ZOOM', 13)

/** Centro por defecto, en formato "lat,lon". Si viene mal formado se usa el de reserva. */
export function defaultCenter(): [number, number] {
  const fallback: [number, number] = [43.5322, -5.6611]
  const raw = env('VITE_MAP_DEFAULT_CENTER')
  if (!raw) return fallback
  const parts = raw.split(',').map((p) => Number(p.trim()))
  if (parts.length !== 2 || !parts.every((n) => Number.isFinite(n))) return fallback
  const [lat, lon] = parts
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return fallback
  return [lat, lon]
}
