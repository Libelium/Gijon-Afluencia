<script setup lang="ts">
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'

withDefaults(
  defineProps<{
    title: string
    subtitle?: string
    loading?: boolean
    error?: string | null
    empty?: boolean
    emptyText?: string
    emptyHint?: string
    emptyIcon?: string
    minHeight?: number
  }>(),
  { emptyIcon: 'mdi-chart-line-variant', minHeight: 300 },
)

defineEmits<{ retry: [] }>()
</script>

<template>
  <VCard class="h-100 d-flex flex-column">
    <div class="px-4 py-3 min-w-0">
      <div class="text-subtitle-2 font-weight-medium text-truncate" :title="title">{{ title }}</div>
      <div v-if="subtitle" class="text-caption text-medium-emphasis text-truncate mt-1" :title="subtitle">
        {{ subtitle }}
      </div>
    </div>
    <VDivider />
    <div class="flex-grow-1 pa-4">
      <div class="d-flex flex-column justify-center" :style="{ minHeight: `${minHeight}px` }">
        <StateBlock
          :loading="loading"
          :error="error"
          :empty="empty"
          :empty-text="emptyText || t('dashboards.panel.noData')"
          :empty-hint="emptyHint"
          :empty-icon="emptyIcon"
          skeleton="card"
          @retry="$emit('retry')"
        >
          <slot />
        </StateBlock>
      </div>
    </div>
  </VCard>
</template>
