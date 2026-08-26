<script setup lang="ts">
import { t } from '@/i18n'

/**
 * No es un error: el panel existe y esta bien configurado, solo que su tipo de grafico no se
 * dibuja en esta edicion. Se presenta como aviso informativo, sin color de alarma.
 */
withDefaults(
  defineProps<{
    /** Tipo original del panel; se muestra tal cual para poder identificarlo. */
    type?: string
    height?: number | string
  }>(),
  { height: 280 },
)
</script>

<template>
  <div
    class="d-flex flex-column align-center justify-center text-center ga-3 pa-6"
    :style="{ minHeight: typeof height === 'number' ? `${height}px` : height }"
  >
    <div class="icon-tile" style="width: 48px; height: 48px">
      <VIcon icon="mdi-chart-box-outline" size="24" />
    </div>

    <div class="min-w-0">
      <div class="text-subtitle-2 font-weight-medium">{{ t('dashboards.panel.unsupported') }}</div>
      <div class="text-body-2 text-medium-emphasis mt-1">
        {{ t('dashboards.panel.unsupportedHint') }}
      </div>
    </div>

    <VChip v-if="type" variant="tonal" class="text-caption">{{ type }}</VChip>
  </div>
</template>
