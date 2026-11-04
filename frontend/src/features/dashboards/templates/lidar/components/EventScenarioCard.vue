<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import StatTile from '@/components/StatTile.vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { formatDateTime, formatNumber } from '@/lib/format'
import type { Entity } from '@/types'
import { LineChart, type ChartSeries } from '../../../charts'
import { SCENARIO_HORIZON_HOURS } from '../../../lib/range'
import { fetchZoneSeries, refOf } from '../data'
import {
  DEFAULT_INTENSITY,
  EVENT_CATALOG,
  MAX_EVENT_DAYS,
  MAX_EVENT_HOURS,
  MAX_INTENSITY,
  MIN_INTENSITY,
  WEATHER_FACTORS,
  eventPeak,
  eventStartHours,
  referenceOf,
  registeredScenarioEvents,
  simulate,
  summariseScenario,
  type EventKind,
  type ScenarioEvent,
  type Weather,
} from '../eventSimulation'
import { asPublished, draftFromScenario, type RegistryDraft, type RegistryList } from '../predictionEvents'
import ChartCard from './ChartCard.vue'
import EventRegistry from './EventRegistry.vue'

const props = defineProps<{
  /** Gemela de prevision de la zona. */
  twin: Entity
  /** Nombre de la zona que se simula, para el titulo. */
  zoneName?: string
  /** Medida con el valor previsto. */
  predictedId: string
  /** Aforo de la zona en personas, o null si no lo publica. */
  capacity: number | null
  timeZone?: string
  /** Eventos registrados de la zona: siempre se suman y no se pueden quitar. */
  registered?: ScenarioEvent[]
  /** La zona como la conoce el modelo de prediccion. Sin ella no se ofrece el registro. */
  zoneUrn?: string
}>()

const HOUR_MS = 3_600_000

const loading = ref(false)
const error = ref<string | null>(null)
const times = ref<string[]>([])
const base = ref<(number | null)[]>([])

/** Se simula por horas sobre todo lo que publica la prevision (una semana), sea cual sea el rango
 * del panel. */
async function load() {
  loading.value = true
  error.value = null
  try {
    const now = Date.now()
    const range = {
      start: new Date(Math.floor(now / HOUR_MS) * HOUR_MS).toISOString(),
      end: new Date(now + SCENARIO_HORIZON_HOURS * HOUR_MS).toISOString(),
    }
    const series = await fetchZoneSeries(
      refOf(props.twin),
      [{ key: 'predicted', fn: 'mean', measureId: props.predictedId }],
      range,
      { forceInterval: 'PT1H' },
    )
    const points = series.predicted ?? []
    times.value = points.map((point) => point.t)
    base.value = points.map((point) => point.v)
  } catch (e) {
    error.value = errorMessage(e)
    times.value = []
    base.value = []
  } finally {
    loading.value = false
  }
}

watch(() => [props.twin.id, props.predictedId], () => void load(), { immediate: true })

const people = t('dashboards.lidar.people')
const kindLabel = (kind: EventKind) => t(`dashboards.lidar.scenario.kind.${kind}`)
const weatherLabel = (weather: Weather) => t(`dashboards.lidar.scenario.weather.${weather}`)
const hoursLabel = (n: number) => t('dashboards.lidar.scenario.hoursValue', { n })
const daysLabel = (n: number) =>
  n === 1 ? t('dashboards.lidar.scenario.oneDay') : t('dashboards.lidar.scenario.daysValue', { n })

const startHours = computed(() => eventStartHours(times.value, base.value, Date.now()))
const startItems = computed(() =>
  startHours.value.map((iso) => ({ title: formatDateTime(iso, props.timeZone), value: iso })),
)
const hourItems = Array.from({ length: MAX_EVENT_HOURS }, (_, i) => ({ title: hoursLabel(i + 1), value: i + 1 }))
const dayItems = Array.from({ length: MAX_EVENT_DAYS }, (_, i) => ({ title: daysLabel(i + 1), value: i + 1 }))
const kindItems = EVENT_CATALOG.map((spec) => ({ title: kindLabel(spec.kind), value: spec.kind }))
const weatherItems = (Object.keys(WEATHER_FACTORS) as Weather[]).map((w) => ({ title: weatherLabel(w), value: w }))

const start = ref<string | null>(null)
const hours = ref(2)
const days = ref(1)
const kind = ref<EventKind>('concert')
const weather = ref<Weather>('clear')
const intensity = ref(DEFAULT_INTENSITY)
const events = ref<ScenarioEvent[]>([])
let nextId = 1

// Al recargar la prevision, la hora elegida puede haber quedado atras: se pasa a la primera libre.
watch(startHours, (list) => {
  if (!start.value || !list.includes(start.value)) start.value = list[0] ?? null
})

const intensityLabel = computed(() =>
  t('dashboards.lidar.scenario.intensity', { value: intensity.value.toFixed(1).replace('.', ',') }),
)

