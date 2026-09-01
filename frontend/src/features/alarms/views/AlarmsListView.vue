<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { t } from '@/i18n'
import { errorMessage } from '@/api/http'
import { formatDateTime } from '@/lib/format'
import { clickableRowProps } from '@/lib/a11y'
import { useSessionStore } from '@/stores/session'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import AlarmStateChip from '../components/AlarmStateChip.vue'
import AlarmTypeChip from '../components/AlarmTypeChip.vue'
import TableFooter from '../components/TableFooter.vue'
import { listAlarms } from '../api/alarms'
import { lastModified } from '../lib/display'
import type { AlarmRow } from '../types'

const router = useRouter()
const session = useSessionStore()

const rows = ref<AlarmRow[]>([])
const total = ref(0)
const page = ref(1)
const itemsPerPage = ref(10)
const search = ref('')
const appliedSearch = ref('')
const loading = ref(false)
const loaded = ref(false)
const error = ref<string | null>(null)

let debounceId: ReturnType<typeof setTimeout> | undefined

interface Header {
  title: string
  key: string
  sortable: false
  align?: 'start' | 'center' | 'end'
  width?: number
}

const headers: Header[] = [
  { title: t('alarms.col.name'), key: 'name', sortable: false },
  { title: t('alarms.col.state'), key: 'state', sortable: false },
  { title: t('alarms.col.type'), key: 'type', sortable: false },
  { title: t('alarms.col.updated'), key: 'updated', sortable: false },
  { title: '', key: 'open', sortable: false, align: 'end', width: 64 },
]

const emptyText = computed(() =>
  appliedSearch.value ? t('alarms.list.emptySearch') : t('alarms.list.empty'),
)

async function fetchAlarms() {
  loading.value = true
  error.value = null
  try {
    const data = await listAlarms({
      page: page.value,
      paginationSize: itemsPerPage.value,
      search: appliedSearch.value,
    })
    rows.value = data.rows
    total.value = data.count
    loaded.value = true
  } catch (e) {
    rows.value = []
    total.value = 0
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

// Una sola fuente para la peticion: pagina, tamano y busqueda cambian a la vez sin lanzar
// dos consultas seguidas.
const request = computed(() => ({
  page: page.value,
  size: itemsPerPage.value,
  search: appliedSearch.value,
}))

watch(request, fetchAlarms, { immediate: true })

watch(search, (value) => {
  clearTimeout(debounceId)
  debounceId = setTimeout(() => {
    page.value = 1
    appliedSearch.value = (value ?? '').trim()
  }, 350)
})

onBeforeUnmount(() => clearTimeout(debounceId))

function clearSearch() {
  search.value = ''
  clearTimeout(debounceId)
  page.value = 1
  appliedSearch.value = ''
}

function openAlarm(_event: unknown, row: { item: AlarmRow }) {
  goToAlarm(row.item)
}

function goToAlarm(alarm: AlarmRow) {
  if (alarm?.id !== undefined) void router.push(`/alarmas/${alarm.id}`)
}

// Mismo motivo que en el listado de entidades: la fila pulsable necesita equivalente de teclado.
const rowProps = clickableRowProps<AlarmRow>(goToAlarm)
</script>

<template>
  <PageHeader :title="t('alarms.list.title')" :subtitle="t('alarms.list.subtitle')">
    <template #actions>
      <VBtn to="/alarmas/nueva" color="primary" prepend-icon="mdi-plus">
        {{ t('alarms.list.new') }}
      </VBtn>
    </template>
  </PageHeader>

  <VCard>
    <div class="d-flex flex-wrap align-center ga-3 pa-4">
      <VTextField
        v-model="search"
        :label="t('alarms.list.search')"
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
      empty-icon="mdi-bell-off-outline"
      skeleton="table"
      @retry="fetchAlarms"
    >
      <template #empty-action>
        <VBtn v-if="appliedSearch" variant="tonal" @click="clearSearch">
          {{ t('alarms.list.clearSearch') }}
        </VBtn>
        <VBtn v-else to="/alarmas/nueva" color="primary" prepend-icon="mdi-plus">
          {{ t('alarms.list.new') }}
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
        @click:row="openAlarm"
      >
        <template #[`item.name`]="{ item }">
          <span class="font-weight-medium">{{ item.name || '—' }}</span>
        </template>

        <!-- El chip resuelve los tres estados excluyentes; dos chips sueltos dejaban una alarma
             desactivada y disparada a la vez, que es una combinacion que no existe. -->
        <template #[`item.state`]="{ item }">
          <AlarmStateChip :alarm="item" />
        </template>

        <template #[`item.type`]="{ item }">
          <AlarmTypeChip :type="item.type" />
        </template>

        <template #[`item.updated`]="{ item }">
          <span class="text-body-2 text-medium-emphasis">
            {{ formatDateTime(lastModified(item), session.timeZone) }}
          </span>
        </template>

        <template #[`item.open`]="{ item }">
          <VBtn
            :to="`/alarmas/${item.id}`"
            icon="mdi-chevron-right"
            variant="text"
            density="comfortable"
            :aria-label="t('alarms.list.open')"
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
