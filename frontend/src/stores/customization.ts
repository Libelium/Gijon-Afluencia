import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { ThemeInstance } from 'vuetify'
import {
  getPreferences,
  getPublicPreferences,
  pickCustomization,
  savePreference,
  deletePreference,
  type OrganizationPreferences,
} from '@/api/organization'
import {
  CUSTOMIZATION_PREFERENCES,
  DEFAULT_BRAND,
  isHexColor,
  type CustomizationPreference,
  type CustomizationValues,
} from '@/customization/preferences'
import { darkColors, lightColors, type BrandColors } from '@/customization/palette'

/**
 * Personalizacion visual de la organizacion: colores de marca, logotipos y footer.
 *
 * Se aplica en tiempo de ejecucion sobre el tema de Vuetify, no al compilar, para que la misma
 * imagen de contenedor sirva a cualquier organizacion — igual que hace `config.js` con la
 * configuracion. Los valores vienen de las preferencias de organizacion del backend.
 */

const CACHE_KEY = 'pidgijon.customization'

/**
 * Se guarda el ultimo valor conocido en el navegador y se aplica antes de pedirlo al servidor.
 * Sin esto la aplicacion arranca con la paleta por defecto y salta al color corporativo cuando
 * responde la peticion: un parpadeo de marca en cada carga.
 */
function readCache(): CustomizationValues {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    return raw ? (JSON.parse(raw) as CustomizationValues) : {}
  } catch {
    return {}
  }
}

function writeCache(values: CustomizationValues): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(values))
  } catch {
    // Modo privado o cuota agotada: la personalizacion sigue funcionando, solo parpadeara.
  }
}

export const useCustomizationStore = defineStore('customization', () => {
  const values = ref<CustomizationValues>(readCache())
  const organizationId = ref<number | null>(null)
  const loading = ref(false)
  const saving = ref(false)

  const color = (name: CustomizationPreference, fallback: string): string => {
    const v = values.value[name]
    return v && isHexColor(v) ? v : fallback
  }

  const brand = computed<BrandColors>(() => ({
    primary: color('themePrimaryColor', DEFAULT_BRAND.primary),
    secondary: color('themeSecondaryColor', DEFAULT_BRAND.secondary),
    accent: color('themeLightPrimaryColor', DEFAULT_BRAND.accent),
  }))

  /** Logotipo de la barra lateral: uno por tema, con respaldo al del tema claro. */
  const logo = (theme: 'light' | 'dark'): string | null => {
    const dark = values.value.themeDarkIcon
    const light = values.value.themeLightIcon
    return (theme === 'dark' ? dark || light : light || dark) || null
  }

  const footerHtml = computed(() => values.value.themeCustomFooter || null)

  /**
   * Escribe los colores derivados en el tema de Vuetify.
   *
   * Se mutan los colores del tema existente en lugar de registrar temas nuevos: asi se conservan
   * los neutros y los pares texto/fondo que ya trae `plugins/vuetify.ts` con su contraste
   * calculado, y solo cambia lo que es de marca.
   */
  function applyTheme(theme: ThemeInstance): void {
    const light = theme.themes.value.light
    const dark = theme.themes.value.dark
    if (!light || !dark) return

    const l = lightColors(brand.value, light.colors.surface)
    const d = darkColors(brand.value, dark.colors.surface)

    // Las sobrescrituras explicitas del tema oscuro ganan a lo derivado.
    const overrides: Array<[CustomizationPreference, keyof typeof d]> = [
      ['darkThemePrimaryColor', 'primary'],
      ['darkThemeSecondaryColor', 'secondary'],
      ['darkThemeLightPrimaryColor', 'lightPrimary'],
    ]
    for (const [pref, key] of overrides) {
      const v = values.value[pref]
      if (v && isHexColor(v)) d[key] = v
    }

    light.colors.primary = l.primary
    light.colors['on-primary'] = l.onPrimary
    light.colors.secondary = l.secondary
    light.colors['on-secondary'] = l.onSecondary
    light.colors['light-primary'] = l.lightPrimary
    light.colors.info = l.accent

    dark.colors.primary = d.primary
    dark.colors['on-primary'] = d.onPrimary
    dark.colors.secondary = d.secondary
    dark.colors['on-secondary'] = d.onSecondary
    dark.colors['light-primary'] = d.lightPrimary
    dark.colors.info = d.accent
  }

  function absorb(all: OrganizationPreferences): void {
    values.value = pickCustomization(all, CUSTOMIZATION_PREFERENCES)
    writeCache(values.value)
  }

  /** Carga con sesion. Un fallo no es fatal: se sigue con lo cacheado o con la paleta por defecto. */
  async function load(orgId: number): Promise<void> {
    organizationId.value = orgId
    loading.value = true
    try {
      absorb(await getPreferences(orgId))
    } finally {
      loading.value = false
    }
  }

  /** Carga sin sesion, para la pantalla de inicio de sesion. */
  async function loadPublic(orgId: number): Promise<void> {
    organizationId.value = orgId
    absorb(await getPublicPreferences(orgId))
  }

  /** Guarda un valor y lo refleja de inmediato, sin recargar la pagina. */
  async function save(name: CustomizationPreference, value: string): Promise<void> {
    const orgId = organizationId.value
    if (orgId === null) throw new Error('Organización desconocida')
    saving.value = true
    try {
      await savePreference(orgId, name, value)
      values.value = { ...values.value, [name]: value }
      writeCache(values.value)
    } finally {
      saving.value = false
    }
  }

  /** Borra un valor y vuelve al comportamiento por defecto para esa pieza. */
  async function clear(name: CustomizationPreference): Promise<void> {
    const orgId = organizationId.value
    if (orgId === null) throw new Error('Organización desconocida')
    saving.value = true
    try {
      await deletePreference(orgId, name)
      const next = { ...values.value }
      delete next[name]
      values.value = next
      writeCache(values.value)
    } finally {
      saving.value = false
    }
  }

  return {
    values,
    organizationId,
    loading,
    saving,
    brand,
    logo,
    footerHtml,
    applyTheme,
    load,
    loadPublic,
    save,
    clear,
  }
})
