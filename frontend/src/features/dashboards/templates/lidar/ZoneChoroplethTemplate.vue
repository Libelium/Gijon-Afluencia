<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import StateBlock from '@/components/StateBlock.vue'
import StatTile from '@/components/StatTile.vue'
import { getEntityMeasures, listEntities } from '@/features/entities/api/entities'
import { geolocationLatLng } from '@/features/map/lib/geometry'
import { t } from '@/i18n'
import { formatNumber, urnTail } from '@/lib/format'
import type { Dashboard, Entity } from '@/types'
import type { ChartPoint } from '../../charts'
import { rangeHours, type DateRange } from '../../lib/range'
import HourTimeline from '../shared/HourTimeline.vue'
import { fetchSeries } from '../shared/series'
import { datamodelOf } from '../contract'
import {
  deviceUrn,
  NEAR_FULL,
  polygonOf,
  ratioOf,
  summarize,
  timeSteps,
  twinUrn,
  valueAt,
  zoneSerials,
  type DeviceKind,
  type ZoneDevice,
  type ZoneState,
} from './choropleth'
import ChoroplethMap from './components/ChoroplethMap.vue'
import LidarControlBar from './components/LidarControlBar.vue'
import LidarNotice from './components/LidarNotice.vue'
import { describeZone, refOf, zoneModel } from './data'
import { useZone } from './useZone'

/** Se declaran las cuatro props aunque el registro solo prometa `dashboard`: si el anfitrion
 * pasa alguna mas, declararla evita que Vue la escupa como atributo del nodo raiz. */
const props = defineProps<{
  dashboard: Dashboard
  range?: DateRange
  timeZone?: string
  reloadKey?: number
}>()

const { zones, zoneId, preset, custom, range, ownRange, timeZone, loading, error, reload } = useZone(props)

interface LiveZone {
  value: number | null
  capacity: number | null
  /** Medida de ocupacion de la zona, para pedir su serie por horas. */
  measureId: string | null
  /** Dispositivos que la fusion declara en la zona. */
  serials: Record<DeviceKind, string[]>
}

/** Lectura actual de cada zona asignada. */
const live = ref<Record<number, LiveZone>>({})
const liveLoading = ref(false)
/** Ocupacion de cada zona en cada paso de la barra, por id. */
const hourly = ref<Map<string, ChartPoint[]>>(new Map())
/** Dispositivos de todas las zonas que tienen ubicacion. */
const devices = ref<ZoneDevice[]>([])
/** Paso de la barra, o null para la ocupacion de ahora. */
const step = ref<number | null>(null)

/** Zonas que se piden a la vez: llegan todas sin lanzar decenas de peticiones juntas. */
const LIVE_BATCH = 6
/** URN que se piden por consulta: la lista viaja en el cuerpo y no conviene alargarla sin fin. */
const DEVICE_BATCH = 50
let liveRequest = 0

async function loadLive() {
  const request = ++liveRequest
  liveLoading.value = true
  const next: Record<number, LiveZone> = {}
  try {
    for (let i = 0; i < zones.value.length; i += LIVE_BATCH) {
      const batch = zones.value.slice(i, i + LIVE_BATCH)
      const results = await Promise.allSettled(batch.map((zone) => getEntityMeasures(refOf(zone))))
      // Una recarga posterior ya esta pidiendo lo suyo: este resultado llega tarde.
      if (request !== liveRequest) return
      results.forEach((result, index) => {
        if (result.status !== 'fulfilled') return
        const profile = describeZone(result.value)
        next[batch[index].id] = {
          value: profile.current,
          capacity: profile.capacity,
          measureId: profile.occupancy?.id ?? null,
          serials: zoneSerials(result.value),
        }
      })
    }
    await addTwinCapacity(next)
    if (request !== liveRequest) return
    live.value = next
  } finally {
    if (request === liveRequest) liveLoading.value = false
  }
}

watch(zones, () => void loadLive(), { immediate: true })

/**
 * El aforo maximo de una zona no esta en la zona combinada sino en su gemela de analitica del
 * LIDAR (`maxCapacity`). Se completa desde ella el de las zonas que no lo traen.
 */
async function addTwinCapacity(next: Record<number, LiveZone>) {
  const from = zoneModel()
  const to = datamodelOf('zoneScan')
  const wanted = new Map<string, number>()
  for (const zone of zones.value) {
    if (next[zone.id]?.capacity != null) continue
    const urn = twinUrn(zone.urn, from, to)
    if (urn) wanted.set(urn, zone.id)
  }
  if (!wanted.size) return
  try {
    const urns = [...wanted.keys()]
    const twins: Entity[] = []
    for (let i = 0; i < urns.length; i += DEVICE_BATCH) {
      const chunk = urns.slice(i, i + DEVICE_BATCH)
      const { rows } = await listEntities({ page: 1, paginationSize: chunk.length, urn: chunk.join(',') })
      twins.push(...rows)
    }
    for (let i = 0; i < twins.length; i += LIVE_BATCH) {
      const batch = twins.slice(i, i + LIVE_BATCH)
      const results = await Promise.allSettled(batch.map((twin) => getEntityMeasures(refOf(twin))))
      results.forEach((result, index) => {
        const zoneId = wanted.get(batch[index].urn)
        if (result.status !== 'fulfilled' || zoneId === undefined || !next[zoneId]) return
        next[zoneId].capacity = describeZone(result.value).capacity
      })
    }
  } catch {
    // Sin gemela la zona sigue sin aforo, en gris y con su ocupacion en personas.
  }
}

