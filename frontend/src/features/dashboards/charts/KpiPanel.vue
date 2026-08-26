<script setup lang="ts">
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'
import { t } from '@/i18n'
import { formatDateTime, formatMeasure, formatNumber, relativeFromNow } from '@/lib/format'
import { useChartTheme } from './useChartTheme'
import { nonNull } from './chartOptions'
import type { ChartSeries } from './types'

const props = withDefaults(
  defineProps<{
    series: ChartSeries[]
    units?: string
    height?: number | string
  }>(),
  { height: 280 },
)

const { compact } = useChartTheme()
const session = useSessionStore()

const main = computed(() => props.series[0])
const points = computed(() => nonNull(main.value?.points ?? []))
const last = computed(() => points.value[points.value.length - 1] ?? null)
const previous = computed(() =>
  points.value.length > 1 ? points.value[points.value.length - 2] : null,
)

const units = computed(() => main.value?.units ?? props.units)
const figure = computed(() => (last.value ? formatNumber(last.value.v) : '—'))

/**
 * La cifra es el elemento principal, asi que no se trunca: cuando ocupa muchos digitos se baja
 * un peldano de la escala tipografica, que sigue leyendose como cifra destacada.
 */
const SIZES = ['text-h4', 'text-h5', 'text-h6'] as const

const figureClass = computed(() => {
  const length = figure.value.length + (units.value?.length ?? 0)
  const step = length > 14 ? 2 : length > 9 ? 1 : 0
  return SIZES[Math.min(SIZES.length - 1, step + (compact.value && length > 7 ? 1 : 0))]
})

/** Variacion frente al dato anterior. Sin color semantico: subir no siempre es bueno. */
const delta = computed(() => {
  if (!last.value || !previous.value || last.value.v === null || previous.value.v === null) {
    return null
  }
  const diff = last.value.v - previous.value.v
  const rounded = formatNumber(Math.abs(diff))
  if (rounded === '0') return { icon: 'mdi-approximately-equal', text: t('dashboards.kpi.noChange') }
  return {
    icon: diff > 0 ? 'mdi-arrow-top-right' : 'mdi-arrow-bottom-right',
    text: `${diff > 0 ? '+' : '−'}${rounded}`,
  }
})

const others = computed(() =>
  props.series.slice(1).map((serie) => {
    const valid = nonNull(serie.points)
    const point = valid[valid.length - 1]
    return {
      name: serie.name,
      value: point ? formatMeasure(point.v, serie.units ?? props.units) : '—',
    }
  }),
)

const timestamp = computed(() => formatDateTime(last.value?.t, session.timeZone))
const relative = computed(() => relativeFromNow(last.value?.t, session.timeZone))

const style = computed(() => ({
  minHeight: typeof props.height === 'number' ? `${props.height}px` : props.height,
}))
</script>

<template>
  <div class="d-flex flex-column justify-center ga-4 py-2" :style="style">
    <div class="min-w-0">
      <div
        v-if="main?.name"
        class="text-caption text-medium-emphasis text-uppercase font-weight-medium text-truncate mb-2"
        :title="main.name"
      >
        {{ main.name }}
      </div>

      <div class="d-flex flex-wrap align-baseline ga-2">
        <span class="font-weight-medium" :class="figureClass">{{ figure }}</span>
        <span v-if="units" class="text-body-2 text-medium-emphasis">{{ units }}</span>
        <VChip
          v-if="delta"
          variant="tonal"
          color="secondary"
          :title="t('dashboards.kpi.deltaTitle', { value: delta.text })"
        >
          <VIcon :icon="delta.icon" size="14" start />
          {{ delta.text }}
        </VChip>
      </div>

      <div class="d-flex flex-wrap align-center ga-2 text-caption text-medium-emphasis mt-4">
        <template v-if="last">
          <VIcon icon="mdi-clock-outline" size="14" />
          <span>{{ t('dashboards.kpi.lastData') }}: {{ timestamp }}</span>
          <span class="text-disabled">{{ relative }}</span>
        </template>
        <template v-else>
          <VIcon icon="mdi-clock-alert-outline" size="14" />
          <span>{{ t('dashboards.kpi.noRecent') }}</span>
        </template>
      </div>
    </div>

    <template v-if="others.length">
      <VDivider />
      <div class="d-flex flex-column ga-3">
        <div v-for="other in others" :key="other.name" class="d-flex align-center ga-4">
          <span class="text-body-2 text-medium-emphasis text-truncate flex-1-1-0" :title="other.name">
            {{ other.name }}
          </span>
          <span class="text-body-2 font-weight-medium flex-shrink-0">{{ other.value }}</span>
        </div>
      </div>
    </template>
  </div>
</template>
