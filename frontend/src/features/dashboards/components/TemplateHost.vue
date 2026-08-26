<script setup lang="ts">
import { computed, onErrorCaptured, ref } from 'vue'
import { t } from '@/i18n'
import type { Dashboard } from '@/types'
import { resolveTemplate } from '../templates/registry'

const props = defineProps<{ dashboard: Dashboard; typeId: string | null }>()

const failed = ref(false)
const descriptor = computed(() => resolveTemplate(props.typeId))

// Una plantilla se carga en diferido: si su fragmento no llega, sin esto la pantalla se queda en blanco.
onErrorCaptured(() => {
  failed.value = true
  return false
})
</script>

<template>
  <Suspense v-if="descriptor && !failed">
    <template #default>
      <component :is="descriptor.view" :dashboard="dashboard" />
    </template>
    <template #fallback>
      <div class="pa-2">
        <VSkeletonLoader type="card" />
      </div>
    </template>
  </Suspense>

  <VCard v-else class="pa-6">
    <div class="d-flex flex-column align-center text-center ga-3">
      <div class="icon-tile" style="width: 56px; height: 56px">
        <VIcon :icon="failed ? 'mdi-cloud-off-outline' : 'mdi-shape-outline'" size="28" />
      </div>

      <div class="text-subtitle-1 font-weight-medium">
        {{ failed ? t('dashboards.detail.templateFailed') : t('dashboards.detail.templateMissing') }}
      </div>

      <div class="text-body-2 text-medium-emphasis">
        {{ failed ? t('dashboards.detail.templateFailedHint') : t('dashboards.detail.templateMissingHint') }}
      </div>

      <VChip v-if="typeId" variant="tonal" class="text-caption">
        {{ t('dashboards.detail.templateId', { id: typeId }) }}
      </VChip>

      <div class="d-flex flex-wrap justify-center ga-3 mt-2">
        <VBtn to="/entidades" variant="tonal" color="primary" prepend-icon="mdi-database-outline">
          {{ t('dashboards.detail.goToEntities') }}
        </VBtn>
        <VBtn to="/paneles" variant="text" prepend-icon="mdi-arrow-left">
          {{ t('dashboards.detail.backToList') }}
        </VBtn>
      </div>
    </div>
  </VCard>
</template>
