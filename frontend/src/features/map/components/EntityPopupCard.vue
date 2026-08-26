<script setup lang="ts">
import { computed } from 'vue'
import type { Entity } from '@/types'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import { formatLatLng, type LatLng } from '../lib/geometry'

const props = defineProps<{ entity: Entity; latLng: LatLng }>()

defineEmits<{ open: [entity: Entity] }>()

const heading = computed(() => props.entity.name || urnTail(props.entity.urn))
const identifier = computed(() => urnTail(props.entity.urn))
// Sin nombre propio el titular ya es el identificador: repetirlo debajo no aporta nada.
const showIdentifier = computed(() => identifier.value !== heading.value)
</script>

<template>
  <div class="d-flex flex-column ga-3 pa-4">
    <div class="d-flex flex-column ga-1 pe-4">
      <div class="text-subtitle-2 font-weight-medium">{{ heading }}</div>
      <div
        v-if="showIdentifier"
        class="text-caption text-medium-emphasis text-truncate"
        :title="entity.urn"
      >
        {{ identifier }}
      </div>
    </div>

    <div class="d-flex flex-wrap align-center ga-2">
      <VChip v-if="entity.datamodel" variant="tonal" color="secondary" :text="entity.datamodel" />
      <span v-else class="text-caption text-medium-emphasis">{{ t('common.noValue') }}</span>
    </div>

    <div class="d-flex align-center ga-2" :title="t('map.coordinates')">
      <VIcon icon="mdi-map-marker-outline" size="16" class="text-medium-emphasis" />
      <span class="text-caption text-medium-emphasis">{{ formatLatLng(latLng) }}</span>
    </div>

    <VBtn color="primary" block append-icon="mdi-arrow-right" @click="$emit('open', entity)">
      {{ t('map.viewDetail') }}
    </VBtn>
  </div>
</template>
