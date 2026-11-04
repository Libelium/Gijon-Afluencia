<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { DateTime } from 'luxon'
import { ApiError, errorMessage } from '@/api/http'
import { t } from '@/i18n'
import ConfirmDialog from '../../../components/ConfirmDialog.vue'
import { EVENT_CATALOG } from '../eventSimulation'
import {
  appliesToZone,
  deleteRegistryEvent,
  emptyDraft,
  listRegistry,
  type RegistryDraft,
  type RegistryEvent,
  type RegistryList,
  type RegistryTarget,
} from '../predictionEvents'
import EventRegistryDialog from './EventRegistryDialog.vue'

const props = defineProps<{
  target: RegistryTarget
  /** La zona del panel, como la conoce el modelo. */
  zoneUrn: string
  zoneName?: string
  timeZone: string
}>()
const emit = defineEmits<{
  /** El registro entero, o null si quien mira no puede leerlo. */
  loaded: [list: RegistryList | null]
  registered: [event: RegistryEvent, draft: RegistryDraft]
}>()

/** El formulario abierto. El simulador lo abre relleno con uno de sus eventos. */
const draft = defineModel<RegistryDraft | null>('draft', { default: null })

const list = ref<RegistryList | null>(null)
const forbidden = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const removing = ref<RegistryEvent | null>(null)
const deleting = ref(false)

async function load() {
  loading.value = true
  error.value = null
  try {
    list.value = await listRegistry(props.target)
    forbidden.value = false
  } catch (e) {
    list.value = null
    // Sin permiso de lectura no se ensena nada: el simulador sigue con lo que publica la prevision.
    forbidden.value = e instanceof ApiError && e.kind === 'forbidden'
    if (!forbidden.value) error.value = errorMessage(e)
  } finally {
    loading.value = false
    emit('loaded', list.value)
  }
}

watch(() => [props.target.tenant, props.target.scope], () => void load(), { immediate: true })

const rows = computed(() =>
  (list.value?.rows ?? [])
    .filter((event) => appliesToZone(event, props.zoneUrn))
    .sort((a, b) => a.date.localeCompare(b.date) || a.end_date.localeCompare(b.end_date)),
)

/** Los dias del registro son de calendario: se ensenan tal cual, sin pasarlos por una zona. */
const day = (iso: string) => DateTime.fromISO(iso).toFormat('dd/MM/yyyy')
const when = (event: RegistryEvent) =>
  event.end_date && event.end_date !== event.date ? `${day(event.date)} – ${day(event.end_date)}` : day(event.date)
const hours = (event: RegistryEvent) =>
  event.start_hour === null || event.end_hour === null
    ? t('common.noValue')
    : `${String(event.start_hour).padStart(2, '0')}:00 – ${String(event.end_hour).padStart(2, '0')}:00`
const kind = (event: RegistryEvent) =>
  EVENT_CATALOG.some((spec) => spec.kind === event.event_type)
    ? t(`dashboards.lidar.scenario.kind.${event.event_type}`)
    : event.event_type || t('common.noValue')
const zones = (event: RegistryEvent) =>
  event.device_ids.length === 0
    ? t('dashboards.lidar.registry.allZones')
    : event.device_ids.length === 1
      ? t('dashboards.lidar.registry.thisZone')
      : t('dashboards.lidar.registry.thisAndOthers', { n: event.device_ids.length - 1 })

function openNew() {
  draft.value = emptyDraft(props.timeZone)
}

function onSaved(event: RegistryEvent, from: RegistryDraft) {
  draft.value = null
  emit('registered', event, from)
  void load()
}

async function confirmDelete() {
  const event = removing.value
  if (!event) return
  deleting.value = true
  try {
    await deleteRegistryEvent(props.target, event.id)
    removing.value = null
    void load()
  } catch (e) {
    removing.value = null
    // Otra persona lo cambio entretanto: se vuelve a cargar para que se vea como esta.
    if (e instanceof ApiError && e.status === 409) {
      void load().then(() => (error.value = t('dashboards.lidar.registry.changed')))
    } else {
      error.value = errorMessage(e)
    }
  } finally {
    deleting.value = false
  }
}

const confirmOpen = computed({
  get: () => removing.value !== null,
  set: (value) => {
    if (!value) removing.value = null
  },
})
</script>

<template>
  <section v-if="!forbidden" class="d-flex flex-column ga-2" :aria-label="t('dashboards.lidar.registry.title')">
    <div class="d-flex flex-wrap align-center ga-2">
      <div class="text-subtitle-1 font-weight-medium">{{ t('dashboards.lidar.registry.title') }}</div>
      <VSpacer />
      <VBtn v-if="list?.canEdit" color="primary" variant="tonal" prepend-icon="mdi-calendar-plus" @click="openNew">
        {{ t('dashboards.lidar.registry.add') }}
      </VBtn>
    </div>
    <div class="text-caption text-medium-emphasis">{{ t('dashboards.lidar.registry.hint') }}</div>

    <VAlert v-if="error" type="error" variant="tonal" density="compact" role="alert">
      {{ error }}
      <template #append>
        <VBtn variant="text" size="small" @click="load">{{ t('common.retry') }}</VBtn>
      </template>
    </VAlert>

    <VProgressLinear v-if="loading" indeterminate color="primary" />
    <VTable v-else-if="rows.length" density="compact">
      <thead>
        <tr>
          <th>{{ t('dashboards.lidar.registry.table.days') }}</th>
          <th>{{ t('dashboards.lidar.registry.table.type') }}</th>
          <th>{{ t('dashboards.lidar.registry.table.hours') }}</th>
          <th>{{ t('dashboards.lidar.registry.table.zones') }}</th>
          <th>{{ t('dashboards.lidar.registry.table.notes') }}</th>
          <th v-if="list?.canEdit"><span class="d-sr-only">{{ t('dashboards.lidar.registry.table.actions') }}</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="event in rows" :key="event.id">
          <td>{{ when(event) }}</td>
          <td>{{ kind(event) }}</td>
          <td>{{ hours(event) }}</td>
          <td>{{ zones(event) }}</td>
          <td>{{ event.notes || t('common.noValue') }}</td>
          <td v-if="list?.canEdit" class="text-end">
            <VBtn
              icon="mdi-delete-outline"
              variant="text"
              size="small"
              :aria-label="t('dashboards.lidar.registry.delete', { when: when(event) })"
              @click="removing = event"
            />
          </td>
        </tr>
      </tbody>
    </VTable>
    <div v-else-if="!error" class="text-body-2 text-medium-emphasis">{{ t('dashboards.lidar.registry.empty') }}</div>

    <EventRegistryDialog
      :draft="draft"
      :target="target"
      :zone-urn="zoneUrn"
      :zone-name="zoneName"
      :time-zone="timeZone"
      @close="draft = null"
      @saved="onSaved"
    />
    <ConfirmDialog
      v-model="confirmOpen"
      :title="t('dashboards.lidar.registry.deleteTitle')"
      :text="removing ? t('dashboards.lidar.registry.deleteText', { when: when(removing), kind: kind(removing) }) : undefined"
      :confirm-text="t('dashboards.lidar.registry.deleteConfirm')"
      color="error"
      :loading="deleting"
      @confirm="confirmDelete"
    />
  </section>
</template>
