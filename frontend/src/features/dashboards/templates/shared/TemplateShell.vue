<script setup lang="ts">
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import RangeSelector from '../../components/RangeSelector.vue'
import type { DateRange, RangePresetId } from '../../lib/range'
import { AUTO_REFRESH_INTERVALS, useAutoRefresh } from './useAutoRefresh'

const props = withDefaults(
  defineProps<{
    preset: RangePresetId
    custom?: DateRange | null
    timeZone?: string
    loading?: boolean
    error?: string | null
    rangeCaption?: string
    empty?: boolean
    emptyText?: string
    emptyHint?: string
    emptyIcon?: string
    /** URN de los puntos cuya lectura en vivo ha fallado. */
    failed?: string[]
    /** Aviso de recorte: «Se muestran los N puntos con más afluencia». */
    notice?: string
  }>(),
  { emptyIcon: 'mdi-tray-remove' },
)

const emit = defineEmits<{
  'update:preset': [RangePresetId]
  'update:custom': [DateRange | null]
  refresh: []
  retry: []
}>()

// Pausa el auto-refresco mientras carga (no solapar peticiones) y con un rango fijo (no cambia).
const { minutes: autoRefresh } = useAutoRefresh(
  () => emit('refresh'),
  () => Boolean(props.loading) || props.custom != null,
)

const autoRefreshItems = AUTO_REFRESH_INTERVALS.map((minutes) => ({
  value: minutes,
  title: minutes === 0 ? t('templates.common.autoRefreshOff') : t('templates.common.autoRefreshEvery', { minutes }),
}))
</script>

<template>
  <div>
    <VCard class="mb-6">
      <div class="d-flex flex-wrap align-center ga-3 pa-4">
        <RangeSelector
          :preset="preset"
          :custom="custom"
          :time-zone="timeZone"
          @update:preset="emit('update:preset', $event)"
          @update:custom="emit('update:custom', $event)"
        />
        <!-- Selectores propios de cada plantilla: medida, categorias… -->
        <slot name="controls" />
        <VSpacer />
        <!-- Opt-in y con «Desactivado» por defecto: contenido que se actualiza solo (WCAG 2.2.2). -->
        <VSelect
          v-model="autoRefresh"
          :items="autoRefreshItems"
          :aria-label="t('templates.common.autoRefreshLabel')"
          :title="t('templates.common.autoRefreshLabel')"
          prepend-inner-icon="mdi-autorenew"
          density="compact"
          variant="outlined"
          hide-details
          min-width="160"
          max-width="190"
          class="flex-grow-0"
        />
        <VBtn
          icon="mdi-refresh"
          variant="tonal"
          :loading="loading"
          :aria-label="t('common.refresh')"
          :title="t('common.refresh')"
          @click="emit('refresh')"
        />
      </div>
    </VCard>

    <div v-if="rangeCaption" class="text-caption text-medium-emphasis mb-4">{{ rangeCaption }}</div>

    <VAlert v-if="failed?.length" type="warning" density="compact" class="mb-4">
      {{ t('templates.common.someFailed', { count: failed.length }) }}
    </VAlert>

    <VAlert v-if="notice" type="info" density="compact" class="mb-4">{{ notice }}</VAlert>

    <StateBlock
      :loading="loading"
      :error="error"
      :empty="empty"
      :empty-text="emptyText"
      :empty-hint="emptyHint"
      :empty-icon="emptyIcon"
      skeleton="card"
      @retry="emit('retry')"
    >
      <slot />
    </StateBlock>
  </div>
</template>
