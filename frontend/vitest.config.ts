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
      },
    },
  },
})
