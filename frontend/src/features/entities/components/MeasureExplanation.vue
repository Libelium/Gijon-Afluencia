<script setup lang="ts">
import { t } from '@/i18n'
import type { Measure } from '@/types'

defineProps<{ measure: Measure }>()
</script>

<template>
  <div class="d-flex flex-column ga-1">
    <div class="font-weight-medium">{{ measure.name }}</div>
    <div v-if="measure.description">{{ measure.description }}</div>
    <div v-else>{{ t('entities.measures.noDescription', { id: measure.id }) }}</div>
    <div v-if="measure.calculation">
      <span class="font-weight-medium">{{ t('entities.measures.calculation') }}:</span> {{ measure.calculation }}
    </div>
  </div>
</template>
