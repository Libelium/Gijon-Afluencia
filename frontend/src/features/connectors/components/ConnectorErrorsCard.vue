<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { formatDateTime } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import type { LogLine } from '@/types'
import TableFooter from '@/features/alarms/components/TableFooter.vue'
import { listConnectorErrors } from '../api/connectors'

/** Registro de errores del conector, los mas recientes primero. */
const props = defineProps<{ connectorId: number }>()

const session = useSessionStore()

const rows = ref<LogLine[]>([])
const total = ref(0)
const page = ref(1)
const itemsPerPage = ref(10)
const loading = ref(false)
const loaded = ref(false)
const error = ref<string | null>(null)

interface Header {
  title: string
  key: string
  sortable: false
  width?: number
}

const headers: Header[] = [
  { title: t('connectors.errors.colDatetime'), key: 'datetime', sortable: false, width: 168 },
  { title: t('connectors.errors.colMessage'), key: 'message', sortable: false },
]

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await listConnectorErrors(props.connectorId, page.value, itemsPerPage.value)
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

watch(() => props.connectorId, () => {
  page.value = 1
})

const request = computed(() => ({ id: props.connectorId, page: page.value, size: itemsPerPage.value }))

watch(request, load, { immediate: true })

defineExpose({ reload: load })
</script>

<template>
  <VCard>
    <div class="d-flex flex-wrap align-center ga-3 pa-4">
      <h2 class="text-subtitle-2 flex-grow-1 mb-0">{{ t('connectors.errors.title') }}</h2>
      <VBtn
        icon="mdi-refresh"
        variant="text"
        density="comfortable"
        :loading="loading"
        :aria-label="t('common.refresh')"
        :title="t('common.refresh')"
        @click="load"
      />
    </div>

    <VDivider />

    <StateBlock
      :loading="loading && !loaded"
      :error="error"
      :empty="!loading && !error && rows.length === 0"
      :empty-text="t('connectors.errors.empty')"
      empty-icon="mdi-check-circle-outline"
      skeleton="table"
      @retry="load"
    >
      <VDataTableServer
        :headers="headers"
        :items="rows"
        :items-length="total"
        :items-per-page="itemsPerPage"
        :page="page"
        :loading="loading"
        :loading-text="t('common.loading')"
        :no-data-text="t('connectors.errors.empty')"
        item-value="id"
        hide-default-footer
      >
        <template #[`item.datetime`]="{ item }">
          <span class="text-body-2 text-no-wrap">
            {{ formatDateTime(item.datetime, session.timeZone) }}
          </span>
        </template>

        <template #[`item.message`]="{ item }">
          <!-- Texto plano: el mensaje viene del servidor sin sanear. -->
          <span v-if="item.message" class="text-body-2">{{ item.message }}</span>
          <span v-else class="text-body-2 text-medium-emphasis">
            {{ t('connectors.errors.noMessage') }}
          </span>
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
