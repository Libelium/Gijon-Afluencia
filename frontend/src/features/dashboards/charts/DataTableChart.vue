<script setup lang="ts">
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { t } from '@/i18n'
import { formatDateTime, formatNumber } from '@/lib/format'
import { toMillis } from './chartOptions'
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

type Header = { title: string; key: string; align?: 'start' | 'end' | 'center'; sortable?: boolean }

// Las unidades van en la cabecera, no repetidas en cada celda.
const unitsOf = (serie: ChartSeries) => serie.units ?? props.units

const headers = computed<Header[]>(() => [
  { title: t('dashboards.chart.datetime'), key: 't', align: 'start', sortable: false },
  ...props.series.map((serie, index) => ({
    title: unitsOf(serie) ? `${serie.name} (${unitsOf(serie)})` : serie.name,
    key: `s${index}`,
    align: 'end' as const,
    sortable: false,
  })),
])

function stampLabel(raw: string): string {
  const ms = toMillis(raw)
  return Number.isFinite(ms) ? formatDateTime(raw, session.timeZone) : raw
}

function byTimeDesc(a: string, b: string): number {
  const left = toMillis(a)
  const right = toMillis(b)
  if (Number.isFinite(left) && Number.isFinite(right)) return right - left
  return b.localeCompare(a)
}

const items = computed(() => {
  const stamps = new Set<string>()
  for (const serie of props.series) {
    for (const point of serie.points) if (point.v !== null) stamps.add(point.t)
  }

  const values = props.series.map((serie) => new Map(serie.points.map((p) => [p.t, p.v])))

  return [...stamps]
    .sort(byTimeDesc)
    .slice(0, props.limit)
    .map((stamp) => {
      const row: Record<string, string> = { t: stampLabel(stamp) }
      values.forEach((map, index) => {
        row[`s${index}`] = formatNumber(map.get(stamp) ?? null)
      })
      return row
    })
})
</script>

<template>
  <VDataTable
    :headers="headers"
    :items="items"
    :items-per-page="-1"
    :height="height"
    item-value="t"
    fixed-header
    hide-default-footer
    class="text-body-2"
  />
</template>
