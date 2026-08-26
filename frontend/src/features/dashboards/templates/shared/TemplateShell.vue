<script setup lang="ts">
import { computed } from 'vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { RANGE_PRESETS, type RangePresetId } from '../../lib/range'

withDefaults(
  defineProps<{
    preset: RangePresetId
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
  refresh: []
  retry: []
}>()

const rangeItems = computed(() => RANGE_PRESETS.map((p) => ({ value: p.id, title: t(p.labelKey) })))
</script>

<template>
  <div>
    <VCard class="mb-6">
      <div class="d-flex flex-wrap align-center ga-3 pa-4">
        <VSelect
          :model-value="preset"
          :items="rangeItems"
          :label="t('dashboards.range.label')"
          min-width="180"
          max-width="220"
          @update:model-value="emit('update:preset', $event)"
        />
        <!-- Selectores propios de cada plantilla: medida, categorias… -->
        <slot name="controls" />
        <VSpacer />
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
