<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import MapFilters from './MapFilters.vue'

const props = defineProps<{
  shown: number
  total: number
  withoutLocation: number
  datamodels: string[]
  datamodelsLoading?: boolean
}>()

const search = defineModel<string>('search', { default: '' })
const datamodel = defineModel<string | null>('datamodel', { default: null })

const { smAndDown } = useDisplay()

// En escritorio los filtros cuelgan del propio panel y se pueden plegar para despejar el mapa.
// En movil no caben: un panel desplegado taparia media pantalla, asi que van a una hoja inferior.
const open = ref(true)
const sheet = ref(false)

watch(smAndDown, () => {
  sheet.value = false
})

const expanded = computed(() => (smAndDown.value ? sheet.value : open.value))
const filtered = computed(() => Boolean(search.value) || Boolean(datamodel.value))

const countLabel = computed(() => {
  const short = smAndDown.value
  if (!props.shown) return t(short ? 'map.count.zeroShort' : 'map.count.zero')
  if (props.total > props.shown) {
    return t(short ? 'map.count.cappedShort' : 'map.count.capped', {
      n: formatNumber(props.shown),
      total: formatNumber(props.total),
    })
  }
  if (props.shown === 1) return t(short ? 'map.count.oneShort' : 'map.count.one')
  return t(short ? 'map.count.manyShort' : 'map.count.many', { n: formatNumber(props.shown) })
})

const toggleIcon = computed(() =>
  !smAndDown.value && open.value ? 'mdi-chevron-up' : 'mdi-tune-variant',
)

function toggle() {
  if (smAndDown.value) sheet.value = !sheet.value
  else open.value = !open.value
}
</script>

<template>
  <VCard elevation="6">
    <div class="d-flex align-center ga-3 pl-4 pr-2 py-2">
      <VIcon icon="mdi-map-marker-multiple-outline" size="20" class="text-medium-emphasis" />

      <div class="text-body-2 text-medium-emphasis flex-grow-1 min-w-0 text-truncate" :title="countLabel">
        {{ countLabel }}
      </div>

      <VBadge :model-value="filtered && !expanded" color="primary" dot offset-x="8" offset-y="8">
        <VBtn
          :icon="toggleIcon"
          variant="text"
          density="comfortable"
          :aria-label="expanded ? t('map.hideFilters') : t('map.showFilters')"
          @click="toggle"
        />
      </VBadge>
    </div>

    <VExpandTransition>
      <div v-if="!smAndDown && open">
        <VDivider />
        <MapFilters
          v-model:search="search"
          v-model:datamodel="datamodel"
          :datamodels="datamodels"
          :datamodels-loading="datamodelsLoading"
          :without-location="withoutLocation"
          class="pa-4"
        />
      </div>
    </VExpandTransition>
  </VCard>

  <VBottomSheet v-model="sheet">
    <VCard rounded="t-xl">
      <div class="d-flex align-center ga-3 pl-4 pr-2 py-3">
        <div class="text-subtitle-2 flex-grow-1 min-w-0 text-truncate">{{ t('map.filters') }}</div>
        <VBtn
          icon="mdi-close"
          variant="text"
          density="comfortable"
          :aria-label="t('common.close')"
          @click="sheet = false"
        />
      </div>

      <VDivider />

      <MapFilters
        v-model:search="search"
        v-model:datamodel="datamodel"
        :datamodels="datamodels"
        :datamodels-loading="datamodelsLoading"
        :without-location="withoutLocation"
        class="pa-4"
      />

      <div class="px-4 pb-4">
        <VBtn color="primary" block @click="sheet = false">{{ t('map.filtersApply') }}</VBtn>
      </div>
    </VCard>
  </VBottomSheet>
</template>
