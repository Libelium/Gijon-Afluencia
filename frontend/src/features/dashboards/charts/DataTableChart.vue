<script setup lang="ts">
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { seriesTable } from './a11y'
import type { ChartSeries } from './types'

const props = withDefaults(
  defineProps<{
    series: ChartSeries[]
    units?: string
    /** Ultimas filas que se muestran; una tabla de panel se lee, no se pagina. */
    limit?: number
    height?: number | string
  }>(),
  { limit: 50, height: 280 },
)

const session = useSessionStore()

/**
 * La construccion de la tabla vive en `a11y.ts` porque es la MISMA que alimenta la alternativa
 * textual del resto de graficas: una sola implementacion, probada una vez. Este componente solo
 * la pinta con la tabla de Vuetify, que ademas pagina y fija la cabecera.
 */
const table = computed(() =>
  seriesTable(props.series, {
    timeZone: session.timeZone,
    units: props.units,
    limit: props.limit,
    // Lo reciente arriba: en una tabla de panel es el dato que se busca.
    order: 'desc',
  }),
)

const headers = computed(() =>
  table.value.columns.map((title, index) => ({
    title,
    key: `c${index}`,
    align: (index === 0 ? 'start' : 'end') as 'start' | 'end',
    sortable: false,
  })),
)

const items = computed(() =>
  table.value.rows.map((row) => {
    const item: Record<string, string> = {}
    row.forEach((cell, index) => {
      item[`c${index}`] = cell
    })
    return item
  }),
)
</script>

<template>
  <VDataTable
    :headers="headers"
    :items="items"
    :items-per-page="-1"
    :height="height"
    item-value="c0"
    fixed-header
    hide-default-footer
    class="text-body-2"
  />
</template>
