<script setup lang="ts">
import { computed } from 'vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import { coordinatesText, type EntityLocation } from '../lib/location'
import CopyButton from './CopyButton.vue'
import EntityLocationMap from './EntityLocationMap.vue'

const props = defineProps<{
  location: EntityLocation | null
  loading?: boolean
}>()

const coordinates = computed(() => (props.location ? coordinatesText(props.location) : ''))

const detailed = computed(() =>
  props.location
    ? t('entities.detail.coordinates', {
        lat: formatNumber(props.location.lat, 5),
        lon: formatNumber(props.location.lon, 5),
      })
    : '',
)

const origin = computed(() => {
  const location = props.location
  if (!location) return ''
  if (location.source === 'entity') return t('entities.detail.locationFromEntity')
  return location.measureId
    ? t('entities.detail.locationFromMeasure', { measure: location.measureId })
    : t('entities.detail.locationFromMeasures')
})
</script>

<template>
  <VCard>
    <div class="d-flex align-center ga-2 px-4 pt-4 pb-3">
      <VIcon icon="mdi-map-marker-outline" size="18" class="text-medium-emphasis" />
      <span class="text-subtitle-2 font-weight-medium">{{ t('entities.detail.location') }}</span>
    </div>

    <VDivider />

    <StateBlock
      :loading="loading"
      :empty="!loading && !location"
      :empty-text="t('entities.detail.noLocation')"
      empty-icon="mdi-map-marker-off-outline"
      skeleton="card"
    >
      <div class="pa-4">
        <EntityLocationMap v-if="location" :lat="location.lat" :lon="location.lon" />

        <div class="d-flex flex-wrap align-center ga-2 mt-4 min-w-0">
          <div class="flex-grow-1 min-w-0">
            <div class="text-body-2 text-truncate" :title="detailed">{{ coordinates }}</div>
            <div class="text-caption text-medium-emphasis text-truncate" :title="origin">
              {{ origin }}
            </div>
          </div>
          <CopyButton :value="coordinates" :label="t('entities.detail.copyCoordinates')" />
        </div>
      </div>
    </StateBlock>
  </VCard>
</template>
