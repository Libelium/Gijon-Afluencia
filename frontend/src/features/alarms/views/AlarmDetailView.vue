<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ApiError, errorMessage } from '@/api/http'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import AlarmEventsCard from '../components/AlarmEventsCard.vue'
import AlarmIndicators from '../components/AlarmIndicators.vue'
import AlarmStateChip from '../components/AlarmStateChip.vue'
import AlarmStatusCard from '../components/AlarmStatusCard.vue'
import AlarmSummaryCard from '../components/AlarmSummaryCard.vue'
import AlarmTypeChip from '../components/AlarmTypeChip.vue'
import { getActions, getAlarm, getConditions, getInactivityConditions } from '../api/alarms'
import { actionChannels, type ActionChannel } from '../lib/display'
import type { AlarmDetail, InactivityCondition, ThresholdCondition } from '../types'

const route = useRoute()

const alarm = ref<AlarmDetail | null>(null)
const conditions = ref<ThresholdCondition[]>([])
const inactivityConditions = ref<InactivityCondition[]>([])
const pending = ref(true)
const error = ref<string | null>(null)

const channels = ref<ActionChannel[]>([])
/** Los avisos se consultan aparte: si esa llamada falla, se dice en su tarjeta y nada mas. */
const channelsUnavailable = ref(false)

/** El id llega por la ruta y puede ser cualquier cosa: sin un numero no hay alarma que pedir. */
const alarmId = computed(() => {
  const raw = Number(route.params.id)
  return Number.isInteger(raw) && raw > 0 ? raw : null
})

const title = computed(() => alarm.value?.name?.trim() || t('alarms.detail.title'))

/** Distinto de un error: la consulta ha ido bien (o no habia id que pedir) y la alarma no esta. */
const missing = computed(() => !pending.value && !error.value && !alarm.value)

/** Se limpian juntos: el nombre de una alarma con las condiciones de otra enganaria al leerlo. */
function clearDetail() {
  alarm.value = null
  conditions.value = []
  inactivityConditions.value = []
}

async function loadActions(id: number) {
  try {
    channels.value = actionChannels(await getActions(id))
  } catch {
    channels.value = []
    channelsUnavailable.value = true
  }
}

async function load() {
  const id = alarmId.value
  pending.value = true
  error.value = null
  channels.value = []
  channelsUnavailable.value = false

  if (id === null) {
    clearDetail()
    pending.value = false
    return
  }

  let exists = false
  try {
    // La alarma primero: si el id no existe no hay condiciones que pedir, y un 404 se puede
    // atribuir a la alarma y no a una de las dos consultas de apoyo.
    const detail = await getAlarm(id)
    exists = true
    // Las condiciones no son un extra: sin ellas no se puede decir cuando se dispara la
    // alarma, asi que comparten la suerte del detalle.
    const [thresholds, inactivity] = await Promise.all([
      getConditions(id),
      getInactivityConditions(id),
    ])
    alarm.value = detail
    conditions.value = thresholds
    inactivityConditions.value = inactivity
  } catch (e) {
    clearDetail()
    // Que el id no exista no es un fallo de la aplicacion y no se ofrece reintentar. Un 404
    // de las condiciones, en cambio, si es un error: la alarma esta y no se puede describir.
    if (exists || !(e instanceof ApiError && e.kind === 'notFound')) error.value = errorMessage(e)
  } finally {
    pending.value = false
  }

  if (alarm.value) void loadActions(id)
}

watch(alarmId, () => void load(), { immediate: true })
</script>

<template>
  <PageHeader
    :title="title"
    :subtitle="alarm?.description"
    icon="mdi-bell-outline"
    back-to="/alarmas"
  >
    <template #actions>
      <template v-if="alarm">
        <AlarmStateChip :alarm="alarm" />
        <AlarmTypeChip :type="alarm.type" />
      </template>

      <VBtn
        icon="mdi-refresh"
        variant="tonal"
        :loading="pending"
        :aria-label="t('common.refresh')"
        :title="t('common.refresh')"
        @click="load()"
      />
    </template>
  </PageHeader>

  <StateBlock
    :loading="pending"
    :error="error"
    :empty="missing"
    :empty-text="t('alarms.detail.notFound')"
    empty-icon="mdi-bell-off-outline"
    skeleton="card"
    @retry="load()"
  >
    <template #empty-action>
      <VBtn to="/alarmas" variant="tonal">{{ t('common.back') }}</VBtn>
    </template>

    <div v-if="alarm">
      <AlarmIndicators
        :alarm="alarm"
        :threshold-count="conditions.length"
        :inactivity-count="inactivityConditions.length"
        :channels="channels"
        :channels-unavailable="channelsUnavailable"
        class="mb-6"
      />

      <!-- El resumen dice cuando se dispara y el historico si lo ha hecho: se leen juntos. -->
      <VRow class="mb-6">
        <VCol cols="12" md="5">
          <AlarmSummaryCard
            :alarm="alarm"
            :conditions="conditions"
            :inactivity-conditions="inactivityConditions"
            :channels="channels"
            :channels-unavailable="channelsUnavailable"
          />
        </VCol>
        <VCol cols="12" md="7">
          <AlarmStatusCard :alarm-id="alarm.id" />
        </VCol>
      </VRow>

      <AlarmEventsCard :alarm-id="alarm.id" />
    </div>
  </StateBlock>
</template>
