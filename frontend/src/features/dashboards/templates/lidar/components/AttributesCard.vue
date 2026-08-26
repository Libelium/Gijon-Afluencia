<script setup lang="ts">
import { computed } from 'vue'
import StateBlock from '@/components/StateBlock.vue'
import { describeMeasure } from '@/features/entities/lib/measures'
import { t } from '@/i18n'
import { formatDateTime } from '@/lib/format'
import type { Measure } from '@/types'
import { isoOf } from '../data'
import ConfidenceChip from './ConfidenceChip.vue'

const props = defineProps<{
  title: string
  attributes: Measure[]
  confidenceId?: string | null
  timeZone: string
  loading?: boolean
  error?: string | null
}>()

defineEmits<{ retry: [] }>()

const rows = computed(() =>
  props.attributes.map((m) => ({
    id: m.id,
    name: m.name,
    display: describeMeasure(m, props.timeZone),
    when: formatDateTime(isoOf(m.timestamp), props.timeZone),
    raw: m.value,
  })),
)

const headers = [
  { title: t('dashboards.lidar.analytics.attribute'), key: 'name' },
  { title: t('dashboards.lidar.analytics.attributeValue'), key: 'value' },
  { title: t('dashboards.lidar.analytics.attributeWhen'), key: 'when', width: 180 },
]
</script>

<template>
  <VCard class="table-card">
    <div class="d-flex align-center ga-2 px-4 pt-4 pb-3">
      <VIcon icon="mdi-tag-text-outline" size="18" class="text-medium-emphasis" />
      <span class="text-subtitle-2 font-weight-medium">{{ title }}</span>
    </div>
    <VDivider />
    <StateBlock
      :loading="loading"
      :error="error"
      :empty="!attributes.length"
      :empty-text="t('dashboards.lidar.analytics.noAttributes')"
      :empty-hint="t('dashboards.lidar.analytics.noAttributesHint')"
      empty-icon="mdi-tag-off-outline"
      skeleton="table"
      @retry="$emit('retry')"
    >
      <VDataTable :headers="headers" :items="rows" item-value="id" :items-per-page="-1" hide-default-footer :hover="false">
        <template #item.value="{ item }">
          <ConfidenceChip v-if="confidenceId && item.id === confidenceId" :value="item.raw" />
          <span
            v-else
            class="d-inline-block text-truncate"
            style="max-width: 420px"
            :title="item.display.full"
          >
            {{ item.display.text }}
          </span>
        </template>
      </VDataTable>
    </StateBlock>
  </VCard>
</template>
