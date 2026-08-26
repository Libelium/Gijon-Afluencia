<script setup lang="ts">
import StatTile from '@/components/StatTile.vue'

export interface StatItem {
  key: string
  label: string
  value: string | number
  unit?: string
  icon?: string
  hint?: string
  color?: string
}

defineProps<{ items: StatItem[] }>()
</script>

<template>
  <div class="d-flex flex-wrap ga-3 mb-6">
    <StatTile
      v-for="item in items"
      :key="item.key"
      :label="item.label"
      :value="item.value"
      :unit="item.unit"
      :icon="item.icon"
      :hint="item.hint"
      :color="item.color"
    />
  </div>
</template>
