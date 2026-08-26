<script setup lang="ts">
import { t } from '@/i18n'
</script>

<template>
  <div class="text-center py-16">
    <div class="icon-tile mx-auto mb-5" style="width: 64px; height: 64px">
      <VIcon icon="mdi-lock-outline" size="32" />
    </div>
    <h1 class="text-h6 font-weight-bold mb-2">{{ t('error.403.title') }}</h1>
    <p class="text-body-2 text-medium-emphasis mb-7">{{ t('error.403.text') }}</p>
    <VBtn color="primary" to="/entidades" prepend-icon="mdi-arrow-left">
      {{ t('error.goHome') }}
    </VBtn>
  </div>
</template>
