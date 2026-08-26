<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '@/api/http'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { formatNumber, relativeFromNow, urnTail } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import { dataScopeLabel, listDataScopes, type DataScope } from '@/api/scopes'
import type { Entity } from '@/types'
import { getLastDataTimes, listDatamodels, listEntities } from '../api/entities'
import { datamodelIcon } from '../lib/datamodel'

const SEARCH_DEBOUNCE = 400

const router = useRouter()
const session = useSessionStore()

const search = ref('')
const searchTerm = ref('')
const types = ref<string[]>([])
const dataScope = ref<DataScope | null>(null)
const page = ref(1)
const perPage = ref(25)

const rows = ref<Entity[]>([])
const total = ref(0)
const pending = ref(true)
const error = ref<string | null>(null)

const datamodels = ref<string[]>([])
const dataScopes = ref<DataScope[]>([])
const lastData = ref<Record<string, string>>({})

const filtered = computed(
  () => !!searchTerm.value || types.value.length > 0 || !!dataScope.value,
)
const firstLoad = computed(() => pending.value && rows.value.length === 0)

const countText = computed(() =>
  total.value === 1
    ? t('entities.list.countOne')
    : t('entities.list.count', { count: formatNumber(total.value, 0) }),
)

/** Sin nombre propio el titular ya es el identificador: repetirlo debajo no aporta nada. */
function subIdentifier(item: Entity): string | null {
  const tail = urnTail(item.urn)
  return item.name && tail !== item.name ? tail : null
}

// Ninguna columna es ordenable a proposito: el servidor descarta el parametro `orderBy` y
// ordena siempre por identificador interno, asi que una cabecera pulsable prometeria algo
// que no se cumple.
const headers = [
  { title: t('entities.table.name'), key: 'name', sortable: false, maxWidth: 360 },
  { title: t('entities.table.datamodel'), key: 'datamodel', sortable: false },
  { title: t('entities.table.tenant'), key: 'tenant', sortable: false },
  { title: t('entities.table.scope'), key: 'scope', sortable: false },
  { title: t('entities.table.lastData'), key: 'time_last_data', sortable: false },
]

const pageText = `{0}-{1} ${t('common.of')} {2}`

// Cada carga lleva su numero: una respuesta lenta de una busqueda anterior no debe pisar la actual.
let sequence = 0
let debounce: number | undefined

async function load() {
  const current = ++sequence
  pending.value = true
  error.value = null
  try {
    const result = await listEntities({
      page: page.value,
      paginationSize: perPage.value,
      search: searchTerm.value || undefined,
      types: types.value.length ? types.value.join(',') : undefined,
      // Los dos van juntos o no van: el servidor rechaza un ambito sin espacio de datos.
      tenant: dataScope.value?.tenant,
      scope: dataScope.value?.scope,
    })
    if (current !== sequence) return
    rows.value = result.rows
    total.value = result.count
    void loadLastData(result.rows, current)
  } catch (e) {
    if (current !== sequence) return
    rows.value = []
    total.value = 0
    error.value = errorMessage(e)
  } finally {
    if (current === sequence) pending.value = false
  }
}

async function loadLastData(items: Entity[], current: number) {
  try {
    const times = await getLastDataTimes(items.map((e) => e.id))
    if (current !== sequence) return
    lastData.value = { ...lastData.value, ...times }
  } catch {
    // La marca de ultimo dato es informativa: si falla, la tabla sigue siendo utilizable.
  }
}

async function loadDatamodels() {
  try {
    datamodels.value = await listDatamodels()
  } catch {
    // Sin catalogo el filtro queda deshabilitado, pero el listado sigue funcionando.
  }
}

async function loadDataScopes() {
  try {
    dataScopes.value = await listDataScopes()
  } catch {
    // Un usuario sin permiso de lectura sobre los ambitos simplemente no ve ese filtro.
  }
}

function clearFilters() {
  // Un rebote en vuelo volveria a escribir searchTerm despues de haberlo limpiado.
  window.clearTimeout(debounce)
  search.value = ''
  searchTerm.value = ''
  types.value = []
  dataScope.value = null
}

function openEntity(_event: unknown, row: { item: Entity }) {
  void router.push(`/entidades/${row.item.id}`)
}

// El campo lleva `clearable`, y al pulsar la «x» Vuetify emite null, no cadena vacia. Sin el
// respaldo, el trim revienta dentro del temporizador, fuera de cualquier captura, y el listado
// se queda con los resultados del texto anterior y el campo vacio.
watch(search, (value) => {
  window.clearTimeout(debounce)
  debounce = window.setTimeout(() => {
    searchTerm.value = (value ?? '').trim()
  }, SEARCH_DEBOUNCE)
})

const scopeId = computed(() => dataScope.value?.id ?? null)

watch([searchTerm, types, scopeId], () => {
  page.value = 1
})

