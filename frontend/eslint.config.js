// Configuracion plana de ESLint (formato unico desde ESLint 9).
//
// Por que existe: el proyecto es TypeScript estricto y `vue-tsc` ya pasa limpio, pero el
// compilador no ve los errores que viven en la PLANTILLA de un componente (una directiva mal
// escrita, una clave `v-for` ausente, un `v-html` sin justificar). Sin ESLint, los comentarios
// `eslint-disable-next-line` que ya habia repartidos por el codigo no desactivaban nada porque
// no habia nadie leyendolos.
//
// Criterio de las reglas: se activan las que detectan ERRORES (esencial + recomendado de
// eslint-plugin-vue, y el recomendado de typescript-eslint) y se apagan las de FORMATO, que son
// competencia de un formateador y no de un analizador estatico.
import js from '@eslint/js'
import globals from 'globals'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'

export default tseslint.config(
  {
    ignores: ['dist/**', 'coverage/**', 'node_modules/**', 'public/**', 'THIRD-PARTY-LICENSES.json'],
  },

  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],

  {
    files: ['**/*.{js,ts,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser },
      parserOptions: {
        // Las plantillas las analiza vue-eslint-parser; el bloque <script lang="ts"> se delega
        // en el analizador de TypeScript.
        parser: tseslint.parser,
        extraFileExtensions: ['.vue'],
      },
    },
    rules: {
      // --- Formato: lo resuelve el formateador, no el analizador --------------------
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multiline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/html-indent': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/attributes-order': 'off',
      'vue/first-attribute-linebreak': 'off',

      // Vuetify nombra los huecos de tabla con un punto (`#[`item.name`]`), y la regla lee ese
      // punto como un modificador de directiva. El compilador de Vue no: genera el hueco
      // «item.name» tal cual, comprobado con `compileTemplate`. Es un falso positivo conocido.
      'vue/valid-v-slot': ['error', { allowModifiers: true }],

      // En `<script setup lang="ts">` una prop opcional (`prop?: T`) YA declara que su valor por
      // defecto es `undefined`, y el compilador obliga a tratarlo. Exigir ademas un valor
      // literal duplicaria la declaracion sin anadir garantia.
      'vue/require-default-prop': 'off',

      // Se prohibe reasignar la prop; se permite mutar las propiedades del objeto que llega en
      // ella. El formulario de alarmas pasa a cada tarjeta de condicion su `draft`, que es
      // deliberadamente un objeto mutable compartido con el padre.
      'vue/no-mutating-props': ['error', { shallowOnly: true }],

      // --- Errores reales -----------------------------------------------------------
      // `_` como prefijo es la convencion del proyecto para un argumento deliberadamente
      // ignorado (por ejemplo en los formateadores de ECharts).
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'none' },
      ],
      // El pie de pagina personalizable es HTML por diseno del backend y pasa por doble saneado
      // (HTMLPurifier al guardar, DOMPurify al pintar). La regla sigue activa para el resto.
      'vue/no-v-html': 'error',
      'vue/multi-word-component-names': 'off',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },

  {
    files: ['**/*.spec.ts', 'tests/**/*.ts'],
    languageOptions: { globals: { ...globals.node } },
  },

  {
    files: ['*.config.{js,ts}', 'vite.config.ts', 'vitest.config.ts'],
    languageOptions: { globals: { ...globals.node } },
  },
)
