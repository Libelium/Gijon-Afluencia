<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { formatDateTime, relativeFromNow } from '@/lib/format'
import type { Measure } from '@/types'
import { describeMeasure } from '../lib/measures'

const props = defineProps<{
  measure: Measure
  timeZone?: string
  /** false cuando la entidad no admite consultas: sin ellas no hay historico que ofrecer. */
  history?: boolean
}>()

const emit = defineEmits<{ history: [] }>()

const display = computed(() => describeMeasure(props.measure, props.timeZone))
// Sin nombre propio el titular ya es el identificador: repetirlo debajo no aporta nada.
const showId = computed(() => props.measure.id !== props.measure.name)
const showHistory = computed(() => props.history && display.value.kind === 'number')
</script>

<template>
  <VCard class="d-flex flex-column ga-3 pa-4 min-w-0">
    <div class="d-flex align-start ga-2">
      <div class="flex-grow-1 min-w-0">
        <div class="text-subtitle-2 font-weight-medium text-truncate" :title="measure.name">
          {{ measure.name }}
        </div>
        <div
          v-if="showId"
          class="text-caption text-medium-emphasis text-truncate"
          :title="measure.id"
        >
          {{ measure.id }}
        </div>
      </div>

      <VBtn
        v-if="showHistory"
        icon="mdi-chart-line"
        variant="text"
        density="comfortable"
        size="small"
        class="flex-shrink-0"
        :aria-label="t('entities.history.open')"
        :title="t('entities.history.open')"
        @click="emit('history')"
      />
    </div>

    <div class="flex-grow-1 min-w-0">
      <VChip
        v-if="display.kind === 'boolean'"
        variant="tonal"
        :color="display.truthy ? 'success' : 'secondary'"
        :text="display.text"
      />

      <div v-else-if="display.kind === 'number'" class="d-flex align-baseline ga-1 min-w-0">
        <span class="text-h6 font-weight-bold text-truncate" :title="display.full">
          {{ display.text }}
        </span>
        <span v-if="display.units" class="text-caption text-medium-emphasis flex-shrink-0">
          {{ display.units }}
        </span>
      </div>

      <div v-else class="d-flex align-center ga-2 min-w-0">
        <VIcon
          v-if="display.kind === 'coordinates'"
          icon="mdi-map-marker-outline"
          size="16"
          class="text-medium-emphasis flex-shrink-0"
        />
        <span
          class="text-body-2 text-truncate"
          :class="display.kind === 'empty' ? 'text-medium-emphasis' : ''"
          :title="display.full"
        >
          {{ display.text }}
        </span>
      </div>
    </div>

    <div
      class="text-caption text-medium-emphasis text-truncate"
      :title="formatDateTime(measure.timestamp, timeZone)"
    >
      {{ t('entities.measures.updated', { when: relativeFromNow(measure.timestamp, timeZone) }) }}
    </div>
  </VCard>
</template>
