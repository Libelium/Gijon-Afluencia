<script setup lang="ts">
/** Indicador compacto para las tiras de cifras de las fichas de detalle. */
withDefaults(
  defineProps<{
    label: string
    value: string | number
    unit?: string
    icon?: string
    hint?: string
    /** Color del icono y del valor destacado. Por defecto, el acento del tema. */
    color?: string
  }>(),
  { color: 'primary' },
)
</script>

<template>
  <VCard class="flex-grow-1" min-width="150">
    <div class="d-flex align-center ga-3 pa-4">
      <div v-if="icon" class="icon-tile" style="width: 40px; height: 40px">
        <VIcon :icon="icon" :color="color" size="20" />
      </div>
      <div class="min-w-0">
        <div class="text-caption text-medium-emphasis text-uppercase font-weight-medium">
          {{ label }}
        </div>
        <div class="d-flex align-baseline ga-1">
          <span class="text-h6 font-weight-bold text-truncate">{{ value }}</span>
          <span v-if="unit" class="text-caption text-medium-emphasis">{{ unit }}</span>
        </div>
        <div v-if="hint" class="text-caption text-medium-emphasis text-truncate">{{ hint }}</div>
      </div>
    </div>
  </VCard>
</template>
