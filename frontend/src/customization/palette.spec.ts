import { describe, expect, it } from 'vitest'
import {
  AA_NON_TEXT,
  AA_TEXT,
  contrast,
  darkColors,
  ensureContrast,
  lightColors,
  mix,
  parseHex,
  readableOn,
} from './palette'

describe('parseHex', () => {
  it('acepta #RRGGBB', () => {
    expect(parseHex('#FFFFFF')).toEqual({ r: 1, g: 1, b: 1 })
    expect(parseHex('#000000')).toEqual({ r: 0, g: 0, b: 0 })
  })

  it('acepta la forma corta #RGB expandiendo cada digito', () => {
    expect(parseHex('#FFF')).toEqual(parseHex('#FFFFFF'))
    expect(parseHex('#08F')).toEqual(parseHex('#0088FF'))
  })

  it('ignora espacios y no distingue mayusculas', () => {
    expect(parseHex('  #7233c2  ')).toEqual(parseHex('#7233C2'))
  })

  it('devuelve null en cualquier otro caso, para que el llamante decida el respaldo', () => {
    expect(parseHex('7233C2')).toBeNull()
    expect(parseHex('#12345')).toBeNull()
    expect(parseHex('#GGGGGG')).toBeNull()
    expect(parseHex('')).toBeNull()
    expect(parseHex('rgb(1,2,3)')).toBeNull()
  })
})

describe('contrast', () => {
  it('da 21:1 entre negro y blanco, el maximo de la escala', () => {
    expect(contrast('#000000', '#FFFFFF')).toBeCloseTo(21, 5)
  })

  it('da 1:1 entre un color y si mismo', () => {
    expect(contrast('#7233C2', '#7233C2')).toBeCloseTo(1, 10)
  })

  it('es simetrico: el orden de los argumentos no cambia el resultado', () => {
    expect(contrast('#7233C2', '#FFFFFF')).toBeCloseTo(contrast('#FFFFFF', '#7233C2'), 10)
  })

  it('reproduce los valores documentados de la marca de Gijon', () => {
    // Los dos numeros que cita la cabecera de palette.ts, que es de donde sale la razon de ser
    // del modulo: el mismo rojo cumple sobre blanco y suspende sobre la superficie oscura.
    expect(contrast('#97233F', '#FFFFFF')).toBeCloseTo(7.99, 1)
    expect(contrast('#97233F', '#1A1726')).toBeCloseTo(2.2, 1)
  })

  it('devuelve 1 —el caso mas desfavorable— si algun color no es valido', () => {
    expect(contrast('no-es-un-color', '#FFFFFF')).toBe(1)
    expect(contrast('#FFFFFF', 'no-es-un-color')).toBe(1)
  })
})

describe('ensureContrast', () => {
  it('no toca un color que ya cumple', () => {
    expect(ensureContrast('#7233C2', '#FFFFFF', AA_TEXT, 'darker')).toBe('#7233C2')
  })

  it('oscurece hasta alcanzar el umbral sobre fondo claro', () => {
    const result = ensureContrast('#97233F', '#FFFFFF', 7, 'darker')
    expect(contrast(result, '#FFFFFF')).toBeGreaterThanOrEqual(7)
  })

  it('aclara hasta alcanzar el umbral sobre fondo oscuro', () => {
    const result = ensureContrast('#97233F', '#1A1726', AA_TEXT, 'lighter')
    expect(contrast(result, '#1A1726')).toBeGreaterThanOrEqual(AA_TEXT)
  })

  it('se mueve lo menos posible: el resultado sigue siendo reconocible como el color de marca', () => {
    const brand = '#97233F'
    const result = ensureContrast(brand, '#1A1726', AA_TEXT, 'lighter')
    // Conserva tono y saturacion, asi que el canal rojo sigue dominando ampliamente.
    const rgb = parseHex(result)!
    expect(rgb.r).toBeGreaterThan(rgb.g)
    expect(rgb.r).toBeGreaterThan(rgb.b)
  })

  it('devuelve el color tal cual si no es un hexadecimal valido', () => {
    expect(ensureContrast('rojo', '#FFFFFF', AA_TEXT, 'darker')).toBe('rojo')
  })

  it('devuelve el extremo alcanzado cuando el umbral es inalcanzable, no un bucle infinito', () => {
    // 21:1 solo lo da negro sobre blanco: partiendo de un gris medio hacia claro es imposible.
    const result = ensureContrast('#808080', '#FFFFFF', 21, 'lighter')
    expect(parseHex(result)).not.toBeNull()
    expect(contrast(result, '#FFFFFF')).toBeLessThan(21)
  })
})

