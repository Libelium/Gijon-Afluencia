<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
  /** Recuento de resultados: se muestra junto al titulo, atenuado. */
  count?: string
  backTo?: string
  icon?: string
}>()
</script>

<template>
  <div class="d-flex flex-wrap align-center ga-3 mb-6">
    <VBtn
      v-if="backTo"
      :to="backTo"
      icon="mdi-arrow-left"
      variant="text"
      density="comfortable"
      aria-label="Volver"
    />

    <VAvatar v-if="icon" color="surface-variant" rounded="lg" size="42">
      <VIcon :icon="icon" color="primary" size="22" />
    </VAvatar>

    <div class="flex-grow-1 min-w-0">
      <div class="d-flex align-center ga-2 flex-wrap">
        <h1 class="text-h6 font-weight-bold text-truncate mb-0">{{ title }}</h1>
        <span v-if="count" class="text-body-2 text-medium-emphasis">{{ count }}</span>
      </div>
      <div v-if="subtitle" class="text-body-2 text-medium-emphasis text-truncate">
        {{ subtitle }}
      </div>
    </div>

    <div class="d-flex flex-wrap align-center ga-3">
      <slot name="actions" />
    </div>
  </div>
</template>