let devicesRequest = 0

/** Situa en el mapa los dispositivos de cada zona, buscando la entidad que lleva su ubicacion. */
async function loadDevices() {
  const request = ++devicesRequest
  const models = { smartspot: datamodelOf('flowObserved'), lidar: datamodelOf('lidarObserved') }
  const wanted = zones.value.flatMap((zone) => {
    const serials = live.value[zone.id]?.serials
    if (!serials) return []
    return (['smartspot', 'lidar'] as const).flatMap((kind) =>
      serials[kind].map((serial) => ({ zone, kind, serial, urn: deviceUrn(kind, serial, models) })),
    )
  })
  const located = new Map<string, [number, number]>()
  try {
    for (let i = 0; i < wanted.length; i += DEVICE_BATCH) {
      const urns = wanted.slice(i, i + DEVICE_BATCH).map((item) => item.urn)
      const { rows } = await listEntities({ page: 1, paginationSize: urns.length, urn: urns.join(',') })
      for (const row of rows) {
        const latLng = geolocationLatLng(row.geolocation)
        if (latLng) located.set(row.urn, latLng)
      }
    }
  } catch {
    // Sin dispositivos el mapa sigue pintando las zonas: son un apoyo, no el dato.
  }
  if (request !== devicesRequest) return
  devices.value = wanted.flatMap(({ zone, kind, serial, urn }) => {
    const latLng = located.get(urn)
    if (!latLng) return []
    const zoneName = zone.name || urnTail(zone.urn)
    return [{ key: urn, kind, serial, zoneId: zone.id, zoneName, lat: latLng[0], lon: latLng[1] }]
  })
}

watch(live, () => void loadDevices())

/** Por horas cabe un mes: pasado eso, la serie superaria el tope de puntos de una consulta. */
const HOURLY_MAX_HOURS = 24 * 31
/** Por defecto, por horas hasta una semana; con mas, por dias, para que la barra no sea eterna. */
const HOURLY_DEFAULT_HOURS = 24 * 7

const hourlyAllowed = computed(() => rangeHours(range.value) <= HOURLY_MAX_HOURS)
/** Paso elegido a mano, o null para el que toca segun el rango. */
const chosenStep = ref<'hour' | 'day' | null>(null)
const granularity = computed<'hour' | 'day'>(() => {
  if (!hourlyAllowed.value) return 'day'
  return chosenStep.value ?? (rangeHours(range.value) <= HOURLY_DEFAULT_HOURS ? 'hour' : 'day')
})

let hourlyRequest = 0

async function loadHourly() {
  const request = ++hourlyRequest
  const requests = zones.value.flatMap((zone) => {
    const measureId = live.value[zone.id]?.measureId
    return measureId ? [{ key: String(zone.id), ref: refOf(zone), measureId }] : []
  })
  try {
    const interval = granularity.value === 'hour' ? 'PT1H' : 'P1D'
    const series = await fetchSeries(requests, range.value, { aggregation: { type: 'mean', interval } })
    if (request === hourlyRequest) hourly.value = series
  } catch {
    // Sin series por horas el mapa sigue mostrando la ocupacion de ahora; la barra queda vacia.
    if (request === hourlyRequest) hourly.value = new Map()
  }
}

watch([live, granularity, () => range.value.start, () => range.value.end], () => void loadHourly())

const steps = computed(() => timeSteps(hourly.value.values()))

/** Cada zona en el momento elegido: ahora, o la media de esa hora. El aforo es el publicado hoy. */
const states = computed<ZoneState[]>(() =>
  zones.value.map((zone) => {
    const current = live.value[zone.id]
    const capacity = current?.capacity ?? null
    const value =
      step.value === null
        ? (current?.value ?? null)
        : valueAt(hourly.value.get(String(zone.id)) ?? [], steps.value[step.value])
    return {
      id: zone.id,
      name: zone.name || urnTail(zone.urn),
      polygon: polygonOf(zone.geolocation),
      value,
      capacity,
      ratio: ratioOf(value, capacity),
    }
  }),
)

const summary = computed(() => summarize(states.value))
const selected = computed(() => states.value.find((state) => state.id === zoneId.value) ?? null)

