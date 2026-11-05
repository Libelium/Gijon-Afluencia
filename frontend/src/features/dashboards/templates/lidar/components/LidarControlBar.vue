<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import type { Entity } from '@/types'
import RangeSelector from '../../../components/RangeSelector.vue'
import type { DateRange, RangePresetId } from '../../../lib/range'

const props = defineProps<{
  zones: Entity[]
  zoneId: number | null
  preset: RangePresetId
  custom: DateRange | null
  timeZone?: string
  showRange: boolean
  loading?: boolean
}>()

defineEmits<{
  'update:zoneId': [value: number | null]
  'update:preset': [value: RangePresetId]
  'update:custom': [value: DateRange | null]
  refresh: []
}>()

const zoneItems = computed(() => props.zones.map((z) => ({ value: z.id, title: z.name || urnTail(z.urn) })))
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
    <RangeSelector
      v-if="showRange"
      :preset="preset"
      :custom="custom"
      :time-zone="timeZone"
      @update:preset="$emit('update:preset', $event)"
      @update:custom="$emit('update:custom', $event)"
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
