<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import { BarChart, hasData, PieChart, type ChartPoint } from '../../charts'
import { byHourOfDay, kpisOf, sumSeries } from '../shared/aggregate'
import { isCumulative } from '../shared/discovery'
import { fetchSeries, type SeriesRequest } from '../shared/series'
import ChartCard from '../shared/ChartCard.vue'
import MatrixHeatmap from '../shared/MatrixHeatmap.vue'
import StatStrip from '../shared/StatStrip.vue'
import TemplateShell from '../shared/TemplateShell.vue'
import type { Category, Kpis, MatrixCell, Point, TemplateDashboard } from '../shared/types'
import { useTemplateData, type TemplateContext } from '../shared/useTemplateData'

const MAX_POINTS = 8
const MAX_CATEGORIES = 12

const HOUR_LABELS = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')} h`)

const props = defineProps<{ dashboard: TemplateDashboard }>()

const data = useTemplateData({
  dashboard: props.dashboard,
  intent: 'occupancy',
  withCategories: true,
  defaultPreset: '7d',
})

const busy = ref(false)
const seriesError = ref<string | null>(null)
const notice = ref<string | undefined>(undefined)

const categories = ref<Category[]>([])
const usedPoints = ref<Point[]>([])
/** Series sin sumar, indexadas `${point.key}|${category.measureId}`: alimentan la comparativa y la tabla cruzada. */
const seriesMap = ref<Map<string, ChartPoint[]>>(new Map())
const byCategory = ref<Record<string, ChartPoint[]>>({})
const kpisByCategory = ref<Record<string, Kpis>>({})
const grandTotal = ref<number | null>(null)

function topByRecency(points: Point[], limit: number): Point[] {
  if (points.length <= limit) return points
  return [...points]
    .sort((a, b) => (b.entity.time_last_data ?? '').localeCompare(a.entity.time_last_data ?? ''))
    .slice(0, limit)
}

function sumTotals(values: (number | null)[]): number | null {
  const nums = values.filter((v): v is number => v !== null)
  return nums.length ? nums.reduce((a, b) => a + b, 0) : null
}

