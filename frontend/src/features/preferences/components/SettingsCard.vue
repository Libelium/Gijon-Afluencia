<script setup lang="ts">
import { t } from '@/i18n'

/** Tarjeta tematica del formulario de preferencias: rotulo, linea de ayuda y sus campos. */
defineProps<{
  icon: string
  title: string
  help: string
  pending?: boolean
}>()
</script>

<template>
  <VCard>
    <VCardText class="pa-4 pa-sm-6">
      <div class="d-flex flex-wrap align-center ga-3">
        <VIcon :icon="icon" size="20" class="text-primary" />
        <h2 class="text-subtitle-2 flex-grow-1 min-w-0">{{ title }}</h2>
        <VChip v-if="pending" color="warning" variant="tonal">
          {{ t('preferences.pendingTag') }}
        </VChip>
      </div>

      <p class="text-body-2 text-medium-emphasis mt-2 mb-5">{{ help }}</p>

      <slot />
    </VCardText>
  </VCard>
</template>
