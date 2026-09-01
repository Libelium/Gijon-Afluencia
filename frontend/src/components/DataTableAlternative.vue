<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import type { AlternativeTable } from '@/features/dashboards/charts/a11y'

/**
 * Alternativa textual de un contenido grafico: la misma informacion, en una tabla de datos.
 *
 * Por que una tabla y no una descripcion: una grafica o un mapa no se resumen sin perder lo
 * que los hace utiles —el valor concreto de un punto—. La recomendacion de la auditoria es
 * literal: «generar la tabla de datos que ya alimenta la grafica y ofrecerla como alternativa,
 * no describir la imagen».
 *
 * Por que dentro de un `<details>`: la tabla tiene que estar DISPONIBLE, no necesariamente
 * desplegada. Plegada, el resumen es un control nativo, enfocable con teclado y anunciado como
 * tal, y no altera el alto del panel; desplegada, la lee cualquiera, tambien quien no usa
 * lector de pantalla pero necesita el numero exacto.
 *
 * La tabla es `<table>` nativa con `<caption>` y `<th scope="col">`, no una `VDataTable`: aqui
 * lo que hace falta es semantica, no paginacion ni ordenacion.
 */
const props = withDefaults(
  defineProps<{
    /** Rotulo de lo que representa: da nombre al resumen y al `<caption>`. */
    title: string
    table: AlternativeTable
    /** Texto del control de despliegue; por defecto, «Ver los datos en una tabla». */
    label?: string
    /** Alto maximo de la tabla desplegada, en pixeles. */
    maxHeight?: number
  }>(),
  { maxHeight: 320 },
)

const summaryText = computed(() => props.label ?? t('a11y.dataTable.show'))
const truncated = computed(() => props.table.total > props.table.rows.length)
const hasRows = computed(() => props.table.rows.length > 0)
</script>

<template>
  <details class="data-alt">
    <summary class="data-alt__summary text-caption">
      <VIcon icon="mdi-table" size="14" class="me-1" />
      {{ summaryText }}
    </summary>

    <div class="data-alt__body" :style="{ maxHeight: `${maxHeight}px` }">
      <p v-if="!hasRows" class="text-caption text-medium-emphasis pa-2 mb-0">
        {{ t('a11y.dataTable.empty') }}
      </p>

      <table v-else class="data-alt__table text-caption">
        <caption class="data-alt__caption">
          {{ t('a11y.dataTable.caption', { title }) }}
          <template v-if="truncated">
            {{ t('a11y.dataTable.truncated', { shown: table.rows.length, total: table.total }) }}
          </template>
        </caption>
        <thead>
          <tr>
            <th v-for="column in table.columns" :key="column" scope="col">{{ column }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in table.rows" :key="index">
            <!-- La primera celda identifica la fila (el instante, la zona…): es cabecera de
                 fila, y con `scope="row"` el lector la repite al leer cada valor. -->
            <th scope="row">{{ row[0] }}</th>
            <td v-for="(cell, column) in row.slice(1)" :key="column">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </details>
</template>

<style scoped>
.data-alt {
  margin-block-start: 8px;
}

.data-alt__summary {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
  color: rgb(var(--v-theme-on-surface-variant));
  user-select: none;
}

.data-alt__summary:hover {
  background: rgb(var(--v-theme-surface-variant));
}

/* El anillo de foco es obligatorio: el resumen es el unico control de este bloque y sin el
   no se ve donde esta el teclado. */
.data-alt__summary:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.data-alt__body {
  overflow: auto;
  margin-block-start: 6px;
  border: 1px solid rgb(var(--v-theme-outline));
  border-radius: 8px;
}

.data-alt__table {
  inline-size: 100%;
  border-collapse: collapse;
}

.data-alt__caption {
  caption-side: top;
  text-align: start;
  padding: 6px 8px;
  color: rgb(var(--v-theme-on-surface-variant));
}

.data-alt__table th,
.data-alt__table td {
  padding: 4px 8px;
  border-block-end: 1px solid rgb(var(--v-theme-outline));
  text-align: start;
  white-space: nowrap;
}

.data-alt__table thead th {
  position: sticky;
  inset-block-start: 0;
  background: rgb(var(--v-theme-surface-variant));
  font-weight: 600;
}

.data-alt__table tbody th {
  font-weight: 500;
}
</style>
