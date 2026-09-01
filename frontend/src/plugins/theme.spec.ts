import { describe, expect, it } from 'vitest'
import { AA_NON_TEXT, AA_TEXT, contrast, mix } from '@/customization/palette'
import { dark, light, MEDIUM_EMPHASIS_OPACITY, SURFACES, type ThemeDefinition } from './theme'

/**
 * Verificacion del criterio WCAG 2.2 AA 1.4.3 (contraste minimo) sobre los tokens del tema.
 *
 * Se comprueba aqui, y no a ojo, porque el hallazgo GDTIS-PT01-ACC-011 fue exactamente un
 * incumplimiento de 4,42:1 —a siete centesimas del umbral— que ninguna revision visual iba a
 * detectar. Cambiar un color del tema sin recalcular rompe esta prueba.
 */

const THEMES: [string, ThemeDefinition][] = [
  ['claro', light],
  ['oscuro', dark],
]

/** Color efectivo de un texto pintado con opacidad sobre un fondo opaco. */
const withOpacity = (ink: string, background: string, opacity: number) =>
  mix(ink, background, opacity)

describe.each(THEMES)('tema %s', (_name, theme) => {
  it('el texto principal cumple 4.5:1 sobre todas las superficies', () => {
    for (const surface of SURFACES) {
      const ink = surface === 'background' ? theme.colors['on-background'] : theme.colors['on-surface']
      expect(contrast(ink, theme.colors[surface])).toBeGreaterThanOrEqual(AA_TEXT)
    }
  })

  it('cada color con pareja "on-" cumple 4.5:1 con ella', () => {
    const pairs = ['primary', 'secondary', 'error', 'success', 'warning', 'info', 'surface', 'background']
    for (const role of pairs) {
      const on = theme.colors[`on-${role}`]
      expect(on, `falta on-${role}`).toBeDefined()
      expect(contrast(theme.colors[role], on), `${role} / on-${role}`).toBeGreaterThanOrEqual(AA_TEXT)
    }
  })

  it('los colores de estado se leen sobre la superficie', () => {
    for (const role of ['primary', 'secondary', 'error', 'success', 'info', 'muted']) {
      expect(contrast(theme.colors[role], theme.colors.surface), role).toBeGreaterThanOrEqual(AA_TEXT)
    }
  })

  it('el borde de campos y controles cumple el 3:1 de elementos no textuales', () => {
    expect(contrast(theme.colors['outline-strong'], theme.colors.surface)).toBeGreaterThanOrEqual(
      AA_NON_TEXT,
    )
  })

  /** ACC-011: el motivo por el que el tema declara `medium-emphasis-opacity`. */
  it('text-medium-emphasis cumple 4.5:1 sobre todas las superficies', () => {
    const ink = theme.colors['on-surface']
    for (const surface of SURFACES) {
      const background = theme.colors[surface]
      const effective = withOpacity(ink, background, MEDIUM_EMPHASIS_OPACITY)
      expect(contrast(effective, background), `${surface}`).toBeGreaterThanOrEqual(AA_TEXT)
    }
  })

  it('la opacidad de serie de Vuetify en tema claro (0,60) NO llegaba: la prueba documenta el hallazgo', () => {
    if (theme.dark) return
    const ink = theme.colors['on-surface']
    // Este es el numero que cita la auditoria. Si algun dia el fondo cambia y 0,60 pasara a
    // cumplir, esta prueba avisa de que la sobrescritura ya no hace falta.
    expect(contrast(withOpacity(ink, theme.colors.background, 0.6), theme.colors.background)).toBeLessThan(
      AA_TEXT,
    )
  })
})
