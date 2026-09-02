<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { formatDateTime, formatNumber } from '@/lib/format'
import { BarChart, hasData, LineChart, useChartTheme, type ChartPoint, type ChartSeries } from '../../charts'
import { autoAggregation, type AggregationOption } from '../../lib/range'
import { occupancyColor, occupancyColors } from '../../palette'
import { byHourOfDay, kpisOf, levelRatio, sumSeries, topByRecency } from '../shared/aggregate'
import { fetchSeries, REQUEST_BATCH, type SeriesRequest } from '../shared/series'
import ChartCard from '../shared/ChartCard.vue'
import PointMap, { type MapPoint } from '../shared/PointMap.vue'
import StatStrip from '../shared/StatStrip.vue'
import TemplateShell from '../shared/TemplateShell.vue'
import type { Kpis, Point, TemplateDashboard } from '../shared/types'
import { useTemplateData, type TemplateContext } from '../shared/useTemplateData'

/** Tope de puntos: cabe en un solo lote de peticiones y la tabla comparativa sigue leyendose. */
const MAX_POINTS = REQUEST_BATCH

/** Lineas de la evolucion. Con mas, la leyenda ocupa mas que el grafico y los colores se repiten. */
const MAX_TREND_SERIES = 8

/** Radio fijo: en este mapa el nivel lo comunica el color, no el tamaño. */
const MARKER_RADIUS = 11

/** Un paso de la escala de ocupacion, en el mismo orden que sus colores. */
const LEVEL_KEYS = ['levelVeryLow', 'levelLow', 'levelMedium', 'levelHigh', 'levelVeryHigh']

type Located = Point & { lat: number; lon: number }

const props = defineProps<{ dashboard: TemplateDashboard }>()

const data = useTemplateData({
  dashboard: props.dashboard,
  intent: 'occupancy',
  withCategories: false,
  defaultPreset: '7d',
})

const { isDark } = useChartTheme()

const busy = ref(false)
const seriesError = ref<string | null>(null)
const notice = ref<string | undefined>(undefined)

const usedPoints = ref<Point[]>([])
const seriesByPoint = ref<Map<string, ChartPoint[]>>(new Map())

