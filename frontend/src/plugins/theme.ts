/**
 * Definicion de los dos temas, aparte del plugin para que se pueda importar sin arrastrar
 * Vuetify ni sus hojas de estilo: `theme.spec.ts` comprueba sobre estos mismos valores que
 * todos los pares texto/fondo cumplen el 4.5:1 de WCAG 2.2 AA (criterio 1.4.3), que es
 * obligatorio por el RD 1112/2018.
 *
 * Paleta violeta con neutros de matiz calido-violeta, que es lo que da cohesion al conjunto.
 * No cambiar ningun valor sin recalcular el contraste: la prueba lo verifica y falla.
 */

export interface ThemeDefinition {
  dark: boolean
  colors: Record<string, string>
  variables: Record<string, string | number>
}

/**
 * Opacidad de `text-medium-emphasis` y del resto de texto secundario de Vuetify.
 *
 * Vuetify trae 0,60 en el tema claro. Sobre esta paleta eso da 4,42:1 contra el fondo de
 * pagina (#F7F5FB) y 4,32:1 contra la superficie tenue (#F0EDF7): por debajo del minimo AA,
 * que es exactamente el hallazgo GDTIS-PT01-ACC-011. Con 0,70 el peor caso sube a 5,94:1.
 *
 * En el tema oscuro Vuetify ya usa 0,70 y cumplia (5,55:1 en el peor caso); se deja igual para
 * no alterar un tema que estaba bien.
 */
export const MEDIUM_EMPHASIS_OPACITY = 0.7

export const light: ThemeDefinition = {
  dark: false,
  colors: {
    background: '#F7F5FB',
    surface: '#FFFFFF',
    'surface-variant': '#F0EDF7',
    'on-surface-variant': '#413C57',
    primary: '#7233C2', // 7.08:1 con blanco
    'on-primary': '#FFFFFF',
    secondary: '#4A4766', // 8.81:1
    'on-secondary': '#FFFFFF',
    error: '#B3261E',
    'on-error': '#FFFFFF',
    success: '#1B6B45',
    'on-success': '#FFFFFF',
    warning: '#E8A32B',
    'on-warning': '#1C1830',
    info: '#1C5E85',
    'on-info': '#FFFFFF',
    'on-background': '#1C1830',
    'on-surface': '#1C1830',
    outline: '#E2DEEE',
    'outline-strong': '#7A7590', // 4.40:1 — borde de campos y controles
    muted: '#5B5670', // 6.98:1 — texto secundario
  },
  variables: {
    'medium-emphasis-opacity': MEDIUM_EMPHASIS_OPACITY,
  },
}

export const dark: ThemeDefinition = {
  dark: true,
  colors: {
    background: '#121019',
    surface: '#1A1726',
    'surface-variant': '#241F33',
    'on-surface-variant': '#CFC9E0',
    primary: '#C4A7FF', // 8.64:1 con la superficie oscura
    'on-primary': '#2A0A4A',
    secondary: '#B9B4D4',
    'on-secondary': '#1E1B2E',
    error: '#FF8A7A',
    'on-error': '#3A0B08',
    success: '#6BCF9B',
    'on-success': '#04291A',
    warning: '#F2C25B',
    'on-warning': '#2A2005',
    info: '#7EC0E8',
    'on-info': '#062333',
    'on-background': '#E9E6F2',
    'on-surface': '#E9E6F2',
    outline: '#2E2A3D',
    'outline-strong': '#7E7899', // 4.21:1
    muted: '#A7A2BC', // 7.15:1
  },
  variables: {
    'medium-emphasis-opacity': MEDIUM_EMPHASIS_OPACITY,
  },
}

/** Los fondos sobre los que se pinta texto en cada tema. Los usa la prueba de contraste. */
export const SURFACES = ['background', 'surface', 'surface-variant'] as const