function add() {
  if (!start.value) return
  events.value = [
    ...events.value,
    {
      id: nextId++,
      kind: kind.value,
      weather: weather.value,
      intensity: intensity.value,
      start: start.value,
      hours: hours.value,
      days: days.value,
    },
  ]
}

function remove(id: number) {
  events.value = events.value.filter((event) => event.id !== id)
}

function clear() {
  events.value = []
}

const zone = computed(() => props.timeZone || 'UTC')
const target = computed(() => ({ tenant: props.twin.tenant, scope: props.twin.scope }))
const registry = ref<RegistryList | null>(null)
const registryDraft = ref<RegistryDraft | null>(null)

/**
 * Los registrados salen del registro en cuanto se carga, asi que lo que se acaba de registrar se
 * ve ya. Sin el (quien mira no puede leerlo), los que publico la prevision en su ultima ejecucion.
 */
const registered = computed(() =>
  registry.value && props.zoneUrn
    ? registeredScenarioEvents(asPublished(registry.value.rows, props.zoneUrn), zone.value)
    : (props.registered ?? []),
)
const canRegister = computed(() => !!registry.value?.canEdit && !!props.zoneUrn)

function registerScenario(event: ScenarioEvent) {
  registryDraft.value = draftFromScenario(event, zone.value)
}

/** Un evento simulado que se registra pasa a contarse como registrado: se quita de lo simulado. */
function onRegistered(_saved: unknown, draft: RegistryDraft) {
  if (draft.fromScenario !== undefined) remove(draft.fromScenario)
}

// Los registrados van delante: son lo que ya se sabe que va a pasar, lo simulado se suma encima.
const allEvents = computed(() => [...registered.value, ...events.value])
const hasForecast = computed(() => startHours.value.length > 0)
const reference = computed(() => referenceOf(props.capacity, base.value))
const simulated = computed(() =>
  reference.value === null
    ? base.value
    : simulate(times.value, base.value, allEvents.value, reference.value, props.timeZone),
)
const summary = computed(() => summariseScenario(times.value, base.value, simulated.value, props.capacity))

const series = computed<ChartSeries[]>(() => {
  const list: ChartSeries[] = [
    {
      name: t('dashboards.lidar.scenario.base'),
      units: people,
      points: times.value.map((iso, i) => ({ t: iso, v: base.value[i] })),
    },
  ]
  if (allEvents.value.length) {
    list.push({
      name: t('dashboards.lidar.scenario.withEvents'),
      units: people,
      points: times.value.map((iso, i) => ({ t: iso, v: simulated.value[i] })),
    })
  }
  if (props.capacity) {
    const capacity = props.capacity
    list.push({
      name: t('dashboards.lidar.scenario.capacity'),
      units: people,
      points: times.value.map((iso) => ({ t: iso, v: capacity })),
    })
  }
  return list
})

const rows = computed(() =>
  allEvents.value.map((event) => ({
    event,
    label: event.registered
      ? t('dashboards.lidar.scenario.registeredLabel', { kind: kindLabel(event.kind) })
      : kindLabel(event.kind),
    when: [
      formatDateTime(event.start, props.timeZone),
      hoursLabel(event.hours),
      ...((event.days ?? 1) > 1 ? [daysLabel(event.days!)] : []),
    ].join(' · '),
    weather: `${weatherLabel(event.weather)} · ${event.intensity.toFixed(1).replace('.', ',')}x`,
    extra: reference.value === null ? null : Math.round(eventPeak(event, reference.value)),
  })),
)

const overValue = computed(() =>
  summary.value.hoursOverCapacity === null ? t('common.noValue') : formatNumber(summary.value.hoursOverCapacity, 0),
)
const overHint = computed(() =>
  props.capacity
    ? t('dashboards.lidar.scenario.tileOverHint', { capacity: formatNumber(props.capacity, 0) })
    : t('dashboards.lidar.scenario.tileOverNoCapacity'),
)
</script>

