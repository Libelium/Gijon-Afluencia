<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import { hasData, PieChart } from '../../charts'
import ChartCard from '../shared/ChartCard.vue'
import StatStrip from '../shared/StatStrip.vue'
import TemplateShell from '../shared/TemplateShell.vue'
import type { TemplateDashboard } from '../shared/types'
import { useClassificationData } from './useClassificationData'
import StackedAreaChart from './StackedAreaChart.vue'

const props = defineProps<{ dashboard: TemplateDashboard }>()

const {
  data,
  busy,
  seriesError,
  notice,
  categories,
  byCategory,
  kpisByCategory,
  grandTotal,
  topCategory,
  topPercent,
  donutSeries,
  donutEmpty,
  refreshAll,
} = useClassificationData(props.dashboard)

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
