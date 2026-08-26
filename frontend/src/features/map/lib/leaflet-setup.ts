import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

/**
 * El plugin de agrupacion es un paquete UMD que busca Leaflet en el objeto global, y el
 * componente de mapa se monta con `use-global-leaflet` para partir de esa misma instancia.
 * Sin este puente convivirian dos copias de Leaflet y los marcadores nunca llegarian al mapa.
 */
;(globalThis as typeof globalThis & { L?: unknown }).L = L

export default L
