<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { t } from '@/i18n'
import { formatNumber, urnTail } from '@/lib/format'
import type { PlacedEntity } from '../lib/geometry'
import { canSuggest } from '../lib/suggestions'

/**
 * Los mismos controles sirven al panel flotante de escritorio y a la hoja inferior de movil,
 * asi que viven en un componente aparte en lugar de duplicarse en las dos ramas.
 */
const props = defineProps<{
  datamodels: string[]
  datamodelsLoading?: boolean
  withoutLocation: number
  suggestions?: PlacedEntity[]
  suggestionsLoading?: boolean
}>()

const emit = defineEmits<{ pick: [item: PlacedEntity] }>()

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

// El desplegable de sugerencias se abre al escribir y se cierra al elegir una o con Escape. Con la
// flecha abajo el foco baja a la lista, como en un combo. El texto sigue filtrando el mapa como
// siempre: elegir una sugerencia no lo cambia.
const menu = ref(false)
const suggestable = computed(() => canSuggest(search.value))
const suggestionItems = computed(() =>
  (props.suggestions ?? []).map((item) => ({
    item,
    title: item.entity.name || urnTail(item.entity.urn),
    subtitle: item.entity.datamodel,
  })),
)

watch(search, (text) => {
  menu.value = canSuggest(text)
})

function onFocus() {
  if (suggestable.value) menu.value = true
}

function pick(item: PlacedEntity) {
  menu.value = false
  emit('pick', item)
}
</script>

<template>
  <div class="d-flex flex-column ga-3">
    <VTextField
      v-model="search"
      :label="t('map.search')"
      prepend-inner-icon="mdi-magnify"
      clearable
      aria-autocomplete="list"
      @focus="onFocus"
    >
      <VMenu
        v-model="menu"
        activator="parent"
        :disabled="!suggestable"
        :open-on-click="false"
        :close-on-content-click="false"
        location="bottom"
        max-height="320"
        content-class="map-suggestions"
      >
        <VList density="compact" :aria-label="t('map.suggestions.label')">
          <VListItem
            v-if="!suggestionItems.length"
            :title="suggestionsLoading ? t('map.suggestions.loading') : t('map.suggestions.empty')"
            disabled
          />
          <VListItem
            v-for="row in suggestionItems"
            :key="row.item.entity.id"
            :title="row.title"
            :subtitle="row.subtitle"
            prepend-icon="mdi-map-marker-outline"
            @click="pick(row.item)"
          />
        </VList>
      </VMenu>
    </VTextField>

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
