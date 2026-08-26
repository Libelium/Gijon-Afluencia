<script setup lang="ts">
import { computed } from 'vue'
import type { Measure } from '@/types'
import { describeMeasure } from '../lib/measures'

const props = defineProps<{ measure: Measure; timeZone?: string }>()

const display = computed(() => describeMeasure(props.measure, props.timeZone))
</script>

<template>
  <VChip
    v-if="display.kind === 'boolean'"
    variant="tonal"
    :color="display.truthy ? 'success' : 'secondary'"
    :text="display.text"
  />

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
    <span v-if="display.units" class="text-caption text-medium-emphasis flex-shrink-0">
      {{ display.units }}
    </span>
  </div>
</template>
