<script setup lang="ts">
withDefaults(
  defineProps<{
    text: string
    hint?: string
    icon?: string
    type?: 'info' | 'warning'
  }>(),
  { type: 'info', icon: 'mdi-information-outline' },
)
</script>

<template>
  <VAlert :type="type" :icon="icon" density="comfortable" class="mb-6">
    <div class="text-body-2 font-weight-medium">{{ text }}</div>
    <div v-if="hint" class="text-body-2 mt-1">{{ hint }}</div>
  </VAlert>
</template>