async function load(ctx: TemplateContext | null) {
  if (!ctx) return
  busy.value = true
  seriesError.value = null
  try {
    const cats = ctx.categories.length > MAX_CATEGORIES ? ctx.categories.slice(0, MAX_CATEGORIES) : ctx.categories
    notice.value =
      ctx.categories.length > MAX_CATEGORIES
        ? t('templates.classification.limited', { total: ctx.categories.length })
        : undefined

    const points = topByRecency(ctx.points, MAX_POINTS)

    const requests: SeriesRequest[] = []
    for (const point of points) {
      for (const category of cats) {
        requests.push({
          key: `${point.key}|${category.measureId}`,
          ref: point.ref,
          measureId: category.measureId,
          cumulative: isCumulative(category.measureId),
        })
      }
    }

    const series = await fetchSeries(requests, ctx.range)

    const nextByCategory: Record<string, ChartPoint[]> = {}
    const nextKpis: Record<string, Kpis> = {}
    for (const category of cats) {
      const perPoint = points.map((point) => series.get(`${point.key}|${category.measureId}`) ?? [])
      const summed = sumSeries(perPoint)
      nextByCategory[category.measureId] = summed
      nextKpis[category.measureId] = kpisOf(summed)
    }

    categories.value = cats
    usedPoints.value = points
    seriesMap.value = series
    byCategory.value = nextByCategory
    kpisByCategory.value = nextKpis
    grandTotal.value = sumTotals(cats.map((c) => nextKpis[c.measureId].total))
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

const topCategory = computed<Category | null>(() => {
  let best: Category | null = null
  let bestValue = Number.NEGATIVE_INFINITY
  for (const category of categories.value) {
    const total = kpisByCategory.value[category.measureId]?.total
    if (total !== null && total !== undefined && total > bestValue) {
      bestValue = total
      best = category
    }
  }
  return best
})

const topPercent = computed<number | null>(() => {
  const category = topCategory.value
  if (!category || !grandTotal.value) return null
  const total = kpisByCategory.value[category.measureId]?.total
  return total === null || total === undefined ? null : (total / grandTotal.value) * 100
})

const stats = computed(() => [
  {
    key: 'total',
    label: t('templates.classification.statTotal'),
    value: formatNumber(grandTotal.value),
    icon: 'mdi-sigma',
  },
  {
    key: 'top',
    label: t('templates.classification.statTop'),
    value: topCategory.value?.label ?? t('common.noValue'),
    hint:
      topPercent.value !== null
        ? t('templates.classification.statTopHint', { percent: formatNumber(topPercent.value, 1) })
        : undefined,
    icon: 'mdi-trophy-outline',
  },
  {
    key: 'count',
    label: t('templates.classification.statCount'),
    value: categories.value.length,
    hint: t('templates.classification.statCountHint'),
    icon: 'mdi-shape-outline',
  },
  {
    key: 'points',
    label: t('templates.classification.statPointsCompared'),
    value: usedPoints.value.length,
    icon: 'mdi-map-marker-multiple-outline',
  },
])

/** Ver ClassificationTemplate.vue: sin unidad fiable por categoria, se dibuja sin sufijo. */
const donutSeries = computed(() =>
  categories.value.map((c) => ({
    name: c.label,
    points: [{ t: data.range.value.end, v: kpisByCategory.value[c.measureId]?.total ?? 0 }],
  })),
)

const donutEmpty = computed(() => grandTotal.value === null || grandTotal.value === 0)

const compareSeries = computed(() =>
  categories.value.map((c) => ({
    name: c.label,
    points: usedPoints.value.map((p) => ({
      t: p.label,
      v: kpisOf(seriesMap.value.get(`${p.key}|${c.measureId}`) ?? []).total,
    })),
  })),
)

const compareEmpty = computed(() => !hasData(compareSeries.value))

const matrixCells = computed<MatrixCell[]>(() => {
  const cells: MatrixCell[] = []
  categories.value.forEach((category, y) => {
    const buckets = byHourOfDay(byCategory.value[category.measureId] ?? [], data.timeZone.value, 'mean')
    buckets.forEach((bucket, x) => cells.push({ x, y, value: bucket.value }))
  })
  return cells
})

const matrixHeight = computed(() => Math.max(220, 44 * categories.value.length + 96))
const matrixEmpty = computed(() => matrixCells.value.every((c) => c.value === null))

interface CrossRow {
  key: string
  label: string
  __isTotal: boolean
  __total: number | null
  [measureId: string]: unknown
}

const crossHeaders = computed(() => [
  { title: t('templates.classification.colPoint'), key: 'label', align: 'start' as const, sortable: true },
  ...categories.value.map((c) => ({ title: c.label, key: c.measureId, align: 'end' as const, sortable: true })),
  { title: t('templates.classification.colTotal'), key: '__total', align: 'end' as const, sortable: true },
])

const crossRows = computed<CrossRow[]>(() => {
  const pointRows = usedPoints.value.map((p) => {
    const row: CrossRow = { key: p.key, label: p.label, __isTotal: false, __total: null }
    let rowTotal: number | null = null
    for (const category of categories.value) {
      const total = kpisOf(seriesMap.value.get(`${p.key}|${category.measureId}`) ?? []).total
      row[category.measureId] = total
      if (total !== null) rowTotal = (rowTotal ?? 0) + total
    }
    row.__total = rowTotal
    return row
  })

  const totalsRow: CrossRow = {
    key: '__totals',
    label: t('templates.classification.rowTotal'),
    __isTotal: true,
    __total: grandTotal.value,
  }
  for (const category of categories.value) totalsRow[category.measureId] = kpisByCategory.value[category.measureId]?.total ?? null

  return [...pointRows, totalsRow]
})
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
        v-model="data.categoryIds.value"
        :items="data.measureItems.value"
        :label="t('templates.classification.categoriesLabel')"
        multiple
        chips
        closable-chips
        clearable
        min-width="260"
        max-width="420"
        :hint="t('templates.classification.categoriesHint')"
        persistent-hint
      />
    </template>

    <StatStrip :items="stats" />

    <VRow>
      <VCol cols="12" md="4">
        <ChartCard
          :title="t('templates.classification.donutTitle')"
          :subtitle="t('templates.classification.donutSubtitle')"
          :empty="donutEmpty"
        >
          <PieChart :series="donutSeries" :height="320" />
        </ChartCard>
      </VCol>
      <VCol cols="12" md="8">
        <ChartCard
          :title="t('templates.classification.compareTitle')"
          :subtitle="t('templates.classification.compareSubtitle')"
          :empty="compareEmpty"
        >
          <BarChart :series="compareSeries" :stacked="false" :height="340" />
        </ChartCard>
      </VCol>
    </VRow>

    <VRow class="mt-0">
      <VCol cols="12">
        <ChartCard
          :title="t('templates.classification.hourTitle')"
          :subtitle="t('templates.classification.hourSubtitle')"
          :empty="matrixEmpty"
        >
          <MatrixHeatmap
            :x-labels="HOUR_LABELS"
            :y-labels="categories.map((c) => c.label)"
            :cells="matrixCells"
            :height="matrixHeight"
            :x-label-interval="1"
            :value-label="t('templates.classification.hourMean')"
          />
        </ChartCard>
      </VCol>
    </VRow>

    <VRow class="mt-0">
      <VCol cols="12">
        <ChartCard :title="t('templates.classification.crossTitle')" class="table-card">
          <div class="overflow-x-auto">
            <VDataTable :headers="crossHeaders" :items="crossRows" :items-per-page="-1" hide-default-footer item-value="key" class="text-body-2">
              <template #[`item.label`]="{ item }">
                <span :class="{ 'font-weight-bold': item.__isTotal }">{{ item.label }}</span>
              </template>
              <template v-for="category in categories" :key="category.measureId" #[`item.${category.measureId}`]="{ item }">
                <span :class="{ 'font-weight-bold': item.__isTotal }">{{ formatNumber(item[category.measureId]) }}</span>
              </template>
              <template #[`item.__total`]="{ item }">
                <span :class="{ 'font-weight-bold': item.__isTotal }">{{ formatNumber(item.__total) }}</span>
              </template>
            </VDataTable>
          </div>
        </ChartCard>
      </VCol>
    </VRow>
  </TemplateShell>
</template>
