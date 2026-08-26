<script setup lang="ts">
import { computed } from 'vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import LineChart from './LineChart.vue'
import BarChart from './BarChart.vue'
import PieChart from './PieChart.vue'
import GaugeChart from './GaugeChart.vue'
import KpiPanel from './KpiPanel.vue'
import DataTableChart from './DataTableChart.vue'
import UnsupportedPanel from './UnsupportedPanel.vue'
import { hasData } from './chartOptions'
import type { ChartData, ChartKind } from './types'

const props = withDefaults(
  defineProps<{
    kind: ChartKind
    data: ChartData
    /** Solo para uso aislado: dentro de una tarjeta el titulo lo pone la propia tarjeta. */
    title?: string
    units?: string
    loading?: boolean
    error?: string | null
    /** Tipo original, solo para el aviso de tipo no disponible. */
    rawType?: string
    height?: number | string
    area?: boolean
    stacked?: boolean
    scale?: 'neutral' | 'occupancy'
    limit?: number
  }>(),
  { height: 280, area: false, stacked: false, scale: 'neutral', limit: 50 },
)

defineEmits<{ retry: [] }>()

const series = computed(() => props.data?.series ?? [])

/** El aviso de tipo no disponible se muestra siempre: no depende de que haya datos. */
const empty = computed(() => props.kind !== 'unsupported' && !hasData(series.value))
</script>

<template>
  <div>
    <div v-if="title" class="text-subtitle-2 text-truncate mb-3" :title="title">{{ title }}</div>

    <StateBlock
      :loading="loading"
      :error="error"
      :empty="empty"
      skeleton="card"
      empty-icon="mdi-chart-line-variant"
      :empty-text="t('dashboards.panel.noData')"
      :empty-hint="t('dashboards.panel.noDataHint')"
      @retry="$emit('retry')"
    >
      <LineChart
        v-if="kind === 'line'"
        :series="series"
        :units="units"
        :area="area"
        :height="height"
      />
      <BarChart
        v-else-if="kind === 'bar'"
        :series="series"
        :units="units"
        :stacked="stacked"
        :height="height"
      />
      <PieChart v-else-if="kind === 'pie'" :series="series" :units="units" :height="height" />
      <GaugeChart
        v-else-if="kind === 'gauge'"
        :series="series"
        :units="units"
        :scale="scale"
        :height="height"
      />
      <KpiPanel v-else-if="kind === 'kpi'" :series="series" :units="units" :height="height" />
      <DataTableChart
        v-else-if="kind === 'table'"
        :series="series"
        :units="units"
        :limit="limit"
        :height="height"
      />
      <UnsupportedPanel v-else :type="rawType" :height="height" />
    </StateBlock>
  </div>
</template>
