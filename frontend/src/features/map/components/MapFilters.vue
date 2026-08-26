<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'

/**
 * Los mismos controles sirven al panel flotante de escritorio y a la hoja inferior de movil,
 * asi que viven en un componente aparte en lugar de duplicarse en las dos ramas.
 */
const props = defineProps<{
  datamodels: string[]
  datamodelsLoading?: boolean
  withoutLocation: number
}>()

const search = defineModel<string>('search', { default: '' })
const datamodel = defineModel<string | null>('datamodel', { default: null })

const items = computed(() => props.datamodels.map((name) => ({ title: name, value: name })))
const filtered = computed(() => Boolean(search.value) || Boolean(datamodel.value))

const withoutLocationText = computed(() =>
  props.withoutLocation === 1
    ? t('map.withoutLocationOne')
    : t('map.withoutLocation', { n: formatNumber(props.withoutLocation) }),
)

function clear() {
  search.value = ''
  datamodel.value = null
}
</script>

<template>
  <div class="d-flex flex-column ga-3">
    <VTextField
      v-model="search"
      :label="t('map.search')"
      prepend-inner-icon="mdi-magnify"
      clearable
    />

    <VSelect
      v-model="datamodel"
      :items="items"
      :label="t('map.datamodel')"
      :loading="datamodelsLoading"
      :no-data-text="t('map.noDatamodels')"
      prepend-inner-icon="mdi-shape-outline"
      clearable
    />

    <div v-if="withoutLocation" class="d-flex align-start ga-2">
      <VIcon icon="mdi-information-outline" size="16" class="text-medium-emphasis" />
      <div class="text-caption text-medium-emphasis min-w-0">{{ withoutLocationText }}</div>
    </div>

    <div v-if="filtered" class="d-flex justify-end">
      <VBtn
        variant="tonal"
        color="secondary"
        size="small"
        prepend-icon="mdi-filter-remove-outline"
        @click="clear"
      >
        {{ t('map.clearFilters') }}
      </VBtn>
    </div>
  </div>
</template>