describe('mix', () => {
  it('devuelve la base con proporcion 0 y el color con proporcion 1', () => {
    expect(mix('#000000', '#FFFFFF', 0)).toBe('#FFFFFF')
    expect(mix('#000000', '#FFFFFF', 1)).toBe('#000000')
  })

  it('interpola linealmente por canal', () => {
    expect(mix('#000000', '#FFFFFF', 0.5)).toBe('#808080')
  })

  it('acota la proporcion fuera de rango en lugar de desbordar el canal', () => {
    expect(mix('#000000', '#FFFFFF', 2)).toBe('#000000')
    expect(mix('#000000', '#FFFFFF', -1)).toBe('#FFFFFF')
  })

  it('devuelve el color de entrada si alguno no es valido', () => {
    expect(mix('#123456', 'nada', 0.5)).toBe('#123456')
  })
})

describe('readableOn', () => {
  it('elige blanco sobre un fondo oscuro y negro sobre uno claro', () => {
    expect(readableOn('#1A1726')).toBe('#FFFFFF')
    expect(readableOn('#F0EDF7')).toBe('#000000')
  })

  it('el resultado siempre cumple el minimo AA de texto sobre el propio fondo', () => {
    for (const hex of ['#7233C2', '#E8A32B', '#1B6B45', '#C4A7FF', '#97233F']) {
      expect(contrast(hex, readableOn(hex))).toBeGreaterThanOrEqual(AA_TEXT)
    }
  })
})

/**
 * El nucleo de por que este modulo existe: se le puede dar CUALQUIER color corporativo y la
 * paleta resultante tiene que cumplir WCAG AA en los dos temas. Es la garantia que se le
 * ofrece a quien personaliza la plataforma sin saber de contraste.
 */
describe('paleta derivada de la marca', () => {
  const BRANDS = [
    { primary: '#97233F', secondary: '#4A4766', accent: '#E8A32B' }, // rojo de Gijon
    { primary: '#7233C2', secondary: '#4A4766', accent: '#1C5E85' }, // el de serie
    { primary: '#FFEE00', secondary: '#00FF00', accent: '#00FFFF' }, // extremos claros
    { primary: '#000000', secondary: '#0A0A0A', accent: '#101010' }, // extremos oscuros
    { primary: '#808080', secondary: '#7F7F7F', accent: '#818181' }, // grises medios
  ]

  it.each(BRANDS)('tema claro cumple AA con la marca %o', (brand) => {
    const surface = '#FFFFFF'
    const colors = lightColors(brand, surface)
    expect(contrast(colors.primary, surface)).toBeGreaterThanOrEqual(AA_TEXT)
    expect(contrast(colors.secondary, surface)).toBeGreaterThanOrEqual(AA_TEXT)
    expect(contrast(colors.accent, surface)).toBeGreaterThanOrEqual(AA_NON_TEXT)
    expect(contrast(colors.primary, colors.onPrimary)).toBeGreaterThanOrEqual(AA_TEXT)
    expect(contrast(colors.secondary, colors.onSecondary)).toBeGreaterThanOrEqual(AA_TEXT)
  })

  it.each(BRANDS)('tema oscuro cumple AA con la marca %o', (brand) => {
    const surface = '#1A1726'
    const colors = darkColors(brand, surface)
    expect(contrast(colors.primary, surface)).toBeGreaterThanOrEqual(AA_TEXT)
    expect(contrast(colors.secondary, surface)).toBeGreaterThanOrEqual(AA_TEXT)
    expect(contrast(colors.accent, surface)).toBeGreaterThanOrEqual(AA_NON_TEXT)
    expect(contrast(colors.primary, colors.onPrimary)).toBeGreaterThanOrEqual(AA_TEXT)
    expect(contrast(colors.secondary, colors.onSecondary)).toBeGreaterThanOrEqual(AA_TEXT)
  })

  it('el relleno suave del tema oscuro es oscuro, no un bloque luminoso', () => {
    const surface = '#1A1726'
    const { lightPrimary } = darkColors({ primary: '#97233F', secondary: '#4A4766', accent: '#E8A32B' }, surface)
    // Contrasta poco con la superficie precisamente porque es un velo, no un color de texto.
    expect(contrast(lightPrimary, surface)).toBeLessThan(AA_NON_TEXT)
    expect(contrast(lightPrimary, '#E9E6F2')).toBeGreaterThanOrEqual(AA_TEXT)
  })
})
