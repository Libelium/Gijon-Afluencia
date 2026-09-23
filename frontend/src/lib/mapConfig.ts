import { env, envNumber } from './env'

/**
 * Configuracion de cartografia en un solo sitio, leida con `env()` para que se pueda cambiar
 * en el despliegue sin reconstruir la imagen. Ningun proveedor por defecto exige credencial:
 * la aplicacion tiene que poder mostrar el mapa sin secretos.
 */
const DEFAULT_TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const DEFAULT_ATTRIBUTION = '&copy; colaboradores de OpenStreetMap'

/**
 * Base propia para el tema oscuro, no la clara invertida por CSS: invertir una base clara
 * invierte tambien sus etiquetas y su contraste queda por debajo del minimo exigido.
 */
const DEFAULT_TILES_DARK =
  'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
const DEFAULT_ATTRIBUTION_DARK = 'Esri, HERE, Garmin, &copy; colaboradores de OpenStreetMap'

export const tilesUrl = (): string => env('VITE_MAP_TILES_URL', DEFAULT_TILES)

export const tilesUrlDark = (): string => env('VITE_MAP_TILES_URL_DARK', DEFAULT_TILES_DARK)

/** La atribucion es obligatoria por los terminos de uso del proveedor de teselas. */
export const tilesAttribution = (): string => env('VITE_MAP_TILES_ATTRIBUTION', DEFAULT_ATTRIBUTION)

export const tilesAttributionDark = (): string =>
  env('VITE_MAP_TILES_ATTRIBUTION_DARK', DEFAULT_ATTRIBUTION_DARK)

/** La URL y la atribucion que corresponden al tema en uso. */
export function tilesForTheme(isDark: boolean): { url: string; attribution: string } {
  return isDark
    ? { url: tilesUrlDark(), attribution: tilesAttributionDark() }
    : { url: tilesUrl(), attribution: tilesAttribution() }
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
