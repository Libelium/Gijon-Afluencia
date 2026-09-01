/**
 * Deriva la paleta del tema a partir de los colores de marca, garantizando el contraste.
 *
 * Por que se deriva en vez de pedirlos todos: un color corporativo suele estar pensado para
 * fondo claro y, puesto tal cual sobre el fondo oscuro, incumple el contraste. El rojo de
 * Gijon (#97233F) da 7.99:1 sobre blanco —excelente— y 2.20:1 sobre la superficie oscura,
 * menos de la mitad del 4.5:1 que exige WCAG AA. Pedir seis colores a mano trasladaria ese
 * calculo a quien personaliza, y basta con que se despiste una vez para dejar la interfaz por
 * debajo de la normativa de accesibilidad del sector publico.
 *
 * Asi que aqui se pide UN color de marca por papel y se calcula la variante de cada tema:
 * en claro se usa el color tal cual (aclarandolo solo si no llega al minimo sobre blanco), y
 * en oscuro se aclara conservando el tono hasta alcanzar el umbral. Quien quiera control total
 * puede fijar las preferencias `darkTheme*`, que tienen prioridad sobre lo calculado.
 */

/** Minimos de WCAG 2.1: AA para texto normal, y el relajado para elementos no textuales. */
export const AA_TEXT = 4.5
export const AA_NON_TEXT = 3

export interface Rgb {
  r: number
  g: number
  b: number
}

const clamp = (v: number, min = 0, max = 1) => Math.min(max, Math.max(min, v))

/** Acepta `#RGB` y `#RRGGBB`. Devuelve null en cualquier otro caso: el llamante decide el respaldo. */
export function parseHex(hex: string): Rgb | null {
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return null
  const h = m[1]
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  return {
    r: parseInt(full.slice(0, 2), 16) / 255,
    g: parseInt(full.slice(2, 4), 16) / 255,
    b: parseInt(full.slice(4, 6), 16) / 255,
  }
}

const toHex = ({ r, g, b }: Rgb): string =>
  '#' + [r, g, b].map((c) => Math.round(clamp(c) * 255).toString(16).padStart(2, '0')).join('').toUpperCase()

/** Luminancia relativa de WCAG. */
function luminance({ r, g, b }: Rgb): number {
  const f = (c: number) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4))
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}

/** Razon de contraste entre dos colores, de 1 (identicos) a 21 (negro sobre blanco). */
export function contrast(a: string, b: string): number {
  const ca = parseHex(a)
  const cb = parseHex(b)
  if (!ca || !cb) return 1
  const la = luminance(ca)
  const lb = luminance(cb)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

function toHsl({ r, g, b }: Rgb): { h: number; s: number; l: number } {
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2
  const d = max - min
  if (d === 0) return { h: 0, s: 0, l }
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  let h: number
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6
  else if (max === g) h = ((b - r) / d + 2) / 6
  else h = ((r - g) / d + 4) / 6
  return { h, s, l }
}

function fromHsl(h: number, s: number, l: number): Rgb {
  if (s === 0) return { r: l, g: l, b: l }
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s
  const p = 2 * l - q
  const channel = (t: number) => {
    let x = t
    if (x < 0) x += 1
    if (x > 1) x -= 1
    if (x < 1 / 6) return p + (q - p) * 6 * x
    if (x < 1 / 2) return q
    if (x < 2 / 3) return p + (q - p) * (2 / 3 - x) * 6
    return p
  }
  return { r: channel(h + 1 / 3), g: channel(h), b: channel(h - 1 / 3) }
}

/**
 * Ajusta la luminosidad de `hex` —conservando tono y saturacion— hasta que contrasta al menos
 * `target` con `against`. Busca en la direccion que indica `towards`, y en pasos de 0.5 % para
 * moverse lo menos posible: el objetivo es el color corporativo mas parecido que cumple, no un
 * color bonito cualquiera.
 *
 * Si ni el blanco ni el negro puros llegan al umbral (fondo de contraste imposible), devuelve el
 * extremo alcanzado: siempre es mejor que el color original, y `contrast()` permite al llamante
 * detectar que no se cumplio.
 */
export function ensureContrast(
  hex: string,
  against: string,
  target: number,
  towards: 'lighter' | 'darker',
): string {
  const rgb = parseHex(hex)
  if (!rgb) return hex
  if (contrast(hex, against) >= target) return hex

  const { h, s } = toHsl(rgb)
  const step = towards === 'lighter' ? 0.005 : -0.005
  let { l } = toHsl(rgb)
  let last = hex

  while (l >= 0 && l <= 1) {
    l += step
    last = toHex(fromHsl(h, s, clamp(l)))
    if (contrast(last, against) >= target) return last
  }
  return last
}

/** Mezcla `hex` con `base` en la proporcion dada (0 = base, 1 = hex). Para rellenos suaves. */
export function mix(hex: string, base: string, amount: number): string {
  const a = parseHex(hex)
  const b = parseHex(base)
  if (!a || !b) return hex
  const t = clamp(amount)
  return toHex({
    r: b.r + (a.r - b.r) * t,
    g: b.g + (a.g - b.g) * t,
    b: b.b + (a.b - b.b) * t,
  })
}

/** Blanco o negro, el que mas contraste dé sobre `hex`. Para el texto que va encima del color. */
export function readableOn(hex: string): string {
  return contrast(hex, '#FFFFFF') >= contrast(hex, '#000000') ? '#FFFFFF' : '#000000'
}

export interface BrandColors {
  primary: string
  secondary: string
  accent: string
}

export interface ModeColors {
  primary: string
  onPrimary: string
  lightPrimary: string
  secondary: string
  onSecondary: string
  accent: string
}

/**
 * Colores del tema claro. El fondo de referencia es la superficie, no el fondo de pagina: los
 * botones y los textos de enfasis se pintan sobre tarjetas blancas.
 */
export function lightColors(brand: BrandColors, surface = '#FFFFFF'): ModeColors {
  const primary = ensureContrast(brand.primary, surface, AA_TEXT, 'darker')
  const secondary = ensureContrast(brand.secondary, surface, AA_TEXT, 'darker')
  return {
    primary,
    onPrimary: readableOn(primary),
    // Relleno suave (chips, filas seleccionadas, avisos): un 12 % del primario sobre la
    // superficie deja sitio de sobra para texto oscuro encima.
    lightPrimary: mix(primary, surface, 0.12),
    secondary,
    onSecondary: readableOn(secondary),
    accent: ensureContrast(brand.accent, surface, AA_NON_TEXT, 'darker'),
  }
}

/** Colores del tema oscuro: los mismos tonos, aclarados hasta cumplir sobre la superficie oscura. */
export function darkColors(brand: BrandColors, surface = '#1A1726'): ModeColors {
  const primary = ensureContrast(brand.primary, surface, AA_TEXT, 'lighter')
  const secondary = ensureContrast(brand.secondary, surface, AA_TEXT, 'lighter')
  return {
    primary,
    onPrimary: readableOn(primary),
    // En oscuro el relleno suave tiene que ser OSCURO: aclararlo como en el tema claro
    // produciria un bloque luminoso que rompe la jerarquia y deslumbra.
    lightPrimary: mix(brand.primary, surface, 0.28),
    secondary,
    onSecondary: readableOn(secondary),
    accent: ensureContrast(brand.accent, surface, AA_NON_TEXT, 'lighter'),
  }
}
