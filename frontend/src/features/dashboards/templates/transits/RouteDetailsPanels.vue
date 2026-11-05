<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { BarChart, type ChartSeries } from '../../charts'
import ChartCard from '../shared/ChartCard.vue'
import { VISITOR_TYPES, type RouteDetail } from './routeDetails'

/** Duracion y tipo de visitante de los recorridos principales. */

const props = defineProps<{
  details: RouteDetail[]
  /** La plantilla avanzada reparte ademas los tránsitos por tipo de visitante. */
  withVisitors: boolean
  error?: string | null
}>()

const minutes = t('templates.transits.minutes')
const people = t('templates.transits.transitsUnit')

/**
 * Las categorias del eje son los rotulos de los recorridos: dos puntos distintos pueden llamarse
 * igual, y dos recorridos con el mismo rotulo se juntarian en una sola barra.
 */
const labels = computed(() => {
  const used = new Map<string, number>()
  return props.details.map((detail) => {
    const seen = (used.get(detail.label) ?? 0) + 1
    used.set(detail.label, seen)
    return seen > 1 ? `${detail.label} (${seen})` : detail.label
  })
})

const durationSeries = computed<ChartSeries[]>(() => [
  {
    name: t('templates.transits.durationAverage'),
    units: minutes,
    points: props.details.map((detail, i) => ({ t: labels.value[i], v: detail.averageMinutes })),
  },
  {
    name: t('templates.transits.durationMaximum'),
    units: minutes,
    points: props.details.map((detail, i) => ({ t: labels.value[i], v: detail.maximumMinutes })),
  },
])

const durationEmpty = computed(() =>
  props.details.every((detail) => detail.averageMinutes === null && detail.maximumMinutes === null),
)

const visitorSeries = computed<ChartSeries[]>(() =>
  VISITOR_TYPES.map(({ key }) => ({
    name: t(`templates.transits.visitor.${key}`),
    units: people,
    points: props.details.map((detail, i) => ({ t: labels.value[i], v: detail.visitors[key] })),
  })),
)

const visitorsEmpty = computed(() =>
  props.details.every((detail) => VISITOR_TYPES.every(({ key }) => detail.visitors[key] === null)),
)

const emptyText = computed(() => props.error || undefined)
</script>

<template>
  <VRow class="mt-0">
    <VCol cols="12" :lg="withVisitors ? 6 : 12">
      <ChartCard
        :title="t('templates.transits.durationTitle')"
        :subtitle="t('templates.transits.durationSubtitle')"
        :empty="!!error || durationEmpty"
        :empty-text="emptyText ?? t('templates.transits.durationEmpty')"
        empty-icon="mdi-timer-sand-empty"
        :footnote="t('templates.transits.durationFootnote')"
      >
        <BarChart
          :series="durationSeries"
          :units="minutes"
          :height="320"
          :category-title="t('templates.transits.routeColumn')"
        />
      </ChartCard>
    </VCol>

    <VCol v-if="withVisitors" cols="12" lg="6">
      <ChartCard
        :title="t('templates.transits.visitorsTitle')"
        :subtitle="t('templates.transits.visitorsSubtitle')"
        :empty="!!error || visitorsEmpty"
        :empty-text="emptyText ?? t('templates.transits.visitorsEmpty')"
        empty-icon="mdi-account-group-outline"
      >
        <BarChart
          :series="visitorSeries"
          :units="people"
          stacked
          :height="320"
          :category-title="t('templates.transits.routeColumn')"
        />
      </ChartCard>
    </VCol>
  </VRow>
</template>
