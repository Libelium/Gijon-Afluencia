<script setup lang="ts">
import { t } from '@/i18n'

/** Estados compartidos por todas las pantallas: cargando, error y vacio. */
const props = withDefaults(
  defineProps<{
    loading?: boolean
    error?: string | null
    empty?: boolean
    emptyText?: string
    emptyHint?: string
    emptyIcon?: string
    skeleton?: 'table' | 'card' | 'text'
  }>(),
  { skeleton: 'table', emptyIcon: 'mdi-tray-remove' },
)

defineEmits<{ retry: [] }>()

const skeletonType = () =>
  props.skeleton === 'card' ? 'card' : props.skeleton === 'text' ? 'paragraph' : 'table-row@6'
</script>

<template>
  <div v-if="loading" class="pa-2">
    <VSkeletonLoader :type="skeletonType()" />
  </div>

  <VAlert v-else-if="error" type="error" class="ma-2">
    <div class="d-flex flex-wrap align-center ga-4">
      <span class="flex-grow-1 min-w-0">{{ error }}</span>
      <VBtn variant="tonal" color="error" size="small" @click="$emit('retry')">
        {{ t('common.retry') }}
      </VBtn>
    </div>
  </VAlert>

  <div v-else-if="empty" class="text-center py-12 px-4">
    <div class="icon-tile mx-auto mb-4" style="width: 56px; height: 56px">
      <VIcon :icon="emptyIcon" size="28" />
    </div>
    <div class="text-subtitle-2 font-weight-medium mb-1">
      {{ emptyText || t('common.empty') }}
    </div>
    <div v-if="emptyHint" class="text-body-2 text-medium-emphasis">{{ emptyHint }}</div>
    <div class="mt-5">
      <slot name="empty-action" />
    </div>
  </div>

  <slot v-else />
</template>
