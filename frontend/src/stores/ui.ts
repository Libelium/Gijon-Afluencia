import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const THEME_KEY = 'pidgijon.theme'
const RAIL_KEY = 'pidgijon.nav.rail'

export type ThemeName = 'light' | 'dark'

export const useUiStore = defineStore('ui', () => {
  const stored = localStorage.getItem(THEME_KEY)
  const theme = ref<ThemeName>(stored === 'dark' ? 'dark' : 'light')
  const rail = ref(localStorage.getItem(RAIL_KEY) === 'true')
  const drawer = ref(true)

  watch(theme, (v) => localStorage.setItem(THEME_KEY, v))
  watch(rail, (v) => localStorage.setItem(RAIL_KEY, String(v)))

  const toggleTheme = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  return { theme, rail, drawer, toggleTheme }
})
