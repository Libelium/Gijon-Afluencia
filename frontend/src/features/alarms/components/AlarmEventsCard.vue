<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { formatDateTime } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import type { LogLine } from '@/types'
import TableFooter from './TableFooter.vue'
import { listAlarmEvents } from '../api/alarms'
import { eventLevelColor, eventLevelLabel, normalizeIso, rangeFromPreset } from '../lib/display'
import type { DateRange, EventLevel, RangePreset } from '../types'

/** Registro de la alarma: cada tarjeta pide sus propios datos, como el historico de estado. */
const props = defineProps<{ alarmId: number }>()

const session = useSessionStore()

const rows = ref<LogLine[]>([])
const total = ref(0)
const page = ref(1)
const itemsPerPage = ref(10)
const preset = ref<RangePreset>('24h')
const level = ref<EventLevel>('ALL')
const range = ref<DateRange>(rangeFromPreset('24h'))
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
  { title: t('alarms.events.colDatetime'), key: 'datetime', sortable: false, width: 168 },
  { title: t('alarms.events.colLevel'), key: 'level', sortable: false, width: 132 },
  { title: t('alarms.events.colMessage'), key: 'message', sortable: false },
]

const rangeItems: Array<{ value: RangePreset; title: string }> = [
  { value: '24h', title: t('alarms.events.range24h') },
  { value: '7d', title: t('alarms.events.range7d') },
  { value: '30d', title: t('alarms.events.range30d') },
]

const levelItems: Array<{ value: EventLevel; title: string }> = [
  { value: 'ALL', title: t('alarms.events.levelAll') },
  { value: 'INFO', title: t('alarms.events.levelInfo') },
  { value: 'WARNING', title: t('alarms.events.levelWarning') },
  { value: 'ERROR', title: t('alarms.events.levelError') },
]

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await listAlarmEvents(
      props.alarmId,
      range.value,
      level.value,
      page.value,
      itemsPerPage.value,
    )
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

/**
 * Cambiar de alarma o de filtro invalida la pagina en la que se estaba: se vuelve a la
 * primera antes de pedir. Al resolver aqui la ventana temporal, paginar no la recalcula:
 * con un «hasta ahora» distinto en cada pagina, los eventos se colarian de una a otra.
 */
watch([() => props.alarmId, preset, level], ([, nextPreset]) => {
  range.value = rangeFromPreset(nextPreset)
  page.value = 1
})

/** Una sola fuente para la peticion: varios filtros cambian a la vez sin lanzar dos consultas. */
const request = computed(() => ({
  id: props.alarmId,
  start: range.value.start,
  end: range.value.end,
  level: level.value,
  page: page.value,
  size: itemsPerPage.value,
}))

watch(request, load, { immediate: true })

/** El periodo es relativo a ahora: actualizar tiene que volver a resolverlo. */
function refresh() {
  range.value = rangeFromPreset(preset.value)
}

function eventDate(line: LogLine): string {
  return formatDateTime(normalizeIso(line.datetime), session.timeZone)
}
</script>

<template>
  <VCard>
    <div class="d-flex flex-wrap align-center ga-3 pa-4">
      <div class="flex-grow-1 min-w-0">
        <div class="text-subtitle-2">{{ t('alarms.events.title') }}</div>
      </div>

      <VSelect
        v-model="preset"
        :items="rangeItems"
        :label="t('alarms.events.range')"
        min-width="180"
        max-width="220"
      />

      <VSelect
        v-model="level"
        :items="levelItems"
        :label="t('alarms.events.level')"
        min-width="160"
        max-width="200"
      />

      <VBtn
        icon="mdi-refresh"
        variant="text"
        density="comfortable"
        :loading="loading"
        :aria-label="t('common.refresh')"
        :title="t('common.refresh')"
        @click="refresh"
      />
    </div>

    <VDivider />

    <StateBlock
      :loading="loading && !loaded"
      :error="error"
      :empty="!loading && !error && rows.length === 0"
      :empty-text="t('alarms.events.empty')"
      empty-icon="mdi-text-box-outline"
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
        :no-data-text="t('alarms.events.empty')"
        item-value="id"
        hide-default-footer
      >
        <template #[`item.datetime`]="{ item }">
          <span class="text-body-2 text-no-wrap">{{ eventDate(item) }}</span>
        </template>

        <template #[`item.level`]="{ item }">
          <VChip :color="eventLevelColor(item.level_name)" size="small" variant="tonal">
            {{ eventLevelLabel(item.level_name) }}
          </VChip>
        </template>

        <template #[`item.message`]="{ item }">
          <!-- Texto plano: el mensaje viene del servidor sin sanear. -->
          <span v-if="item.message" class="text-body-2">{{ item.message }}</span>
          <span v-else class="text-body-2 text-medium-emphasis">
            {{ t('alarms.events.noMessage') }}
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
