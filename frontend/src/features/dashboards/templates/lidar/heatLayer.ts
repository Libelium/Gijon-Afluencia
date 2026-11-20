import { DomUtil, type LatLngExpression, type Map as LeafletMap } from 'leaflet'
import { renderHeat, type HeatZone } from './heatField'

/** Zona que pinta la capa: contorno [lat, lon] y proporcion de aforo. */
export interface HeatSource {
  polygon: [number, number][]
  value: number
}

/** Metros que se difumina cada zona por fuera de su contorno. */
const FADE_METERS = 25
/** Metros hacia dentro en que empieza el difuminado: disimula la forma exacta del contorno. */
const INNER_METERS = 8
/** Desenfoque final de toda la capa, en metros: redondea picos y entrantes del contorno. */
const BLUR_METERS = 4
/** Pixeles de pantalla por celda calculada: el navegador suaviza al ampliar la imagen. */
const CELL = 4
const PANE = 'zoneHeat'

function metersPerPixel(map: LeafletMap): number {
  const lat = map.getCenter().lat
  return (40_075_016.686 * Math.cos((lat * Math.PI) / 180)) / 2 ** (map.getZoom() + 8)
}

/**
 * Capa de calor sobre las teselas y bajo los contornos y los dispositivos. Se vuelve a calcular al
 * terminar cada movimiento o zoom; durante la animacion se oculta para no verse desplazada.
 */
export function createHeatLayer(map: LeafletMap) {
  const pane = map.getPane(PANE) ?? map.createPane(PANE)
  pane.style.zIndex = '350'
  pane.style.pointerEvents = 'none'

  const canvas = DomUtil.create('canvas', 'zone-heat') as HTMLCanvasElement
  canvas.setAttribute('aria-hidden', 'true')
  pane.appendChild(canvas)
  const scratch = document.createElement('canvas')
  let sources: HeatSource[] = []
  let frame = 0

  function draw() {
    const size = map.getSize()
    DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]))
    canvas.width = size.x
    canvas.height = size.y
    canvas.style.visibility = 'visible'
    const context = canvas.getContext('2d')
    const scratchContext = scratch.getContext('2d')
    if (!context || !scratchContext || !sources.length) return

    const zones: HeatZone[] = sources.map((source) => ({
      value: source.value,
      ring: source.polygon.map((point) => {
        const p = map.latLngToContainerPoint(point as LatLngExpression)
        return [p.x, p.y] as [number, number]
      }),
    }))
    const width = Math.ceil(size.x / CELL)
    const height = Math.ceil(size.y / CELL)
    const pixel = metersPerPixel(map)
    const fade = FADE_METERS / pixel
    scratch.width = width
    scratch.height = height
    const image = scratchContext.createImageData(width, height)
    image.data.set(renderHeat(zones, width, height, CELL, fade, INNER_METERS / pixel))
    scratchContext.putImageData(image, 0, 0)
    context.imageSmoothingEnabled = true
    // Sin soporte de `filter` (navegadores antiguos) se pinta igual, solo que sin desenfocar.
    context.filter = `blur(${Math.max(1, BLUR_METERS / pixel).toFixed(1)}px)`
    context.drawImage(scratch, 0, 0, size.x, size.y)
    context.filter = 'none'
  }

  function schedule() {
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(draw)
  }

  function hide() {
    canvas.style.visibility = 'hidden'
  }

  map.on('moveend zoomend resize viewreset', schedule)
  map.on('zoomstart', hide)
  schedule()

  return {
    update(next: HeatSource[]) {
      sources = next
      schedule()
    },
    remove() {
      cancelAnimationFrame(frame)
      map.off('moveend zoomend resize viewreset', schedule)
      map.off('zoomstart', hide)
      canvas.remove()
    },
  }
}

export type HeatLayer = ReturnType<typeof createHeatLayer>
