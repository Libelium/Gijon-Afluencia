<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { formatDateTime } from '@/lib/format'
import type { Measure } from '@/types'
import { describeMeasure, measureTitle, timestampInfo } from '../lib/measures'

const props = defineProps<{
  measure: Measure
  timeZone?: string
  /** false cuando la entidad no admite consultas: sin ellas no hay historico que ofrecer. */
  history?: boolean
  /** La entidad es una prevision: su marca de tiempo es la hora prevista, no la de una lectura. */
  forecast?: boolean
}>()

const emit = defineEmits<{ history: [] }>()

const display = computed(() => describeMeasure(props.measure, props.timeZone))
const nameTitle = computed(() => measureTitle(props.measure))
const updatedText = computed(() => {
  const info = timestampInfo(props.measure.timestamp, props.timeZone)
  if (!info.future) return t('entities.measures.updated', { when: info.text })
  return t(props.forecast ? 'entities.measures.forecastFor' : 'entities.measures.updatedAt', { when: info.text })
})
const showHistory = computed(() => props.history && display.value.kind === 'number')
</script>

<template>
  <VCard class="d-flex flex-column ga-3 pa-4 min-w-0">
    <div class="d-flex align-start ga-2">
      <div class="flex-grow-1 min-w-0">
        <div class="text-subtitle-2 font-weight-medium text-truncate" :title="nameTitle">
          {{ measure.name }}
        </div>
        <div
          v-if="measure.description"
          class="text-caption text-medium-emphasis clamp-2"
          :title="measure.description"
        >
          {{ measure.description }}
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
      {{ updatedText }}
    </div>
  </VCard>
</template>

<style scoped>
/* Una descripcion larga no puede descuadrar la rejilla: se recorta a dos lineas. */
.clamp-2 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}
</style>
