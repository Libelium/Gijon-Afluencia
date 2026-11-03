import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

/**
 * Configuracion de pruebas, separada de `vite.config.ts` a proposito: la de compilacion no
 * necesita saber nada de las pruebas y asi ninguna de las dos arrastra la otra.
 *
 * Los umbrales de cobertura son deliberadamente ASIMETRICOS:
 *
 *  - Global bajo (`lines: 6`) porque la base de codigo tiene ~18.300 lineas sin pruebas y poner
 *    un 80 % hoy solo conseguiria que nadie pudiera ejecutar `npm test`. Es un suelo, no una
 *    meta: sube cada vez que entra un modulo cubierto.
 *  - Por fichero, exigente en lo que YA esta cubierto. Ahi si se pide casi el 100 %, para que
 *    una regresion en la logica de contraste o en los adaptadores de datos rompa la suite.
 *
 * Al anadir pruebas de un modulo nuevo, se le anade aqui su umbral propio.
 */
export default defineConfig({
  plugins: [vue(), vuetify({ autoImport: true })],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.spec.ts'],
    setupFiles: ['tests/setup.ts'],
    // Vuetify se distribuye sin transpilar para navegadores antiguos y necesita transformarse.
    server: { deps: { inline: ['vuetify'] } },
    coverage: {
      provider: 'v8',
      reporter: ['text-summary', 'text'],
      include: ['src/**/*.ts', 'src/**/*.vue'],
      exclude: ['src/**/*.spec.ts', 'src/**/i18n.ts', 'src/i18n/**', 'src/types/**', 'src/main.ts'],
      thresholds: {
        // Suelo global. Es bajo a proposito y no es una meta: mide sobre las ~18.300 lineas de
        // la aplicacion entera, de las que la inmensa mayoria son plantillas de vistas todavia
        // sin pruebas. Solo sirve para que la cobertura no pueda BAJAR de lo ya conseguido.
        // Se sube cada vez que entra un modulo cubierto.
        lines: 9,
        statements: 9,
        // No se fijan umbrales globales de ramas ni de funciones: v8 atribuye 100 % de ramas a
        // los ficheros sin ninguna linea ejecutada, asi que el porcentaje global SUBE al anadir
        // codigo sin probar. Seria un indicador que premia lo contrario de lo que se busca.

        // Por fichero, en cambio, se exige de verdad: aqui una regresion rompe la suite.
        'src/customization/palette.ts': { lines: 95, functions: 100, branches: 85, statements: 95 },
        'src/features/dashboards/charts/chartOptions.ts': {
          lines: 95,
          functions: 90,
          branches: 90,
          statements: 95,
        },
        'src/features/dashboards/charts/a11y.ts': {
          lines: 95,
          functions: 100,
          branches: 90,
          statements: 95,
        },
        'src/lib/a11y.ts': { lines: 100, functions: 100, branches: 100, statements: 100 },
        'src/plugins/theme.ts': { lines: 100, functions: 100, branches: 100, statements: 100 },
        'src/api/scopes.ts': { lines: 95, functions: 100, branches: 90, statements: 95 },
        'src/features/dashboards/lib/range.ts': { lines: 100, functions: 100, branches: 90, statements: 100 },
        'src/features/dashboards/templates/contract.ts': {
          lines: 100,
          functions: 100,
          branches: 100,
          statements: 100,
        },
        'src/features/dashboards/api/panelData.ts': {
          lines: 95,
          functions: 100,
          branches: 80,
          statements: 95,
        },
        'src/features/dashboards/templates/transits/pairs.ts': {
          lines: 90,
          functions: 90,
          branches: 80,
          statements: 90,
        },
        'src/features/dashboards/templates/lidar/roles.ts': {
          lines: 100,
          functions: 60,
          branches: 95,
          statements: 100,
        },
        'src/features/dashboards/templates/lidar/useZone.ts': {
          lines: 95,
          functions: 100,
          branches: 75,
          statements: 95,
        },
        // Suelo de lo ya cubierto (perfil de zona y seleccion de zonas); las lecturas de series
        // por HTTP siguen sin pruebas y suben el umbral cuando las tengan.
        'src/features/dashboards/templates/lidar/data.ts': {
          lines: 35,
          functions: 35,
          branches: 75,
          statements: 35,
        },
        'src/features/entities/views/EntitiesListView.vue': {
          lines: 80,
          functions: 30,
          branches: 55,
          statements: 80,
        },
        // Solo `listEntities` tiene pruebas: es un suelo para que no baje, no una meta.
        'src/features/entities/api/entities.ts': { lines: 20, functions: 8, branches: 25, statements: 20 },
        'src/features/map/lib/viewport.ts': { lines: 100, functions: 100, branches: 100, statements: 100 },
        // Solo `mergePlaced` tiene pruebas: es un suelo para que no baje, no una meta.
        'src/features/map/lib/geometry.ts': { lines: 20, functions: 14, branches: 95, statements: 20 },
        'src/features/entities/components/EntityRenameDialog.vue': {
          lines: 95,
          functions: 60,
          branches: 80,
          statements: 95,
        },
        'src/features/entities/views/EntityDetailView.vue': {
          lines: 95,
          functions: 60,
          branches: 75,
          statements: 95,
        },
      },
    },
  },
})
