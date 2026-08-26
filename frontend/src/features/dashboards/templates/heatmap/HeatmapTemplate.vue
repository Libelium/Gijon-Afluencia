<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { DateTime } from 'luxon'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import { useChartTheme, type ChartPoint } from '../../charts'
import { autoAggregation, rangeHours, type AggregationOption, type DateRange } from '../../lib/range'
import { occupancyColor, occupancyColors } from '../../palette'
import { byDate, byHourOfDay, byWeekday, byWeekHour, kpisOf, levelRatio, peakOf, sumSeries } from '../shared/aggregate'
import { fetchSeries, REQUEST_BATCH, type SeriesRequest } from '../shared/series'
import ChartCard from '../shared/ChartCard.vue'
import MatrixHeatmap from '../shared/MatrixHeatmap.vue'
import PointMap, { type MapPoint } from '../shared/PointMap.vue'
import StatStrip from '../shared/StatStrip.vue'
import TemplateShell from '../shared/TemplateShell.vue'
import type { Point, TemplateDashboard } from '../shared/types'
import { useTemplateData, type TemplateContext } from '../shared/useTemplateData'
import YearCalendar from './YearCalendar.vue'

/** Tope de puntos: cada peticion cabe en un solo lote. */
const MAX_POINTS = REQUEST_BATCH

/**
 * Ventana de la matriz semanal. Cuatro semanas dejan cuatro observaciones en cada celda
 * dia-hora, que ya es una media con sentido, sin pedir un año entero de lecturas horarias.
 */
const MATRIX_DAYS = 28

/** Radio de los circulos del mapa, del punto sin apenas paso al mas transitado. */
const MIN_RADIUS = 7
const MAX_RADIUS = 22

const LEVEL_KEYS = ['levelVeryLow', 'levelLow', 'levelMedium', 'levelHigh', 'levelVeryHigh']

type Located = Point & { lat: number; lon: number }

const props = defineProps<{ dashboard: TemplateDashboard }>()

const data = useTemplateData({
  dashboard: props.dashboard,
  intent: 'occupancy',
  withCategories: false,
  defaultPreset: '30d',
})

const { isDark } = useChartTheme()

const busy = ref(false)
const seriesError = ref<string | null>(null)
const notice = ref<string | undefined>(undefined)

const usedPoints = ref<Point[]>([])
/** Series del rango completo: alimentan el total, el calendario y el mapa. */
const rangeByPoint = ref<Map<string, ChartPoint[]>>(new Map())
/** Series por horas de la ventana reciente: alimentan la matriz y las horas punta. */
const hourlySum = ref<ChartPoint[]>([])
const matrixDays = ref(MATRIX_DAYS)

function topByRecency(points: Point[], limit: number): Point[] {
  if (points.length <= limit) return points
  return [...points]
    .sort((a, b) => (b.entity.time_last_data ?? '').localeCompare(a.entity.time_last_data ?? ''))
    .slice(0, limit)
}

function windowOf(range: DateRange, days: number): DateRange {
  const end = DateTime.fromISO(range.end, { zone: 'utc' })
  const start = end.minus({ days }).toISO({ suppressMilliseconds: true })
  return { start: start ?? range.start, end: range.end }
}

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
    // Suelo de una hora: sin agregar, cada punto trae sus marcas y la suma entre puntos no seria comparable.
    const hourly: AggregationOption = { type: how, interval: 'PT1H' }
    const aggregation = autoAggregation(ctx.range, how) ?? hourly

    const series = await fetchSeries(requests, ctx.range, { aggregation })

    /**
     * La matriz necesita resolucion horaria, y el rango completo la pierde en cuanto pasa del
     * mes. Si ya viene por horas se reutiliza —pedirlo otra vez seria la misma peticion dos
     * veces—; si no, se pide aparte la ventana reciente, que es lo que cabe por horas.
     */
    const rangeDays = Math.max(1, Math.ceil(rangeHours(ctx.range) / 24))
    const reusable = aggregation.interval === hourly.interval
    const days = reusable ? rangeDays : Math.min(MATRIX_DAYS, rangeDays)
    const windowSeries = reusable
      ? series
      : await fetchSeries(requests, windowOf(ctx.range, days), { aggregation: hourly })

    usedPoints.value = points
    rangeByPoint.value = series
    hourlySum.value = sumSeries(points.map((p) => windowSeries.get(p.key) ?? []))
    matrixDays.value = days
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

/** Suma marca a marca de todos los puntos: el paso del conjunto, no el de un sensor. */
const rangeSum = computed(() =>
  sumSeries(usedPoints.value.map((p) => rangeByPoint.value.get(p.key) ?? [])),
)

const totalsByPoint = computed<Record<string, number | null>>(() => {
  const out: Record<string, number | null> = {}
  for (const point of usedPoints.value) out[point.key] = kpisOf(rangeByPoint.value.get(point.key) ?? []).total
  return out
})

const hourBuckets = computed(() => byHourOfDay(hourlySum.value, data.timeZone.value, 'mean'))
const weekdayBuckets = computed(() => byWeekday(hourlySum.value, data.timeZone.value, 'mean'))
const dayBuckets = computed(() => byDate(rangeSum.value, data.timeZone.value, 'sum'))

const peakHour = computed(() => peakOf(hourBuckets.value))
const peakDay = computed(() => peakOf(weekdayBuckets.value))

