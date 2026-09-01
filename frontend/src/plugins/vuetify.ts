import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

import { dark, light } from './theme'

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
    // `scope="col"` en cada `<th>`: Vuetify genera las cabeceras de tabla sin el, y sin ese
    // atributo un lector de pantalla no puede asociar cada celda con su columna (WCAG 1.3.1,
    // hallazgo GDTIS-PT01-ACC-006). `headerProps` se propaga tal cual al elemento `<th>`, asi
    // que declararlo aqui lo arregla en TODAS las tablas de la aplicacion a la vez.
    VDataTable: { density: 'comfortable', hover: true, headerProps: { scope: 'col' } },
    VDataTableServer: { density: 'comfortable', hover: true, headerProps: { scope: 'col' } },
    VDataTableVirtual: { density: 'comfortable', hover: true, headerProps: { scope: 'col' } },
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
