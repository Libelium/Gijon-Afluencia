<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { t } from '@/i18n'
import { useDebounceFn } from '@/composables/useDebounce'
import { usePaginatedList } from '@/composables/usePaginatedList'
import { formatDateTime, relativeFromNow } from '@/lib/format'
import { clickableRowProps } from '@/lib/a11y'
import { useSessionStore } from '@/stores/session'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import TableFooter from '@/features/alarms/components/TableFooter.vue'
import ConnectorStatusChip from '../components/ConnectorStatusChip.vue'
import { listConnectors } from '../api/connectors'
import type { ConnectorRow } from '../types'

const router = useRouter()
const session = useSessionStore()

const page = ref(1)
const itemsPerPage = ref(10)
const search = ref('')
const appliedSearch = ref('')
const loaded = ref(false)

const { rows, total, loading, error, load } = usePaginatedList<ConnectorRow>(
  () =>
    listConnectors({
      page: page.value,
      paginationSize: itemsPerPage.value,
      search: appliedSearch.value,
    }),
  {
    onLoaded: () => {
      loaded.value = true
    },
  },
)

interface Header {
  title: string
  key: string
  sortable: false
  align?: 'start' | 'center' | 'end'
  width?: number
}

const headers: Header[] = [
  { title: t('connectors.col.name'), key: 'name', sortable: false },
  { title: t('connectors.col.state'), key: 'state', sortable: false },
  { title: t('connectors.col.lastSend'), key: 'lastSend', sortable: false },
  { title: '', key: 'open', sortable: false, align: 'end', width: 64 },
]

const emptyText = computed(() =>
  appliedSearch.value ? t('connectors.list.emptySearch') : t('connectors.list.empty'),
)

const request = computed(() => ({
  page: page.value,
  size: itemsPerPage.value,
  search: appliedSearch.value,
}))

watch(request, load, { immediate: true })

const applySearch = useDebounceFn((value: string | null) => {
  page.value = 1
  appliedSearch.value = (value ?? '').trim()
}, 350)

watch(search, (value) => applySearch(value))

function clearSearch() {
  applySearch.cancel()
  search.value = ''
  page.value = 1
  appliedSearch.value = ''
}

function openConnector(_event: unknown, row: { item: ConnectorRow }) {
  goToConnector(row.item)
}

function goToConnector(connector: ConnectorRow) {
  if (connector?.id !== undefined) void router.push(`/conectores/${connector.id}`)
}

const rowProps = clickableRowProps<ConnectorRow>(goToConnector)
</script>

<template>
  <PageHeader :title="t('connectors.list.title')" :subtitle="t('connectors.list.subtitle')">
    <template #actions>
      <VBtn to="/conectores/nuevo" color="primary" prepend-icon="mdi-plus">
        {{ t('connectors.list.new') }}
      </VBtn>
    </template>
  </PageHeader>

  <VCard>
    <div class="d-flex flex-wrap align-center ga-3 pa-4">
      <VTextField
        v-model="search"
        :label="t('connectors.list.search')"
        prepend-inner-icon="mdi-magnify"
        clearable
        max-width="380"
        class="flex-grow-1"
      />
    </div>

    <VDivider />

    <StateBlock
      :loading="loading && !loaded"
      :error="error"
      :empty="!loading && rows.length === 0"
      :empty-text="emptyText"
      empty-icon="mdi-transit-connection-variant"
      skeleton="table"
      @retry="load"
    >
      <template #empty-action>
        <VBtn v-if="appliedSearch" variant="tonal" @click="clearSearch">
          {{ t('connectors.list.clearSearch') }}
        </VBtn>
        <VBtn v-else to="/conectores/nuevo" color="primary" prepend-icon="mdi-plus">
          {{ t('connectors.list.new') }}
        </VBtn>
      </template>

      <VDataTableServer
        :headers="headers"
        :items="rows"
        :items-length="total"
        :items-per-page="itemsPerPage"
        :page="page"
        :loading="loading"
        :loading-text="t('common.loading')"
        :no-data-text="emptyText"
        :row-props="rowProps"
        item-value="id"
        hide-default-footer
        @click:row="openConnector"
      >
        <template #[`item.name`]="{ item }">
          <span class="font-weight-medium">{{ item.name || '—' }}</span>
        </template>

        <template #[`item.state`]="{ item }">
          <ConnectorStatusChip :connector="item" />
        </template>

        <template #[`item.lastSend`]="{ item }">
          <span
            class="text-body-2 text-medium-emphasis"
            :title="formatDateTime(item.last_connection, session.timeZone)"
          >
            {{
              item.last_connection
                ? relativeFromNow(item.last_connection, session.timeZone)
                : t('connectors.kpi.neverSent')
            }}
          </span>
        </template>

        <template #[`item.open`]="{ item }">
          <VBtn
            :to="`/conectores/${item.id}`"
            icon="mdi-chevron-right"
            variant="text"
            density="comfortable"
            :aria-label="t('connectors.list.open')"
          />
        </template>

        <template #bottom>
          <TableFooter
            :page="page"
            :items-per-page="itemsPerPage"
            :total="total"
            @update:page="page = $event"
            @update:items-per-page="itemsPerPage = $event"
          />
        </template>
      </VDataTableServer>
    </StateBlock>
  </VCard>
</template>
