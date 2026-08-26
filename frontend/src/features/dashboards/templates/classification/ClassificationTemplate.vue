<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import { hasData, PieChart, type ChartPoint } from '../../charts'
import { kpisOf, sumSeries } from '../shared/aggregate'
import { isCumulative } from '../shared/discovery'
import { fetchSeries, type SeriesRequest } from '../shared/series'
import ChartCard from '../shared/ChartCard.vue'
import StatStrip from '../shared/StatStrip.vue'
import TemplateShell from '../shared/TemplateShell.vue'
import type { Category, Kpis, Point, TemplateDashboard } from '../shared/types'
import { useTemplateData, type TemplateContext } from '../shared/useTemplateData'
import StackedAreaChart from './StackedAreaChart.vue'

/** Tope de puntos combinados con las categorias: mas alla de esto la peticion no aguanta. */
const MAX_POINTS = 8
const MAX_CATEGORIES = 12

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
const byCategory = ref<Record<string, ChartPoint[]>>({})
const kpisByCategory = ref<Record<string, Kpis>>({})
const grandTotal = ref<number | null>(null)

/** Los puntos con dato mas reciente ganan cuando hay mas de los que la peticion aguanta. */
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
    label: t('templates.classification.statPoints'),
    value: data.context.value?.points.length ?? 0,
    icon: 'mdi-map-marker-multiple-outline',
  },
])

/**
 * Sin una unidad comun fiable por categoria (el contrato de `Category` no la trae), los
 * graficos de esta plantilla se dibujan sin sufijo de unidad. Ver `deviations`.
 */
const donutSeries = computed(() =>
  categories.value.map((c) => ({
    name: c.label,
    points: [{ t: data.range.value.end, v: kpisByCategory.value[c.measureId]?.total ?? 0 }],
  })),
)

const donutEmpty = computed(() => grandTotal.value === null || grandTotal.value === 0)

const stackSeries = computed(() =>
  categories.value.map((c) => ({ name: c.label, points: byCategory.value[c.measureId] ?? [] })),
)

const stackEmpty = computed(() => !hasData(stackSeries.value))

interface Row {
  key: string
  label: string
  total: number | null
  share: number | null
  mean: number | null
  max: number | null
}

const headers = [
  { title: t('templates.classification.colCategory'), key: 'label', align: 'start' as const, sortable: true },
  { title: t('templates.classification.colTotal'), key: 'total', align: 'end' as const, sortable: true },
  { title: t('templates.classification.colShare'), key: 'share', align: 'end' as const, sortable: true },
  { title: t('templates.classification.colMean'), key: 'mean', align: 'end' as const, sortable: true },
  { title: t('templates.classification.colMax'), key: 'max', align: 'end' as const, sortable: true },
]

const rows = computed<Row[]>(() =>
  categories.value.map((c) => {
    const kpis = kpisByCategory.value[c.measureId]
    const total = kpis?.total ?? null
    const share = grandTotal.value ? (total !== null ? (total / grandTotal.value) * 100 : null) : null
    return { key: c.measureId, label: c.label, total, share, mean: kpis?.mean ?? null, max: kpis?.max ?? null }
  }),
)

function shareText(share: number | null): string {
  return share === null ? t('common.noValue') : `${formatNumber(share, 1)} %`
}
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
          :title="t('templates.classification.stackTitle')"
          :subtitle="t('templates.classification.stackSubtitle')"
          :empty="stackEmpty"
          :footnote="t('templates.classification.stackFootnote')"
        >
          <StackedAreaChart :series="stackSeries" :height="320" />
        </ChartCard>
      </VCol>
    </VRow>

    <VRow class="mt-0">
      <VCol cols="12">
        <ChartCard :title="t('templates.classification.tableTitle')" class="table-card">
          <VDataTable :headers="headers" :items="rows" :items-per-page="-1" hide-default-footer item-value="key" class="text-body-2">
            <template #[`item.total`]="{ item }">{{ formatNumber(item.total) }}</template>
            <template #[`item.share`]="{ item }">{{ shareText(item.share) }}</template>
            <template #[`item.mean`]="{ item }">{{ formatNumber(item.mean) }}</template>
            <template #[`item.max`]="{ item }">{{ formatNumber(item.max) }}</template>
          </VDataTable>
        </ChartCard>
      </VCol>
    </VRow>
  </TemplateShell>
</template>