const topPoint = computed<Point | null>(() => {
  let best: Point | null = null
  let bestTotal = Number.NEGATIVE_INFINITY
  for (const point of usedPoints.value) {
    const total = totalsByPoint.value[point.key]
    if (total === null || total === undefined) continue
    if (total > bestTotal) {
      bestTotal = total
      best = point
    }
  }
  return best
})

function meanHint(value: number | null): string | undefined {
  return value === null ? undefined : t('templates.heatmap.statPeakHint', { value: formatNumber(value, 1) })
}

const stats = computed(() => [
  {
    key: 'total',
    label: t('templates.heatmap.statTotal'),
    value: formatNumber(kpisOf(rangeSum.value).total),
    hint: t('templates.heatmap.statTotalHint'),
    icon: 'mdi-sigma',
  },
  {
    key: 'peakHour',
    label: t('templates.heatmap.statPeakHour'),
    value: peakHour.value?.label ?? t('common.noValue'),
    hint: meanHint(peakHour.value?.value ?? null),
    icon: 'mdi-clock-outline',
  },
  {
    key: 'peakDay',
    label: t('templates.heatmap.statPeakDay'),
    value: peakDay.value?.label ?? t('common.noValue'),
    hint: meanHint(peakDay.value?.value ?? null),
    icon: 'mdi-calendar-week-outline',
  },
  {
    key: 'topPoint',
    label: t('templates.heatmap.statTopPoint'),
    value: topPoint.value?.label ?? t('common.noValue'),
    hint:
      topPoint.value && totalsByPoint.value[topPoint.value.key] !== null
        ? t('templates.heatmap.statTopPointHint', {
            value: formatNumber(totalsByPoint.value[topPoint.value.key]),
          })
        : undefined,
    icon: 'mdi-map-marker-star-outline',
  },
])

const weekSubtitle = computed(() =>
  matrixDays.value === 1
    ? t('templates.heatmap.weekSubtitleOne')
    : t('templates.heatmap.weekSubtitle', { days: matrixDays.value }),
)

const matrixCells = computed(() => byWeekHour(hourlySum.value, data.timeZone.value, 'mean'))
const matrixEmpty = computed(() => matrixCells.value.every((cell) => cell.value === null))

const locatedPoints = computed<Located[]>(() =>
  usedPoints.value.filter((p): p is Located => p.lat !== null && p.lon !== null),
)

const withoutLocation = computed(() => usedPoints.value.length - locatedPoints.value.length)

const maxTotal = computed<number | null>(() => {
  let max: number | null = null
  for (const point of usedPoints.value) {
    const total = totalsByPoint.value[point.key]
    if (total === null || total === undefined) continue
    if (max === null || total > max) max = total
  }
  return max
})

const mapPoints = computed<MapPoint[]>(() =>
  locatedPoints.value.map((point) => {
    const total = totalsByPoint.value[point.key] ?? null
    const ratio = levelRatio(total, maxTotal.value)
    return {
      key: point.key,
      lat: point.lat,
      lon: point.lon,
      label: point.label,
      text: formatNumber(total),
      color: occupancyColor(ratio, isDark.value),
      // El area del circulo crece con el total; el radio, con su raiz, para no exagerar la diferencia.
      radius: MIN_RADIUS + Math.sqrt(ratio) * (MAX_RADIUS - MIN_RADIUS),
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
  withoutLocation.value > 0
    ? t('templates.heatmap.mapWithoutLocation', { count: withoutLocation.value })
    : undefined,
)

const calendarDays = computed(() => dayBuckets.value.map((bucket) => ({ date: bucket.key, value: bucket.value })))
const calendarEmpty = computed(() => calendarDays.value.every((day) => day.value === null))
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
      <VCol cols="12">
        <ChartCard
          :title="t('templates.heatmap.weekTitle')"
          :subtitle="weekSubtitle"
          :empty="matrixEmpty"
        >
          <MatrixHeatmap
            :x-labels="hourBuckets.map((bucket) => bucket.label)"
            :y-labels="weekdayBuckets.map((bucket) => bucket.label)"
            :cells="matrixCells"
            :height="376"
            :x-label-interval="1"
            :value-label="t('templates.heatmap.hourMean')"
          />
        </ChartCard>
      </VCol>
    </VRow>

    <VRow class="mt-0">
      <VCol cols="12" md="5">
        <ChartCard
          :title="t('templates.heatmap.mapTitle')"
          :subtitle="t('templates.heatmap.mapSubtitle')"
          :empty="mapPoints.length === 0"
          :empty-text="t('templates.heatmap.emptyMap')"
          empty-icon="mdi-map-marker-off-outline"
          :footnote="mapFootnote"
        >
          <PointMap :points="mapPoints" :legend="legend" :height="320" />
        </ChartCard>
      </VCol>
      <VCol cols="12" md="7">
        <ChartCard
          :title="t('templates.heatmap.calendarTitle')"
          :subtitle="t('templates.heatmap.calendarSubtitle')"
          :empty="calendarEmpty"
          :footnote="t('templates.heatmap.calendarFootnote')"
        >
          <YearCalendar :days="calendarDays" :height="240" />
        </ChartCard>
      </VCol>
    </VRow>
  </TemplateShell>
</template>
