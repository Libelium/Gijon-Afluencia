/**
 * Preferencias de organizacion que componen la personalizacion visual.
 *
 * Los nombres son los que valida el backend y NO son libres: `PreferenceValidator` agrupa por
 * nombre exacto para decidir como validar cada valor, asi que inventarse uno lo degrada a
 * «escalar seguro» (512 caracteres, sin `<` ni `>`) y un data URI de imagen seria rechazado.
 *
 *   - colores  -> `PreferenceValidator::COLOR_PREFERENCES`, exige `#` + 3 a 8 hex
 *   - iconos   -> `ImagePreferenceHelper`, exige data URI de imagen rasterizada; SVG rechazado
 *                 (hallazgo de pentest 5.2.4), y el tipo real se comprueba por magic bytes
 *   - footer   -> `HtmlSanitizerHelper`, HTML saneado con lista blanca de HTMLPurifier
 */

/** Colores de marca. Las variantes por tema se derivan en `palette.ts`. */
export const COLOR_PREFERENCES = [
  'themePrimaryColor',
  'themeSecondaryColor',
  'themeLightPrimaryColor',
] as const

/**
 * Sobrescrituras opcionales del tema oscuro. Si estan puestas ganan a lo derivado, para quien
 * necesite un color exacto; si no, `palette.ts` los calcula con el contraste garantizado.
 */
export const DARK_OVERRIDE_PREFERENCES = [
  'darkThemePrimaryColor',
  'darkThemeSecondaryColor',
  'darkThemeLightPrimaryColor',
] as const

/** Iconos. `themeLoginIcon` lo sirve tambien Keycloak por el endpoint publico de imagen. */
export const IMAGE_PREFERENCES = [
  'themeLightIcon',
  'themeDarkIcon',
  'themeLoginIcon',
] as const

export const HTML_PREFERENCES = ['themeCustomFooter'] as const

export const CUSTOMIZATION_PREFERENCES = [
  ...COLOR_PREFERENCES,
  ...DARK_OVERRIDE_PREFERENCES,
  ...IMAGE_PREFERENCES,
  ...HTML_PREFERENCES,
] as const

export type CustomizationPreference = (typeof CUSTOMIZATION_PREFERENCES)[number]

export type CustomizationValues = Partial<Record<CustomizationPreference, string>>

/**
 * Colores por defecto: los del tema violeta que trae la aplicacion. Sirven de respaldo cuando la
 * organizacion no ha personalizado nada, de modo que la interfaz nunca se queda sin color.
 */
export const DEFAULT_BRAND = {
  primary: '#7233C2',
  secondary: '#4A4766',
  accent: '#1C5E85',
} as const

/** Mismo patron que `PreferenceValidator::isHexColor`, para avisar antes de enviar y no comerse un 422. */
const HEX = /^#[0-9A-Fa-f]{3,8}$/

export function isHexColor(value: string): boolean {
  return HEX.test(value.trim())
}

/** Tipos que acepta `ImagePreferenceHelper`. El SVG se rechaza a proposito, no es un olvido. */
export const ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif'] as const

/**
 * Tope de tamano del fichero antes de codificar. El limite real no es de la columna
 * (`organization_preference.value` es TEXT) sino del navegador de quien mire la aplicacion: el
 * data URI viaja en cada respuesta de preferencias, y base64 engorda un tercio. 512 KB de origen
 * son ~683 KB de texto, suficiente para un logotipo y poco como para no lastrar la carga.
 */
export const MAX_IMAGE_BYTES = 512 * 1024

export function isAllowedImageType(type: string): boolean {
  return (ALLOWED_IMAGE_TYPES as readonly string[]).includes(type)
}

/** Lee un fichero como data URI, el formato exacto que espera el backend. */
export function fileToDataUri(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('No se ha podido leer el fichero'))
    reader.readAsDataURL(file)
  })
}
