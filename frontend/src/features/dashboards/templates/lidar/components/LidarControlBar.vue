<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import type { Entity } from '@/types'
import { RANGE_PRESETS, type RangePresetId } from '../../../lib/range'

const props = defineProps<{
  zones: Entity[]
  zoneId: number | null
  preset: RangePresetId
  showRange: boolean
  loading?: boolean
}>()

defineEmits<{
  'update:zoneId': [value: number | null]
  'update:preset': [value: RangePresetId]
  refresh: []
}>()

const zoneItems = computed(() => props.zones.map((z) => ({ value: z.id, title: z.name || urnTail(z.urn) })))
const rangeItems = computed(() => RANGE_PRESETS.map((p) => ({ value: p.id, title: t(p.labelKey) })))
</script>

<template>
  <div class="d-flex flex-wrap align-center ga-3 mb-6">
    <VSelect
      :model-value="zoneId"
      :items="zoneItems"
      :label="t('dashboards.lidar.zone')"
      :placeholder="t('dashboards.lidar.zonePlaceholder')"
      :disabled="zones.length < 2"
      style="flex: 1 1 240px; max-width: 360px"
      @update:model-value="$emit('update:zoneId', $event)"
    />
    <VSelect
      v-if="showRange"
      :model-value="preset"
      :items="rangeItems"
      :label="t('dashboards.range.label')"
      min-width="190"
      max-width="220"
      @update:model-value="$emit('update:preset', $event)"
    />
    <VBtn
      icon="mdi-refresh"
      variant="tonal"
      :loading="loading"
      :aria-label="t('common.refresh')"
      :title="t('common.refresh')"
      @click="$emit('refresh')"
    />
  </div>
</template>
