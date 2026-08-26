import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

// Paleta violeta con neutros de matiz calido-violeta, que es lo que da cohesion al conjunto.
// Todos los pares texto/fondo estan calculados y cumplen WCAG AA (>=4.5:1 texto, >=3:1
// controles), obligatorio por la normativa de accesibilidad del sector publico.
// No cambiar ningun valor sin recalcular el contraste.
const light = {
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
}

const dark = {
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
}

export default createVuetify({
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  theme: { defaultTheme: 'light', themes: { light, dark } },
  defaults: {
    // El aspecto propio se consigue aqui, por configuracion, sin hojas de estilo a medida.
    VCard: { variant: 'flat', border: true, rounded: 'lg' },
    VBtn: { variant: 'flat', rounded: 'pill', class: 'text-none font-weight-medium' },
    VTextField: { variant: 'outlined', density: 'comfortable', rounded: 'lg', hideDetails: 'auto' },
    VSelect: { variant: 'outlined', density: 'comfortable', rounded: 'lg', hideDetails: 'auto' },
    VAutocomplete: { variant: 'outlined', density: 'comfortable', rounded: 'lg', hideDetails: 'auto' },
    VTextarea: { variant: 'outlined', density: 'comfortable', rounded: 'lg', hideDetails: 'auto' },
    VDataTable: { density: 'comfortable', hover: true },
    VDataTableServer: { density: 'comfortable', hover: true },
    VChip: { size: 'small', rounded: 'pill' },
    VToolbar: { color: 'transparent', density: 'comfortable' },
    VAppBar: { flat: true, border: 'b' },
    VNavigationDrawer: { border: 'e' },
    VList: { density: 'comfortable' },
    VListItem: { rounded: 'lg' },
    VTabs: { density: 'comfortable' },
    VAlert: { variant: 'tonal', rounded: 'lg' },
    VDialog: { maxWidth: 720 },
    VSheet: { rounded: 'lg' },
    VSkeletonLoader: { rounded: 'lg' },
    VAvatar: { rounded: 'pill' },
    VPagination: { rounded: 'pill', density: 'comfortable' },
  },
})
