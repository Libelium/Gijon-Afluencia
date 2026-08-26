<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import type { Panel } from '@/types'
import { ChartRenderer, chartVariant, resolveChartKind, type ChartData } from '../charts'
import { fetchPanelData, queryableSeries } from '../api/dashboards'
import type { DateRange } from '../lib/range'

/**
 * Cada grafico se carga por su cuenta y muestra su propio estado: un panel roto no puede
 * dejar en blanco el resto del cuadro de mando.
 */
const props = defineProps<{
  panel: Panel
  range: DateRange
  height: number
  timeZone?: string
  reloadKey?: number
  removable?: boolean
}>()

defineEmits<{ remove: [] }>()

const EMPTY: ChartData = { series: [] }

/** Estos dos imprimen la unidad junto a su cifra: repetirla en la cabecera sobra. */
const SELF_LABELLED_KINDS = ['kpi', 'gauge']

const data = ref<ChartData>(EMPTY)
const loading = ref(false)
const error = ref<string | null>(null)

const kind = computed(() => resolveChartKind(props.panel))
const variant = computed(() => chartVariant(props.panel))
const title = computed(() => props.panel.title || props.panel.chart?.title || t('dashboards.panel.untitled'))
const items = computed(() => queryableSeries(props.panel.series))
const supported = computed(() => kind.value !== 'unsupported')
const isTable = computed(() => kind.value === 'table')

const unique = (values: (string | undefined)[]) => [...new Set(values.filter(Boolean) as string[])]

const units = computed(() => {
  const found = unique(items.value.map((item) => item.serie.measure?.units))
  return found.length === 1 ? found[0] : undefined
})

/** Rotulo de la cabecera: la medida que se dibuja y su unidad, o cuantas series se comparan. */
const subtitle = computed(() => {
  const measures = unique(items.value.map((item) => item.serie.measure?.name))
  const parts: string[] = []
  if (measures.length === 1) parts.push(measures[0])
  else if (measures.length > 1) parts.push(t('dashboards.panel.seriesCount', { count: items.value.length }))
  if (units.value && !SELF_LABELLED_KINDS.includes(kind.value)) parts.push(units.value)
  return parts.join(' · ')
})

const empty = computed(
  () => items.value.length === 0 || !data.value.series.some((serie) => serie.points.length > 0),
)

const emptyText = computed(() =>
  items.value.length === 0 ? t('dashboards.panel.noSeries') : t('dashboards.panel.noData'),
)

const emptyHint = computed(() =>
  items.value.length === 0 ? undefined : t('dashboards.panel.noDataHint'),
)

const contentStyle = computed(() => ({ minHeight: `${props.height}px` }))

async function load() {
  if (!supported.value || items.value.length === 0) return
  loading.value = true
  error.value = null
  try {
    data.value = await fetchPanelData(props.panel, props.range, props.timeZone)
  } catch (e) {
    error.value = errorMessage(e)
    data.value = EMPTY
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.panel.id, props.range.start, props.range.end, props.reloadKey],
  () => void load(),
  { immediate: true },
)
</script>

<template>
  <VCard class="h-100 d-flex flex-column" :class="{ 'table-card': isTable }">
    <div class="d-flex align-start ga-3 px-4 py-3">
      <div class="min-w-0 flex-grow-1">
        <div class="text-subtitle-2 font-weight-medium text-truncate" :title="title">{{ title }}</div>
        <div v-if="subtitle" class="text-caption text-medium-emphasis text-truncate mt-1" :title="subtitle">
          {{ subtitle }}
        </div>
      </div>

      <VBtn
        v-if="removable"
        icon="mdi-delete-outline"
        variant="text"
        density="comfortable"
        size="small"
        class="flex-shrink-0"
        :aria-label="t('dashboards.panel.delete')"
        :title="t('dashboards.panel.delete')"
        @click="$emit('remove')"
      />
    </div>

    <VDivider />

    <div class="flex-grow-1" :class="isTable ? 'pa-0' : 'pa-4'">
      <div class="d-flex flex-column justify-center" :style="contentStyle">
        <ChartRenderer
          v-if="!supported"
          kind="unsupported"
          :data="EMPTY"
          :raw-type="panel.chart?.type"
          :height="height"
        />
        <StateBlock
          v-else
          :loading="loading"
          :error="error"
          :empty="empty"
          :empty-text="emptyText"
          :empty-hint="emptyHint"
          empty-icon="mdi-chart-line-variant"
          skeleton="card"
          @retry="load"
        >
          <ChartRenderer
            :kind="kind"
            :data="data"
            :units="units"
            :height="height"
            :area="variant.area"
            :stacked="variant.stacked"
          />
        </StateBlock>
      </div>
    </div>
  </VCard>
</template>
