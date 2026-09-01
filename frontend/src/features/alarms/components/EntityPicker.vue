<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import { searchEntities, type EntityOption } from '@/features/dashboards/api/catalog'

const props = defineProps<{ modelValue: EntityOption | null }>()
const emit = defineEmits<{ 'update:modelValue': [EntityOption | null] }>()

const SEARCH_DEBOUNCE = 350
/** Tamano de pagina del desplegable. Corto a proposito: es una lista para elegir, no para leer. */
const PAGE_SIZE = 25

const search = ref('')
const options = ref<EntityOption[]>([])
const count = ref(0)
const page = ref(1)
const loading = ref(false)

const selected = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const hasMore = computed(() => options.value.length < count.value)

let sequence = 0
let timer: ReturnType<typeof setTimeout> | undefined

/**
 * El listado se pagina en el servidor: hay decenas de miles de entidades y traerlas todas para
 * filtrarlas en el navegador no es viable. Por eso el desplegable lleva `no-filter`.
 */
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

watch(search, (value) => {
  // Al elegir una opcion, Vuetify escribe su titulo en el texto de busqueda. Sin esta guarda,
  // cada seleccion lanzaria una busqueda mas por un termino que ya no interesa a nadie.
  if (selected.value && value === selected.value.name) return
  clearTimeout(timer)
  timer = setTimeout(() => void load(true), SEARCH_DEBOUNCE)
})

// La primera pagina se trae al montar: un desplegable vacio hasta que alguien acierte a
// escribir dos letras parece roto, y ademas obliga a saber de antemano que se busca.
onMounted(() => void load(true))

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <VAutocomplete
    v-model="selected"
    v-model:search="search"
    :items="options"
    return-object
    item-title="name"
    item-value="urn"
    :loading="loading"
    :label="t('alarms.form.entity')"
    :no-data-text="loading ? t('common.loading') : t('alarms.form.entityEmpty')"
    no-filter
    clearable
    prepend-inner-icon="mdi-magnify"
  >
    <template #item="{ item, props: itemProps }">
      <VListItem v-bind="itemProps" :subtitle="`${urnTail(item.raw.urn)} · ${item.raw.datamodel}`" />
    </template>

    <!-- Paginacion explicita en lugar de scroll infinito: el numero de entidades es
         informacion util por si el filtro que se busca es otro. -->
    <template v-if="hasMore" #append-item>
      <VDivider />
      <div class="pa-2">
        <VBtn variant="text" color="primary" block :loading="loading" @click="load(false)">
          {{ t('alarms.form.entityMore', { shown: options.length, total: count }) }}
        </VBtn>
      </div>
    </template>
  </VAutocomplete>
</template>