watch([page, perPage, searchTerm, types, scopeId], () => void load())

onMounted(() => {
  void load()
  void loadDatamodels()
  void loadDataScopes()
})

onBeforeUnmount(() => window.clearTimeout(debounce))
</script>

<template>
  <div>
    <PageHeader
      :title="t('entities.list.title')"
      :subtitle="t('entities.list.subtitle')"
      :count="rows.length ? countText : undefined"
      icon="mdi-access-point"
    />

    <VCard>
      <div class="d-flex flex-wrap align-start ga-3 pa-4">
        <VTextField
          v-model="search"
          :label="t('entities.list.search')"
          prepend-inner-icon="mdi-magnify"
          clearable
          class="flex-grow-1"
          style="min-width: 220px"
        />
        <VSelect
          v-model="types"
          :items="datamodels"
          :label="t('entities.list.datamodel')"
          :no-data-text="t('entities.list.datamodelEmpty')"
          multiple
          chips
          closable-chips
          clearable
          class="flex-grow-1"
          style="min-width: 220px"
        />
        <!-- Espacio de datos y ambito se eligen en un solo desplegable: son una pareja
             indivisible para el servidor, y separarlos permitiria formar una peticion invalida. -->
        <VSelect
          v-if="dataScopes.length > 1"
          v-model="dataScope"
          :items="dataScopes"
          :item-title="dataScopeLabel"
          item-value="id"
          :label="t('entities.list.dataScope')"
          :no-data-text="t('entities.list.dataScopeEmpty')"
          return-object
          clearable
          class="flex-grow-1"
          style="min-width: 220px"
        />
        <VBtn
          v-if="filtered"
          variant="tonal"
          color="secondary"
          prepend-icon="mdi-filter-remove-outline"
          class="mt-1"
          @click="clearFilters"
        >
          {{ t('entities.list.clear') }}
        </VBtn>
      </div>

      <VDivider />

      <StateBlock
        :loading="firstLoad"
        :error="error"
        :empty="!pending && !error && rows.length === 0"
        :empty-text="filtered ? t('entities.list.emptyFiltered') : t('entities.list.empty')"
        empty-icon="mdi-access-point-off"
        skeleton="table"
        @retry="load()"
      >
        <template #empty-action>
          <VBtn v-if="filtered" variant="tonal" color="secondary" @click="clearFilters">
            {{ t('entities.list.clear') }}
          </VBtn>
        </template>

        <VDataTableServer
          :headers="headers"
          :items="rows"
          :items-length="total"
          :loading="pending"
          :page="page"
          :items-per-page="perPage"
          :items-per-page-options="[10, 25, 50, 100]"
          :items-per-page-text="t('common.rowsPerPage')"
          :page-text="pageText"
          :first-page-label="t('entities.table.firstPage')"
          :prev-page-label="t('entities.table.previousPage')"
          :next-page-label="t('entities.table.nextPage')"
          :last-page-label="t('entities.table.lastPage')"
          :sort-by="[]"
          :row-props="{ class: 'cursor-pointer' }"
          item-value="id"
          mobile-breakpoint="sm"
          @update:page="page = $event"
          @update:items-per-page="perPage = $event"
          @click:row="openEntity"
        >
          <template #[`item.name`]="{ item }">
            <div class="d-flex flex-column min-w-0 py-1">
              <RouterLink
                :to="`/entidades/${item.id}`"
                class="d-block text-truncate text-primary font-weight-medium text-decoration-none"
                :title="item.name || urnTail(item.urn)"
              >
                {{ item.name || urnTail(item.urn) }}
              </RouterLink>
              <span
                v-if="subIdentifier(item)"
                class="text-caption text-medium-emphasis text-truncate"
                :title="item.urn"
              >
                {{ subIdentifier(item) }}
              </span>
            </div>
          </template>

          <template #[`item.datamodel`]="{ item }">
            <VChip
              v-if="item.datamodel"
              variant="tonal"
              color="secondary"
              :prepend-icon="datamodelIcon(item.datamodel)"
              :text="item.datamodel"
            />
            <span v-else class="text-medium-emphasis">{{ t('common.noValue') }}</span>
          </template>

          <template #[`item.tenant`]="{ item }">
            <span class="text-body-2">{{ item.tenant || t('common.noValue') }}</span>
          </template>

          <template #[`item.scope`]="{ item }">
            <span class="text-body-2 text-medium-emphasis">
              {{ item.scope || t('common.noValue') }}
            </span>
          </template>

          <template #[`item.time_last_data`]="{ item }">
            <span class="text-body-2 text-medium-emphasis">
              {{ relativeFromNow(lastData[item.id], session.timeZone) }}
            </span>
          </template>
        </VDataTableServer>
      </StateBlock>
    </VCard>
  </div>
</template>