<template>
  <ChartCard
    :title="zoneName ? t('dashboards.lidar.scenario.titleZone', { zone: zoneName }) : t('dashboards.lidar.scenario.title')"
    :subtitle="t('dashboards.lidar.scenario.subtitle')"
    :loading="loading"
    :error="error"
    :empty="!hasForecast"
    :empty-text="t('dashboards.lidar.scenario.noForecast')"
    :empty-hint="t('dashboards.lidar.scenario.noForecastHint')"
    empty-icon="mdi-calendar-star"
    :min-height="240"
    @retry="load"
  >
    <div class="d-flex flex-column ga-4">
      <div class="d-flex flex-wrap align-center ga-3">
        <VSelect
          v-model="start"
          :items="startItems"
          :label="t('dashboards.lidar.scenario.start')"
          density="comfortable"
          hide-details
          style="flex: 1 1 200px"
        />
        <VSelect
          v-model="hours"
          :items="hourItems"
          :label="t('dashboards.lidar.scenario.hours')"
          density="comfortable"
          hide-details
          style="flex: 0 1 130px"
        />
        <VSelect
          v-model="days"
          :items="dayItems"
          :label="t('dashboards.lidar.scenario.days')"
          density="comfortable"
          hide-details
          style="flex: 0 1 130px"
        />
        <VSelect
          v-model="kind"
          :items="kindItems"
          :label="t('dashboards.lidar.scenario.kind')"
          density="comfortable"
          hide-details
          style="flex: 1 1 190px"
        />
        <VSelect
          v-model="weather"
          :items="weatherItems"
          :label="t('dashboards.lidar.scenario.weather')"
          density="comfortable"
          hide-details
          style="flex: 1 1 160px"
        />
        <VSlider
          v-model="intensity"
          :min="MIN_INTENSITY"
          :max="MAX_INTENSITY"
          :step="0.1"
          :label="intensityLabel"
          color="primary"
          hide-details
          style="flex: 1 1 260px"
        />
      </div>

      <div class="d-flex flex-wrap ga-2">
        <VBtn color="primary" variant="tonal" prepend-icon="mdi-plus" :disabled="!start" @click="add">
          {{ t('dashboards.lidar.scenario.add') }}
        </VBtn>
        <VBtn variant="text" prepend-icon="mdi-broom" :disabled="!events.length" @click="clear">
          {{ t('dashboards.lidar.scenario.clear') }}
        </VBtn>
      </div>

      <div v-if="allEvents.length" class="d-flex flex-wrap ga-2">
        <VChip
          v-for="row in rows"
          :key="row.event.id"
          :closable="!row.event.registered"
          :color="row.event.registered ? 'secondary' : undefined"
          :prepend-icon="row.event.registered ? 'mdi-calendar-check' : undefined"
          :title="row.event.notes"
          :close-label="t('dashboards.lidar.scenario.remove', { name: row.label })"
          @click:close="remove(row.event.id)"
        >
          {{ row.label }} · {{ row.when }}
        </VChip>
      </div>
      <div v-if="registered.length" class="text-caption text-medium-emphasis">
        {{ t('dashboards.lidar.scenario.registeredHint') }}
      </div>

      <div v-if="allEvents.length" class="d-flex flex-wrap ga-4">
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.scenario.tilePeak')"
          :value="formatNumber(summary.peak, 0)"
          :unit="summary.peak === null ? undefined : people"
          icon="mdi-chart-bell-curve"
          :hint="summary.peakAt ? formatDateTime(summary.peakAt, timeZone) : undefined"
          color="warning"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.scenario.tileExtra')"
          :value="summary.extraAtPeak === null ? t('common.noValue') : `+${formatNumber(summary.extraAtPeak, 0)}`"
          :unit="summary.extraAtPeak === null ? undefined : people"
          icon="mdi-account-multiple-plus-outline"
          color="primary"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.scenario.tileOver')"
          :value="overValue"
          :unit="summary.hoursOverCapacity === null ? undefined : 'h'"
          icon="mdi-alert-outline"
          :hint="overHint"
          :color="summary.hoursOverCapacity ? 'error' : 'secondary'"
        />
      </div>
      <div v-else class="text-body-2 text-medium-emphasis">{{ t('dashboards.lidar.scenario.noEvents') }}</div>

      <LineChart :series="series" :units="people" :height="300" :title="t('dashboards.lidar.scenario.chart')" />

      <VTable v-if="allEvents.length" density="compact">
        <thead>
          <tr>
            <th>{{ t('dashboards.lidar.scenario.table.event') }}</th>
            <th>{{ t('dashboards.lidar.scenario.table.when') }}</th>
            <th>{{ t('dashboards.lidar.scenario.table.weather') }}</th>
            <th class="text-end">{{ t('dashboards.lidar.scenario.table.extra') }}</th>
            <th v-if="canRegister"><span class="d-sr-only">{{ t('dashboards.lidar.registry.table.actions') }}</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.event.id">
            <td>{{ row.label }}</td>
            <td>{{ row.when }}</td>
            <td>{{ row.weather }}</td>
            <td class="text-end">{{ row.extra === null ? t('common.noValue') : `+${formatNumber(row.extra, 0)}` }}</td>
            <td v-if="canRegister" class="text-end">
              <VBtn
                v-if="!row.event.registered"
                variant="text"
                size="small"
                prepend-icon="mdi-calendar-check"
                :aria-label="t('dashboards.lidar.registry.registerThis', { name: row.label })"
                @click="registerScenario(row.event)"
              >
                {{ t('dashboards.lidar.registry.registerShort') }}
              </VBtn>
            </td>
          </tr>
        </tbody>
      </VTable>

      <VDivider v-if="zoneUrn" />
      <EventRegistry
        v-if="zoneUrn"
        v-model:draft="registryDraft"
        :target="target"
        :zone-urn="zoneUrn"
        :zone-name="zoneName"
        :time-zone="zone"
        @loaded="registry = $event"
        @registered="onRegistered"
      />

      <div class="text-caption text-medium-emphasis">{{ t('dashboards.lidar.scenario.assumptions') }}</div>
    </div>
  </ChartCard>
</template>
