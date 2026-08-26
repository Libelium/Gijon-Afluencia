<script setup lang="ts">
import { computed, ref } from 'vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { formatDateTime, relativeFromNow } from '@/lib/format'
import type { EntityRef, Measure } from '@/types'
import { hasChartableHistory } from '../lib/measures'
import MeasureCard from './MeasureCard.vue'
import MeasureHistoryDialog from './MeasureHistoryDialog.vue'
import MeasureValueCell from './MeasureValueCell.vue'

const props = defineProps<{
  measures: Measure[]
  loading: boolean
  error: string | null
  readAt: string | null
  timeZone: string
  /** null = la entidad no tiene ambito de datos y no se le puede preguntar nada. */
  entityRef: EntityRef | null
}>()

defineEmits<{ refresh: [] }>()

interface Header {
  title: string
  key: string
  sortable: false
  align?: 'start' | 'center' | 'end'
  maxWidth?: number
  width?: number
}

const mode = ref<'cards' | 'table'>('cards')
const historyOpen = ref(false)
const historyMeasure = ref<Measure | null>(null)

const available = computed(() => props.entityRef !== null)

const headers: Header[] = [
  { title: t('entities.measures.name'), key: 'name', sortable: false, maxWidth: 320 },
  { title: t('entities.measures.value'), key: 'value', sortable: false },
  { title: t('entities.measures.timestamp'), key: 'timestamp', sortable: false },
  { title: '', key: 'history', sortable: false, align: 'end', width: 64 },
]

/** Una sola instancia del dialogo para toda la lista: no hace falta una por medida. */
function openHistory(measure: Measure) {
  historyMeasure.value = measure
  historyOpen.value = true
}

function chartable(measure: Measure): boolean {
  return available.value && hasChartableHistory(measure, props.timeZone)
}
</script>

<template>
  <VCard class="table-card">
    <div class="d-flex flex-wrap align-center ga-4 pa-4">
      <div class="flex-grow-1 min-w-0">
        <div class="text-subtitle-2 font-weight-medium">{{ t('entities.measures.title') }}</div>
        <div v-if="readAt" class="text-caption text-medium-emphasis">
          {{ t('entities.measures.readAt', { when: relativeFromNow(readAt, timeZone) }) }}
        </div>
      </div>

      <VBtnToggle v-model="mode" mandatory density="comfortable" variant="outlined" divided>
        <VBtn value="cards" icon="mdi-view-grid-outline" :aria-label="t('entities.measures.viewCards')" />
        <VBtn value="table" icon="mdi-table" :aria-label="t('entities.measures.viewTable')" />
      </VBtnToggle>

      <VBtn
        variant="tonal"
        color="secondary"
        prepend-icon="mdi-refresh"
        :loading="loading"
        :disabled="!available"
        @click="$emit('refresh')"
      >
        {{ t('common.refresh') }}
      </VBtn>
    </div>

    <VDivider />

    <VAlert v-if="!available" type="info" class="ma-4">
      {{ t('entities.detail.noScope') }}
    </VAlert>

    <StateBlock
      v-else
      :loading="loading && measures.length === 0"
      :error="error"
      :empty="!loading && !error && measures.length === 0"
      :empty-text="t('entities.measures.empty')"
      empty-icon="mdi-gauge-empty"
      :skeleton="mode === 'cards' ? 'card' : 'table'"
      @retry="$emit('refresh')"
    >
      <!-- La base flexible de 240px hace que la rejilla envuelva sola, sin consultas de medios. -->
      <div v-if="mode === 'cards'" class="d-flex flex-wrap ga-4 pa-4">
        <MeasureCard
          v-for="measure in measures"
          :key="measure.id"
          :measure="measure"
          :time-zone="timeZone"
          :history="available"
          style="flex: 1 1 240px"
          @history="openHistory(measure)"
        />
      </div>

      <VDataTable
        v-else
        :headers="headers"
        :items="measures"
        :sort-by="[]"
        item-value="id"
        hide-default-footer
        :items-per-page="-1"
      >
        <template #[`item.name`]="{ item }">
          <div class="py-1 min-w-0">
            <div class="font-weight-medium text-truncate" :title="item.name">{{ item.name }}</div>
            <div
              v-if="item.id !== item.name"
              class="text-caption text-medium-emphasis text-truncate"
              :title="item.id"
            >
              {{ item.id }}
            </div>
          </div>
        </template>

        <template #[`item.value`]="{ item }">
          <MeasureValueCell :measure="item" :time-zone="timeZone" />
        </template>

        <template #[`item.timestamp`]="{ item }">
          <VTooltip :text="formatDateTime(item.timestamp, timeZone)" location="top">
            <template #activator="{ props: tip }">
              <span v-bind="tip" class="text-body-2 text-medium-emphasis">
                {{ relativeFromNow(item.timestamp, timeZone) }}
              </span>
            </template>
          </VTooltip>
        </template>

        <template #[`item.history`]="{ item }">
          <VBtn
            v-if="chartable(item)"
            icon="mdi-chart-line"
            variant="text"
            density="comfortable"
            size="small"
            :aria-label="t('entities.history.open')"
            :title="t('entities.history.open')"
            @click="openHistory(item)"
          />
        </template>
      </VDataTable>
    </StateBlock>

    <MeasureHistoryDialog
      v-model="historyOpen"
      :measure="historyMeasure"
      :entity-ref="entityRef"
      :time-zone="timeZone"
    />
  </VCard>
</template>
