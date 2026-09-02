<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDebounceFn } from '@/composables/useDebounce'
import { usePaginatedList } from '@/composables/usePaginatedList'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import type { DashboardDetail } from '../api/dashboards'
import { listDashboards } from '../api/dashboards'
import DashboardCard from '../components/DashboardCard.vue'
import DashboardCreateDialog from '../components/DashboardCreateDialog.vue'

const CATALOG_SIZE = 200 // el catalogo de un ayuntamiento son decenas de paneles, no miles
const PAGE_SIZE = 12
const SEARCH_DELAY = 350

type TypeFilter = 'all' | 'custom' | 'template'

const router = useRouter()

const filter = ref<TypeFilter>('all')
const page = ref(1)
const search = ref<string | null>('')
const createOpen = ref(false)

/** El campo con `clearable` devuelve null al vaciarse, no cadena vacia. */
const query = computed(() => (search.value ?? '').trim())

// `all` es el catalogo completo que declara el servidor (hasta CATALOG_SIZE); el filtro por tipo
// y la paginacion se resuelven en cliente sobre el. La busqueda si viaja al servidor.
const { rows: all, total: count, loading, error, load } = usePaginatedList<DashboardDetail>(
  () =>
    listDashboards({
      page: 1,
      paginationSize: CATALOG_SIZE,
      search: query.value || undefined,
    }),
  { initialLoading: false },
)

const filtered = computed(() =>
  all.value.filter((d) => filter.value === 'all' || (filter.value === 'template') === !!d.templateType),
)

const pages = computed(() => Math.max(1, Math.ceil(filtered.value.length / PAGE_SIZE)))

const visible = computed(() => filtered.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))

const truncated = computed(() => count.value > all.value.length)

const filterItems = [
  { value: 'all', title: t('dashboards.list.filterAll') },
  { value: 'custom', title: t('dashboards.list.filterCustom') },
  { value: 'template', title: t('dashboards.list.filterTemplate') },
]

const countLabel = computed(() => {
  if (loading.value || error.value || !all.value.length) return undefined
  if (filter.value !== 'all') {
    return t('dashboards.list.filteredCount', { shown: filtered.value.length, count: all.value.length })
  }
  if (query.value) {
    return count.value === 1
      ? t('dashboards.list.resultCountOne')
      : t('dashboards.list.resultCount', { count: count.value })
  }
  return count.value === 1
    ? t('dashboards.list.countOne')
    : t('dashboards.list.count', { count: count.value })
})

const subtitle = computed(() =>
  query.value && count.value ? t('dashboards.list.searching', { query: query.value }) : undefined,
)

const emptyText = computed(() => {
  if (filter.value !== 'all' && all.value.length) return t('dashboards.list.emptyFiltered')
  if (query.value) return t('dashboards.list.noMatches', { query: query.value })
  return t('dashboards.list.empty')
})

const emptyHint = computed(() => {
  if (filter.value !== 'all' && all.value.length) return t('dashboards.list.emptyFilteredHint')
  if (query.value) return t('dashboards.list.noMatchesHint')
  return t('dashboards.list.emptyHint')
})

watch(filter, () => {
  page.value = 1
})

const runSearch = useDebounceFn(() => {
  page.value = 1
  void load()
}, SEARCH_DELAY)

watch(query, () => runSearch())

function goToDashboard(id: number) {
  void router.push(`/paneles/${id}`)
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      :title="t('dashboards.list.title')"
      :count="countLabel"
      :subtitle="subtitle"
      icon="mdi-view-dashboard-outline"
    >
      <template #actions>
        <VTextField
          v-model="search"
          :label="t('dashboards.list.search')"
          prepend-inner-icon="mdi-magnify"
          clearable
          min-width="220"
          max-width="300"
        />
        <VSelect
          v-model="filter"
          :items="filterItems"
          :label="t('dashboards.list.filter')"
          min-width="170"
          max-width="200"
        />
        <VBtn color="primary" prepend-icon="mdi-plus" @click="createOpen = true">
          {{ t('dashboards.list.new') }}
        </VBtn>
      </template>
    </PageHeader>

    <div v-if="truncated" class="text-caption text-medium-emphasis mb-4">
      {{ t('dashboards.list.truncated', { shown: all.length, count }) }}
    </div>

    <StateBlock
      :loading="loading"
      :error="error"
      :empty="!visible.length"
      :empty-text="emptyText"
      :empty-hint="emptyHint"
      empty-icon="mdi-view-dashboard-outline"
      skeleton="card"
      @retry="load"
    >
      <template #empty-action>
        <VBtn v-if="query" variant="tonal" color="primary" prepend-icon="mdi-close" @click="search = ''">
          {{ t('dashboards.list.clearSearch') }}
        </VBtn>
        <VBtn
          v-else-if="filter !== 'all'"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-filter-remove-outline"
          @click="filter = 'all'"
        >
          {{ t('common.clear') }}
        </VBtn>
        <VBtn v-else color="primary" prepend-icon="mdi-plus" @click="createOpen = true">
          {{ t('dashboards.list.emptyAction') }}
        </VBtn>
      </template>

      <VRow>
        <VCol v-for="d in visible" :key="d.id" cols="12" sm="6" lg="4" xl="3">
          <DashboardCard :dashboard="d" />
        </VCol>
      </VRow>

      <div v-if="pages > 1" class="d-flex justify-center mt-6">
        <VPagination
          v-model="page"
          :length="pages"
          :total-visible="4"
          density="comfortable"
          :aria-label="t('dashboards.list.pagination')"
        />
      </div>
    </StateBlock>

    <DashboardCreateDialog v-model="createOpen" @created="goToDashboard" />
  </div>
</template>
