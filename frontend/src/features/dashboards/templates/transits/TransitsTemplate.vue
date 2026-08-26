<script setup lang="ts">
import { t } from '@/i18n'
import StatStrip from '../shared/StatStrip.vue'
import TemplateShell from '../shared/TemplateShell.vue'
import type { TemplateDashboard } from '../shared/types'
import TransitsPanels from './TransitsPanels.vue'
import { useTransits } from './useTransits'

const props = defineProps<{ dashboard: TemplateDashboard }>()

const tx = useTransits(props.dashboard)
</script>

<template>
  <TemplateShell
    v-model:preset="tx.data.preset.value"
    :loading="tx.data.loading.value || tx.busy.value"
    :error="tx.data.error.value || tx.seriesError.value"
    :range-caption="tx.data.rangeCaption.value"
    :empty="!!tx.emptyState.value"
    :empty-text="tx.emptyState.value?.text"
    :empty-hint="tx.emptyState.value?.hint"
    :empty-icon="tx.emptyState.value?.icon"
    :failed="tx.data.failed.value"
    :notice="tx.notice.value"
    @refresh="tx.refresh"
    @retry="tx.refresh"
  >
    <template #controls>
      <VSelect
        v-model="tx.measure.value"
        :items="tx.measureItems.value"
        :label="t('templates.transits.measureLabel')"
        min-width="240"
        max-width="380"
      />
      <VChip variant="tonal" size="small" prepend-icon="mdi-vector-polyline">
        {{ tx.modeLabel.value }}
      </VChip>
    </template>

    <StatStrip :items="tx.stats.value" />

    <TransitsPanels
      :nodes="tx.nodes.value"
      :routes="tx.ranked.value"
      :total-series="tx.totalSeries.value"
    />
  </TemplateShell>
</template>
