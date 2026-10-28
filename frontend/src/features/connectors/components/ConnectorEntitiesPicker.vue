<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import { searchEntities, type EntityOption } from '@/features/dashboards/api/catalog'
import type { LinkedEntity } from '../types'

/**
 * Seleccion de varias entidades. Las elegidas se muestran aparte, como chips que se quitan con
 * el teclado, y el desplegable solo sirve para buscar y anadir: con decenas de miles de
 * entidades paginadas en el servidor, mezclar ambas cosas en el mismo control las perderia.
 */
const props = defineProps<{ modelValue: LinkedEntity[] }>()
const emit = defineEmits<{ 'update:modelValue': [LinkedEntity[]] }>()

const SEARCH_DEBOUNCE = 350
const PAGE_SIZE = 25

const search = ref('')
const options = ref<EntityOption[]>([])
const count = ref(0)
const page = ref(1)
const loading = ref(false)
/** El desplegable se vacia tras cada eleccion: lo elegido se ve en los chips. */
const picked = ref<EntityOption | null>(null)

const selectedIds = computed(() => new Set(props.modelValue.map((entity) => entity.id)))
const available = computed(() => options.value.filter((option) => !selectedIds.value.has(option.id)))
const hasMore = computed(() => options.value.length < count.value)

let sequence = 0
let timer: ReturnType<typeof setTimeout> | undefined

async function load(reset: boolean) {
  const target = reset ? 1 : page.value + 1
  const current = ++sequence
  loading.value = true
  try {
    const result = await searchEntities({
      search: search.value.trim() || undefined,
      page: target,
      limit: PAGE_SIZE,
    })
    if (current !== sequence) return
    page.value = target
    count.value = result.count
    options.value = reset ? result.rows : [...options.value, ...result.rows]
  } catch {
    if (current !== sequence) return
    if (reset) {
      options.value = []
      count.value = 0
    }
  } finally {
    if (current === sequence) loading.value = false
  }
}

watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(() => void load(true), SEARCH_DEBOUNCE)
})

watch(picked, (option) => {
  if (!option) return
  emit('update:modelValue', [...props.modelValue, { id: option.id, urn: option.urn }])
  picked.value = null
  search.value = ''
})

function remove(id: number) {
  emit('update:modelValue', props.modelValue.filter((entity) => entity.id !== id))
}

onMounted(() => void load(true))
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div class="d-flex flex-column ga-3">
    <VAutocomplete
      v-model="picked"
      v-model:search="search"
      :items="available"
      return-object
      item-title="name"
      item-value="id"
      :loading="loading"
      :label="t('connectors.form.entityPicker')"
      :no-data-text="loading ? t('common.loading') : t('connectors.form.entityEmpty')"
      no-filter
      prepend-inner-icon="mdi-magnify"
    >
      <template #item="{ item, props: itemProps }">
        <VListItem v-bind="itemProps" :subtitle="`${urnTail(item.raw.urn)} · ${item.raw.datamodel}`" />
      </template>

      <template v-if="hasMore" #append-item>
        <VDivider />
        <div class="pa-2">
          <VBtn variant="text" color="primary" block :loading="loading" @click="load(false)">
            {{ t('connectors.form.entityMore', { shown: options.length, total: count }) }}
          </VBtn>
        </div>
      </template>
    </VAutocomplete>

    <div v-if="modelValue.length" class="d-flex flex-wrap ga-2" role="list">
      <VChip
        v-for="entity in modelValue"
        :key="entity.id"
        role="listitem"
        closable
        :close-label="`${t('common.clear')} ${urnTail(entity.urn)}`"
        :title="entity.urn"
        @click:close="remove(entity.id)"
      >
        {{ urnTail(entity.urn) }}
      </VChip>
    </div>
    <p v-else class="text-body-2 text-medium-emphasis mb-0">
      {{ t('connectors.settings.noEntities') }}
    </p>
  </div>
</template>
