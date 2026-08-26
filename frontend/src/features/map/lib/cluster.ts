// El orden importa: `leaflet-setup` deja Leaflet en el global antes de evaluar el plugin.
import L from './leaflet-setup'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import type { DivIcon, MarkerCluster, MarkerClusterGroup } from 'leaflet'
import { formatNumber } from '@/lib/format'

/**
 * Tres tamaños de globo para que la densidad se lea de un vistazo. El texto usa las clases
 * tipograficas de la aplicacion —el HTML del globo lo genera Leaflet, pero las utilidades
 * son globales— de modo que aqui no hay ningun tamaño de letra suelto.
 */
const TIERS = [
  { max: 10, size: 34, name: 'sm', text: 'text-caption font-weight-bold' },
  { max: 100, size: 42, name: 'md', text: 'text-body-2 font-weight-bold' },
  { max: Infinity, size: 50, name: 'lg', text: 'text-body-2 font-weight-bold' },
] as const

function tierFor(count: number): (typeof TIERS)[number] {
  return TIERS.find((tier) => count < tier.max) ?? TIERS[TIERS.length - 1]
}

/**
 * Solo se cargan los estilos de animacion del plugin: el aspecto de los globos se genera
 * aqui con las clases del componente para que siga la paleta de la aplicacion.
 */
function clusterIcon(cluster: MarkerCluster): DivIcon {
  const count = cluster.getChildCount()
  const tier = tierFor(count)
  return L.divIcon({
    html: `<span class="${tier.text}">${formatNumber(count)}</span>`,
    className: `entity-cluster entity-cluster--${tier.name}`,
    iconSize: [tier.size, tier.size],
  })
}

export function createClusterGroup(): MarkerClusterGroup {
  return L.markerClusterGroup({
    maxClusterRadius: 56,
    showCoverageOnHover: false,
    spiderfyOnMaxZoom: true,
    removeOutsideVisibleBounds: true,
    iconCreateFunction: clusterIcon,
  })
}

/**
 * Punto individual: un circulo sobrio, sin depender de las imagenes del paquete.
 * Se declara como Icon porque el tipado del envoltorio de Vue exige esa firma,
 * aunque Leaflet acepta cualquier DivIcon.
 */
export function createEntityIcon(): L.Icon {
  const icon: DivIcon = L.divIcon({
    html: '<span class="entity-marker__dot"></span>',
    className: 'entity-marker',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -11],
  })
  return icon as unknown as L.Icon
}
