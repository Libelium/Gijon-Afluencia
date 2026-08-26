<script setup lang="ts">
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'

withDefaults(
  defineProps<{
    title: string
    subtitle?: string
    empty?: boolean
    emptyText?: string
    emptyIcon?: string
    /** Nota al pie del gráfico: cómo se ha calculado el dato. */
    footnote?: string
  }>(),
  { emptyIcon: 'mdi-chart-box-outline' },
)
</script>

<template>
  <VCard class="h-100">
    <div class="pa-4 pb-2">
      <div class="text-subtitle-2 font-weight-medium">{{ title }}</div>
      <div v-if="subtitle" class="text-caption text-medium-emphasis mt-1">{{ subtitle }}</div>
    </div>
    <div class="px-4 pb-4">
      <StateBlock
        :empty="empty"
        :empty-text="emptyText || t('dashboards.panel.noData')"
        :empty-hint="empty ? t('dashboards.panel.noDataHint') : undefined"
        :empty-icon="emptyIcon"
      >
        <slot />
      </StateBlock>
      <div v-if="footnote" class="text-caption text-medium-emphasis mt-3">{{ footnote }}</div>
    </div>
  </VCard>
</template>