async function load(ctx: TemplateContext | null) {
  if (!ctx) return
  busy.value = true
  seriesError.value = null
  try {
    const points = topByRecency(ctx.points, MAX_POINTS)
    notice.value =
      ctx.points.length > MAX_POINTS
        ? t('templates.common.limitedPoints', { shown: points.length, total: ctx.points.length })
        : undefined

    const requests: SeriesRequest[] = points.map((point) => ({
      key: point.key,
      ref: point.ref,
      measureId: ctx.measureId,
      cumulative: ctx.cumulative,
    }))

    const how = ctx.cumulative ? 'max' : 'mean'
    /**
     * Suelo de una hora en la agregacion: sin agregar, cada punto trae sus propias marcas de
     * tiempo y la suma entre puntos dejaria de ser comparable (cada instante tendria el valor
     * de un solo sensor). Con bucket horario todos los puntos caen en la misma rejilla.
     */
    const hourly: AggregationOption = { type: how, interval: 'PT1H' }
    const aggregation = autoAggregation(ctx.range, how) ?? hourly

    const series = await fetchSeries(requests, ctx.range, { aggregation })

    usedPoints.value = points
    seriesByPoint.value = series
  } catch (e) {
    seriesError.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

watch(() => data.context.value, load, { immediate: true })

async function refreshAll() {
  await data.reload()
}

const kpisByPoint = computed<Record<string, Kpis>>(() => {
  const out: Record<string, Kpis> = {}
  for (const point of usedPoints.value) out[point.key] = kpisOf(seriesByPoint.value.get(point.key) ?? [])
  return out
})

/**
 * Ocupacion del conjunto: se suman los puntos marca a marca y se resumen despues. Sumar los
 * resumenes de cada punto daria un maximo que nunca ha existido, porque cada uno lo alcanza a
 * una hora distinta.
 */
const totalKpis = computed<Kpis>(() =>
  kpisOf(sumSeries(usedPoints.value.map((p) => seriesByPoint.value.get(p.key) ?? []))),
)

const withData = computed(() => usedPoints.value.filter((p) => kpisByPoint.value[p.key]?.at !== null).length)

const stats = computed(() => [
  {
    key: 'current',
    label: t('templates.occupancy.statCurrent'),
    value: formatNumber(totalKpis.value.current),
    hint: totalKpis.value.at
      ? t('templates.occupancy.statCurrentHint', { at: formatDateTime(totalKpis.value.at, data.timeZone.value) })
      : undefined,
    icon: 'mdi-account-group-outline',
  },
  {
    key: 'max',
    label: t('templates.occupancy.statMax'),
    value: formatNumber(totalKpis.value.max),
    hint: totalKpis.value.maxAt
      ? t('templates.occupancy.statMaxHint', { at: formatDateTime(totalKpis.value.maxAt, data.timeZone.value) })
      : undefined,
    icon: 'mdi-arrow-up-bold-outline',
  },
  {
    key: 'mean',
    label: t('templates.occupancy.statMean'),
    value: formatNumber(totalKpis.value.mean, 1),
    icon: 'mdi-chart-bell-curve-cumulative',
  },
  {
    key: 'points',
    label: t('templates.occupancy.statPoints'),
    value: `${withData.value} / ${data.points.value.length}`,
    hint: t('templates.occupancy.statPointsHint'),
    icon: 'mdi-map-marker-multiple-outline',
  },
])

const locatedPoints = computed<Located[]>(() =>
  usedPoints.value.filter((p): p is Located => p.lat !== null && p.lon !== null),
)

const withoutLocation = computed(() => usedPoints.value.length - locatedPoints.value.length)

/** El nivel es relativo al punto mas ocupado del periodo: no hay aforo maximo declarado. */
const maxCurrent = computed<number | null>(() => {
  let max: number | null = null
  for (const point of usedPoints.value) {
    const current = kpisByPoint.value[point.key]?.current
    if (current === null || current === undefined) continue
    if (max === null || current > max) max = current
  }
  return max
})

const mapPoints = computed<MapPoint[]>(() =>
  locatedPoints.value.map((point) => {
    const kpis = kpisByPoint.value[point.key]
    return {
      key: point.key,
      lat: point.lat,
      lon: point.lon,
      label: point.label,
      text: formatNumber(kpis?.current ?? null),
      color: occupancyColor(levelRatio(kpis?.current ?? null, maxCurrent.value), isDark.value),
      radius: MARKER_RADIUS,
    }
  }),
)

const legend = computed(() =>
  occupancyColors(isDark.value).map((color, index) => ({
    color,
    label: t(`templates.common.${LEVEL_KEYS[index]}`),
  })),
)

const mapFootnote = computed(() =>
  [
    t('templates.occupancy.mapFootnote'),
    withoutLocation.value > 0
      ? t('templates.occupancy.mapWithoutLocation', { count: withoutLocation.value })
      : '',
  ]
    .filter((text) => text !== '')
    .join(' '),
)

function meanRank(kpis?: Kpis): number {
  return kpis?.mean ?? Number.NEGATIVE_INFINITY
}

/** Los puntos con mas ocupacion media son los que se dibujan cuando hay mas de los que caben. */
const trendPoints = computed<Point[]>(() =>
  [...usedPoints.value]
    .sort((a, b) => {
      const left = meanRank(kpisByPoint.value[a.key])
      const right = meanRank(kpisByPoint.value[b.key])
      return right === left ? a.label.localeCompare(b.label, 'es') : right - left
    })
    .slice(0, MAX_TREND_SERIES),
)

const trendSeries = computed<ChartSeries[]>(() =>
  trendPoints.value.map((point) => ({
    name: point.label,
    points: seriesByPoint.value.get(point.key) ?? [],
  })),
)

const trendFootnote = computed(() =>
  usedPoints.value.length > MAX_TREND_SERIES
    ? t('templates.occupancy.trendFootnote', { count: MAX_TREND_SERIES })
    : undefined,
)

const hourBuckets = computed(() => {
  // Todas las lecturas de todos los puntos en un solo saco: la media es la del punto medio a esa hora.
  const all = usedPoints.value.flatMap((p) => seriesByPoint.value.get(p.key) ?? [])
  return byHourOfDay(all, data.timeZone.value, 'mean')
})

const hourSeries = computed<ChartSeries[]>(() => [
  {
    name: t('templates.occupancy.hourlySeries'),
    points: hourBuckets.value.map((bucket) => ({ t: bucket.label, v: bucket.value })),
  },
])

interface Row {
  key: string
  label: string
  current: number | null
  max: number | null
  mean: number | null
  at: string | null
}

const headers = [
  { title: t('templates.occupancy.colPoint'), key: 'label', align: 'start' as const, sortable: true },
  { title: t('templates.occupancy.colCurrent'), key: 'current', align: 'end' as const, sortable: true },
  { title: t('templates.occupancy.colMax'), key: 'max', align: 'end' as const, sortable: true },
  { title: t('templates.occupancy.colMean'), key: 'mean', align: 'end' as const, sortable: true },
  { title: t('templates.occupancy.colAt'), key: 'at', align: 'end' as const, sortable: true },
]

const rows = computed<Row[]>(() =>
  usedPoints.value.map((point) => {
    const kpis = kpisByPoint.value[point.key]
    return {
      key: point.key,
      label: point.label,
      current: kpis?.current ?? null,
      max: kpis?.max ?? null,
      mean: kpis?.mean ?? null,
      at: kpis?.at ?? null,
    }
  }),
)
</script>

<template>
  <TemplateShell
    v-model:preset="data.preset.value"
    :loading="data.loading.value || busy"
    :error="data.error.value || seriesError"
    :range-caption="data.rangeCaption.value"
    :empty="!!data.emptyState.value"
    :empty-text="data.emptyState.value?.text"
    :empty-hint="data.emptyState.value?.hint"
    :empty-icon="data.emptyState.value?.icon"
    :failed="data.failed.value"
    :notice="notice"
    @refresh="refreshAll"
    @retry="refreshAll"
  >
    <template #controls>
      <VSelect
        v-model="data.measureId.value"
        :items="data.measureItems.value"
        :label="t('templates.common.measureLabel')"
        min-width="220"
        max-width="320"
      />
    </template>

    <StatStrip :items="stats" />

    <VRow>
      <VCol cols="12" md="5">
        <ChartCard
          :title="t('templates.occupancy.mapTitle')"
          :subtitle="t('templates.occupancy.mapSubtitle')"
          :empty="mapPoints.length === 0"
          :empty-text="t('templates.occupancy.emptyMap')"
          empty-icon="mdi-map-marker-off-outline"
          :footnote="mapFootnote"
        >
          <PointMap :points="mapPoints" :legend="legend" :height="340" />
        </ChartCard>
      </VCol>
      <VCol cols="12" md="7">
        <ChartCard
          :title="t('templates.occupancy.trendTitle')"
          :empty="!hasData(trendSeries)"
          :footnote="trendFootnote"
        >
          <LineChart :series="trendSeries" :height="340" />
        </ChartCard>
      </VCol>
    </VRow>

    <VRow class="mt-0">
      <VCol cols="12">
        <ChartCard
          :title="t('templates.occupancy.hourlyTitle')"
          :subtitle="t('templates.occupancy.hourlySubtitle')"
          :empty="!hasData(hourSeries)"
        >
          <BarChart :series="hourSeries" :height="300" />
        </ChartCard>
      </VCol>
    </VRow>

    <VRow class="mt-0">
      <VCol cols="12">
        <ChartCard :title="t('templates.occupancy.tableTitle')" class="table-card">
          <div class="overflow-x-auto">
            <VDataTable
              :headers="headers"
              :items="rows"
              :items-per-page="-1"
              hide-default-footer
              item-value="key"
              class="text-body-2"
            >
              <template #[`item.current`]="{ item }">{{ formatNumber(item.current) }}</template>
              <template #[`item.max`]="{ item }">{{ formatNumber(item.max) }}</template>
              <template #[`item.mean`]="{ item }">{{ formatNumber(item.mean, 1) }}</template>
              <template #[`item.at`]="{ item }">{{ formatDateTime(item.at, data.timeZone.value) }}</template>
            </VDataTable>
          </div>
        </ChartCard>
      </VCol>
    </VRow>
  </TemplateShell>
</template>
