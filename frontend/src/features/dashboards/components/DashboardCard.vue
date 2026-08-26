<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import type { Dashboard } from '@/types'
import { resolveTemplate } from '../templates/registry'

const props = defineProps<{ dashboard: Dashboard }>()

const descriptor = computed(() => resolveTemplate(props.dashboard.templateType))
const isTemplate = computed(() => !!props.dashboard.templateType)

const panelCount = computed(() => props.dashboard.panels?.length ?? 0)

const panelsLabel = computed(() => {
  if (!panelCount.value) return t('dashboards.card.noPanels')
  return panelCount.value === 1
    ? t('dashboards.card.onePanel')
    : t('dashboards.card.panels', { count: panelCount.value })
})

const description = computed(
  () => props.dashboard.description?.trim() || t('dashboards.card.noDescription'),
)
</script>

<template>
  <VCard
    :to="`/paneles/${dashboard.id}`"
    class="card-link h-100 d-flex flex-column pa-4 ga-4"
    :aria-label="t('dashboards.card.open', { name: dashboard.name })"
  >
    <div class="d-flex align-start ga-3">
      <div class="icon-tile" style="width: 40px; height: 40px">
        <VIcon icon="mdi-view-dashboard-outline" size="22" />
      </div>

      <div class="min-w-0 flex-grow-1">
        <div class="text-subtitle-1 font-weight-medium clamp-2" :title="dashboard.name">
          {{ dashboard.name }}
        </div>
      </div>

      <VIcon icon="mdi-chevron-right" size="20" class="text-medium-emphasis flex-shrink-0" />
    </div>

    <div class="text-body-2 text-medium-emphasis clamp-2 flex-grow-1">{{ description }}</div>

    <div class="d-flex flex-wrap align-center ga-2">
      <VChip v-if="!isTemplate" variant="tonal" prepend-icon="mdi-chart-box-outline">{{ panelsLabel }}</VChip>
      <VChip v-if="!isTemplate" variant="tonal" color="secondary" prepend-icon="mdi-tune-variant">
        {{ t('dashboards.card.custom') }}
      </VChip>
      <VChip v-else-if="descriptor" variant="tonal" color="primary" :prepend-icon="descriptor.icon">
        {{ descriptor.label }}
      </VChip>
      <VChip
        v-else
        variant="tonal"
        color="warning"
        prepend-icon="mdi-help-circle-outline"
        :title="t('dashboards.card.unknownTemplateTitle', { id: dashboard.templateType ?? '' })"
      >
        {{ t('dashboards.card.unknownTemplate') }}
      </VChip>
    </div>
  </VCard>
</template>

<style scoped>
/* Todas las tarjetas de la rejilla tienen que medir lo mismo, y para eso el titulo y la
   descripcion han de ocupar un numero fijo de lineas. No hay utilidad de recorte a dos
   lineas: text-truncate solo recorta una. */
.clamp-2 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}
</style>
