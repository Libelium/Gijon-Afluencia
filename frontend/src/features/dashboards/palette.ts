/**
 * Colores de los graficos. Se declaran aqui, y no se leen del tema de Vuetify, porque los
 * graficos se pintan sobre lienzo (canvas) y ahi no llegan las variables CSS: hay que darle
 * valores literales. Los pares de contraste estan calculados sobre la superficie de cada tema
 * (claro #FFFFFF, oscuro #1A1726) y cumplen WCAG AA. No cambiar sin recalcular.
 *
 * El orden alterna matiz y luminosidad a proposito: dos series contiguas se distinguen
 * tambien en escala de grises, que es lo que salva la lectura a quien no percibe bien el color.
 */

export const SERIES_LIGHT = [
  '#7233C2',
  '#9A6A00',
  '#00706B',
  '#B5216B',
  '#1C6FA8',
  '#2E7D4F',
  '#544F6E',
  '#C25A2B',
]

export const SERIES_DARK = [
  '#C4A7FF',
  '#E9B44C',
  '#4FC3BA',
  '#F58BB8',
  '#6FB6E0',
  '#5FC98F',
  '#B0AAC6',
  '#F09A6A',
]

/**
 * Escala secuencial para niveles de ocupacion, de menos a mas. Es monotona en luminancia
 * (cada paso mas intenso que el anterior) y termina en el color principal de cada tema,
 * de modo que el nivel maximo se lee como aviso sin necesidad de leyenda.
 */
export const OCCUPANCY_LIGHT = ['#FBE7D2', '#F3C193', '#E68E53', '#C24A20', '#B3261E']

export const OCCUPANCY_DARK = ['#3F2E2A', '#6B4433', '#9C6440', '#D08B55', '#FF8A7A']

/** Tinta, lineas, texto secundario y superficie de cada tema, en el mismo orden que Vuetify. */
export const INK = { light: '#1C1830', dark: '#E9E6F2' }
export const LINE = { light: '#E2DEEE', dark: '#2E2A3D' }
export const MUTED = { light: '#5B5670', dark: '#A7A2BC' }
export const SURFACE = { light: '#FFFFFF', dark: '#1A1726' }

export function seriesColors(isDark: boolean): string[] {
  return isDark ? [...SERIES_DARK] : [...SERIES_LIGHT]
}

export function occupancyColors(isDark: boolean): string[] {
  return isDark ? [...OCCUPANCY_DARK] : [...OCCUPANCY_LIGHT]
}

/** Color del nivel de ocupacion para una proporcion 0..1 (fuera de rango se recorta). */
export function occupancyColor(ratio: number, isDark = false): string {
  const scale = occupancyColors(isDark)
  if (!Number.isFinite(ratio)) return scale[0]
  const index = Math.round(Math.min(1, Math.max(0, ratio)) * (scale.length - 1))
  return scale[index]
}

function toLinear(component: number): number {
  const channel = component / 255
  return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
}

function luminance(hex: string): number {
  const value = hex.replace('#', '')
  const full =
    value.length === 3
      ? value
          .split('')
          .map((c) => c + c)
          .join('')
      : value
  const r = toLinear(parseInt(full.slice(0, 2), 16))
  const g = toLinear(parseInt(full.slice(2, 4), 16))
  const b = toLinear(parseInt(full.slice(4, 6), 16))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast(a: number, b: number): number {
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

/**
 * Tinta legible sobre un color de relleno: devuelve la de mayor contraste de las dos del tema.
 * Los pasos intermedios de la escala de ocupacion quedan cerca de 4,5:1, asi que las cifras
 * que se impriman encima deben ir en negrita o a tamano grande (AA large, 3:1).
 */
export function readableOn(background: string): string {
  const bg = luminance(background)
  return contrast(bg, luminance(INK.light)) >= contrast(bg, luminance('#FFFFFF'))
    ? INK.light
    : '#FFFFFF'
}
