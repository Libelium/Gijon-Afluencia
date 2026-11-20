<script setup lang="ts">
import { t } from '@/i18n'

defineProps<{ expanded: boolean }>()
defineEmits<{ toggle: [] }>()
</script>

<template>
  <VBtn
    :icon="expanded ? 'mdi-arrow-collapse' : 'mdi-arrow-expand'"
    variant="text"
    density="comfortable"
    size="small"
    class="flex-shrink-0"
    :aria-label="expanded ? t('dashboards.panel.collapse') : t('dashboards.panel.expand')"
    :title="expanded ? t('dashboards.panel.collapse') : t('dashboards.panel.expand')"
    @click="$emit('toggle')"
  />
</template>