const unpainted = computed(() => states.value.filter((state) => !state.polygon).length)
const withoutCapacity = computed(() => states.value.filter((state) => state.capacity === null).length)

function percent(ratio: number | null): string {
  return ratio === null ? t('common.noValue') : formatNumber(ratio * 100, 0)
}

const moment = computed(() =>
  step.value === null
    ? t('dashboards.lidar.choropleth.momentNow')
    : granularity.value === 'hour'
      ? t('dashboards.lidar.choropleth.momentHour')
      : t('dashboards.lidar.choropleth.momentDay'),
)
</script>

<template>
  <div>
    <LidarControlBar
      :zones="zones"
      :zone-id="zoneId"
      :preset="preset"
      :custom="custom"
      :time-zone="timeZone"
      :show-range="ownRange"
      :loading="loading"
      @update:zone-id="zoneId = $event"
      @update:preset="preset = $event"
      @update:custom="custom = $event"
      @refresh="reload"
    />

    <StateBlock
      :loading="loading"
      :error="error"
      :empty="!zones.length"
      :empty-text="t('dashboards.lidar.noZones')"
      :empty-hint="t('dashboards.lidar.noZonesHint')"
      empty-icon="mdi-map-marker-off-outline"
      skeleton="card"
      @retry="reload"
    >
      <LidarNotice
        v-if="unpainted"
        type="warning"
        :text="t('dashboards.lidar.choropleth.unpainted', { count: unpainted, total: states.length })"
        :hint="t('dashboards.lidar.choropleth.unpaintedHint')"
      />
      <LidarNotice
        v-if="withoutCapacity && !liveLoading"
        :text="t('dashboards.lidar.choropleth.withoutCapacity', { count: withoutCapacity })"
        :hint="t('dashboards.lidar.choropleth.withoutCapacityHint')"
      />

      <div class="d-flex flex-wrap ga-4 mb-6">
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.choropleth.combined')"
          :value="percent(summary.combinedRatio)"
          :unit="summary.combinedRatio === null ? undefined : '%'"
          icon="mdi-account-group-outline"
          :hint="moment"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.choropleth.nearFull', { percent: NEAR_FULL * 100 })"
          :value="summary.nearFull"
          icon="mdi-alert-outline"
          :hint="moment"
          :color="summary.nearFull ? 'error' : 'primary'"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.choropleth.fullest')"
          :value="summary.fullest?.name ?? t('common.noValue')"
          icon="mdi-arrow-up-bold-outline"
          :hint="summary.fullest ? `${percent(summary.fullest.ratio)} %` : moment"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="selected?.name ?? t('dashboards.lidar.choropleth.selected')"
          :value="percent(selected?.ratio ?? null)"
          :unit="selected?.ratio == null ? undefined : '%'"
          icon="mdi-map-marker-outline"
          :hint="
            selected?.value != null
              ? t('dashboards.lidar.choropleth.people', {
                  value: formatNumber(selected.value, 0),
                  capacity: selected.capacity === null ? '—' : formatNumber(selected.capacity, 0),
                })
              : moment
          "
        />
      </div>

      <VCard>
        <div class="d-flex align-center ga-2 px-4 pt-4 pb-2">
          <VIcon icon="mdi-map-legend" size="18" class="text-medium-emphasis" />
          <div class="min-w-0">
            <div class="text-subtitle-2 font-weight-medium">{{ t('dashboards.lidar.choropleth.title') }}</div>
            <div class="text-caption text-medium-emphasis">{{ t('dashboards.lidar.choropleth.hint') }}</div>
          </div>
        </div>
        <VDivider />
        <div class="pa-4">
          <div class="d-flex flex-wrap align-center ga-3 mb-3">
            <span id="choropleth-step" class="text-body-2">{{ t('dashboards.lidar.choropleth.step') }}</span>
            <VBtnToggle
              :model-value="granularity"
              mandatory
              density="compact"
              variant="outlined"
              divided
              aria-labelledby="choropleth-step"
              @update:model-value="chosenStep = $event"
            >
              <VBtn value="hour" size="small" :disabled="!hourlyAllowed">{{ t('dashboards.lidar.choropleth.stepHour') }}</VBtn>
              <VBtn value="day" size="small">{{ t('dashboards.lidar.choropleth.stepDay') }}</VBtn>
            </VBtnToggle>
            <span v-if="!hourlyAllowed" class="text-caption text-medium-emphasis">
              {{ t('dashboards.lidar.choropleth.hourlyLimit') }}
            </span>
          </div>
          <HourTimeline
            v-model="step"
            class="mb-3"
            :steps="steps"
            :daily="granularity === 'day'"
            :summary-label="t('dashboards.lidar.choropleth.now')"
            :time-zone="timeZone"
          />
          <ChoroplethMap :zones="states" :devices="devices" :selected-id="zoneId" @select="zoneId = $event" />
        </div>
      </VCard>
    </StateBlock>
  </div>
</template>
