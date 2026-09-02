<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { DateTime } from 'luxon'
import StateBlock from '@/components/StateBlock.vue'
import StatTile from '@/components/StatTile.vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { formatDateTime, formatNumber, relativeFromNow } from '@/lib/format'
import type { Dashboard, Measure } from '@/types'
import { BarChart, LineChart, hasData, type ChartPoint, type ChartSeries } from '../../charts'
import { autoAggregation, type DateRange } from '../../lib/range'
import OccupancyGauge from './charts/OccupancyGauge.vue'
import AttributesCard from './components/AttributesCard.vue'
import ChartCard from './components/ChartCard.vue'
import LidarControlBar from './components/LidarControlBar.vue'
import LidarNotice from './components/LidarNotice.vue'
import {
  fetchZoneSeries,
  incrementsOf,
  levelColor,
  levelKey,
  MATRIX_POINTS,
  meanByHour,
  meanByWeekday,
  numericValue,
  presetHint,
  refOf,
  summarise,
  type SeriesSpec,
} from './data'
import { useZone } from './useZone'

/** Se declaran las cuatro props aunque el registro solo prometa `dashboard`: si el anfitrion
 * pasa alguna mas, declararla evita que Vue la escupa como atributo del nodo raiz. */
const props = defineProps<{
  dashboard: Dashboard
  range?: DateRange
  timeZone?: string
  reloadKey?: number
}>()

const {
  zones,
  zoneId,
  zone,
  measures,
  profile,
  usedFallbackEntities,
  preset,
  range,
  ownRange,
  timeZone,
  loading,
  error,
  reload,
} = useZone(props)

/**
 * La media y el maximo del periodo son dos agregados de la misma medida, asi que hace falta un
 * intervalo: sin agregar, ambas series serian identicas y la leyenda mentiria.
 */
const interval = computed(() => autoAggregation(range.value)?.interval ?? 'PT1H')
const hourly = computed(() => interval.value === 'PT1H')

const seriesLoading = ref(false)
const seriesError = ref<string | null>(null)
const trendMean = ref<ChartPoint[]>([])
const trendMax = ref<ChartPoint[]>([])
const inflow = ref<ChartPoint[]>([])
const outflow = ref<ChartPoint[]>([])
/** Serie forzada a hora, unica base valida para los perfiles por hora y por dia. */
const shape = ref<ChartPoint[]>([])

const flowRoles = computed(() => {
  const roles = profile.value?.roles
  return { inflow: roles?.inflow ?? null, outflow: roles?.outflow ?? null }
})

function reset() {
  trendMean.value = []
  trendMax.value = []
  inflow.value = []
  outflow.value = []
  shape.value = []
}

async function loadSeries() {
  const entity = zone.value
  const measureId = profile.value?.occupancy?.id
  if (!entity || !measureId) {
    reset()
    seriesError.value = null
    return
  }

  seriesLoading.value = true
  seriesError.value = null
  try {
    const ref_ = refOf(entity)
    const specs: SeriesSpec[] = [
      { key: 'mean', fn: 'mean', measureId },
      { key: 'max', fn: 'max', measureId },
    ]
    // Un contador acumulativo solo se puede agregar por su maximo: su media no significa nada.
    if (flowRoles.value.inflow) specs.push({ key: 'in', fn: 'max', measureId: flowRoles.value.inflow.id })
    if (flowRoles.value.outflow) specs.push({ key: 'out', fn: 'max', measureId: flowRoles.value.outflow.id })

    const [trendRes, shapeRes] = await Promise.all([
      fetchZoneSeries(ref_, specs, range.value, { forceInterval: interval.value }),
      // Con intervalo horario la serie de tendencia ya sirve de perfil: no se repite la consulta.
      hourly.value
        ? Promise.resolve<Record<string, ChartPoint[]>>({})
        : fetchZoneSeries(ref_, [{ key: 'shape', fn: 'mean', measureId }], range.value, {
            forceInterval: 'PT1H',
            limit: MATRIX_POINTS,
          }),
    ])

    trendMean.value = trendRes.mean ?? []
    trendMax.value = trendRes.max ?? []
    inflow.value = trendRes.in ?? []
    outflow.value = trendRes.out ?? []
    shape.value = shapeRes.shape ?? []
  } catch (e) {
    seriesError.value = errorMessage(e)
    reset()
  } finally {
    seriesLoading.value = false
  }
}

watch(
  [
    () => zone.value?.id,
    () => range.value.start,
    () => range.value.end,
    () => profile.value?.occupancy?.id,
    () => flowRoles.value.inflow?.id,
    () => flowRoles.value.outflow?.id,
  ],
  () => void loadSeries(),
  { immediate: true },
)

const meanSummary = computed(() => summarise(trendMean.value))
const peakSummary = computed(() => summarise(trendMax.value))

const shapePoints = computed(() => (hourly.value ? trendMean.value : shape.value))
const byHour = computed(() => meanByHour(shapePoints.value, timeZone.value))
const byWeekday = computed(() => meanByWeekday(shapePoints.value, timeZone.value))

/**
 * Con rangos muy largos la consulta horaria no cabe en el tope de puntos y solo devuelve la
 * cola del periodo: se dice cuantos dias cubre en lugar de dar por bueno un perfil incompleto.
 */
const profileDays = computed<number | null>(() => {
  const first = shapePoints.value[0]?.t
  if (!first) return null
  const start = DateTime.fromISO(range.value.start, { zone: 'utc' })
  const end = DateTime.fromISO(range.value.end, { zone: 'utc' })
  const from = DateTime.fromISO(first, { zone: 'utc' })
  if (!start.isValid || !end.isValid || !from.isValid) return null
  if (from.diff(start, 'days').days < 2) return null
  return Math.max(1, Math.round(end.diff(from, 'days').days))
})

const capacity = computed<number | null>(() => profile.value?.capacity ?? null)
const ratio = computed<number | null>(() => profile.value?.ratio ?? null)

const percentColor = computed(() => levelColor(ratio.value))

const rangeHint = computed(() => presetHint(preset.value))

interface Tile {
  id: string
  label: string
  value: string
  unit?: string
  icon: string
  hint?: string
  color: string
}

/**
 * La tira solo lleva los indicadores que la zona publica de verdad: se arma aqui para no
 * repetir siete condiciones en la plantilla, y para que «sin dato» sea siempre null.
 */
const tiles = computed<Tile[]>(() => {
  const p = profile.value
  if (!p) return []
  const people = t('dashboards.lidar.people')
  const list: Tile[] = []

  if (p.occupancy) {
    list.push({
      id: 'current',
      label: t('dashboards.lidar.tile.current'),
      value: p.current === null ? t('common.noValue') : formatNumber(p.current, 0),
      unit: people,
      icon: 'mdi-account-group-outline',
      hint: p.updatedAt
        ? t('dashboards.lidar.tile.updated', { when: relativeFromNow(p.updatedAt, timeZone.value) })
        : t('dashboards.lidar.tile.noReading'),
      color: 'primary',
    })
  }

  if (ratio.value !== null) {
    list.push({
      id: 'percent',
      label: t('dashboards.lidar.tile.percent'),
      value: formatNumber(ratio.value * 100, 0),
      unit: '%',
      icon: 'mdi-gauge',
      hint: t(levelKey(ratio.value)),
      color: percentColor.value,
    })
  }

  if (capacity.value !== null) {
    list.push({
      id: 'capacity',
      label: t('dashboards.lidar.tile.capacity'),
      value: formatNumber(capacity.value, 0),
      unit: people,
      icon: 'mdi-account-multiple-outline',
      color: 'secondary',
    })
  }

  if (p.occupancy) {
    list.push({
      id: 'average',
      label: t('dashboards.lidar.tile.average'),
      value: formatNumber(meanSummary.value.mean, 0),
      unit: people,
      icon: 'mdi-chart-timeline-variant',
      hint: rangeHint.value,
      color: 'primary',
    })
    list.push({
      id: 'peak',
      label: t('dashboards.lidar.tile.peak'),
      value: formatNumber(peakSummary.value.max, 0),
      unit: people,
      icon: 'mdi-arrow-up-bold-outline',
      hint: peakSummary.value.maxAt
        ? t('dashboards.lidar.tile.peakAt', { when: formatDateTime(peakSummary.value.maxAt, timeZone.value) })
        : undefined,
      color: 'warning',
    })
  }

  const dwell = numericValue(p.roles.dwell?.value)
  if (dwell !== null) {
    list.push({
      id: 'dwell',
      label: t('dashboards.lidar.tile.dwell'),
      value: formatNumber(dwell, 1),
      unit: p.roles.dwell?.units,
      icon: 'mdi-timer-outline',
      color: 'primary',
    })
  }

  const density = numericValue(p.roles.density?.value)
  if (density !== null) {
    list.push({
      id: 'density',
      label: t('dashboards.lidar.tile.density'),
      value: formatNumber(density, 2),
      unit: p.roles.density?.units,
      icon: 'mdi-blur',
      color: 'primary',
    })
  }

  return list
})

const trendSeries = computed<ChartSeries[]>(() => [
  { name: t('dashboards.lidar.analytics.trendMean'), units: t('dashboards.lidar.people'), points: trendMean.value },
  { name: t('dashboards.lidar.analytics.trendMax'), units: t('dashboards.lidar.people'), points: trendMax.value },
])

/** El contador es acumulativo: lo que interesa es cuanta gente ha pasado en cada intervalo. */
const flowSeries = computed<ChartSeries[]>(() => {
  const list: ChartSeries[] = []
  if (flowRoles.value.inflow) {
    list.push({
      name: t('dashboards.lidar.analytics.flowIn'),
      units: t('dashboards.lidar.people'),
      points: incrementsOf(inflow.value),
    })
  }
  if (flowRoles.value.outflow) {
    list.push({
      name: t('dashboards.lidar.analytics.flowOut'),
      units: t('dashboards.lidar.people'),
      points: incrementsOf(outflow.value),
    })
  }
  return list
})

const hasFlowRoles = computed(() => !!flowRoles.value.inflow || !!flowRoles.value.outflow)

/** Atributos de la zona. La fiabilidad puede llegar como numero y entonces no esta entre los
 * atributos de texto: se anade a mano para que salga con su distintivo. */
const attributes = computed<Measure[]>(() => {
  const p = profile.value
  if (!p) return []
  const confidence = p.roles.confidence
  const rows = [...p.text]
  if (confidence && !rows.some((m) => m.id === confidence.id)) rows.unshift(confidence)
  return rows
})
</script>

<template>
  <div>
    <LidarControlBar
      :zones="zones"
      :zone-id="zoneId"
      :preset="preset"
      :show-range="ownRange"
      :loading="loading"
      @update:zone-id="zoneId = $event"
      @update:preset="preset = $event"
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
      <LidarNotice v-if="usedFallbackEntities" type="warning" :text="t('dashboards.lidar.fallbackEntities')" />
      <LidarNotice
        v-if="!measures.length && !loading"
        :text="t('dashboards.lidar.noMeasures')"
        :hint="t('dashboards.lidar.noMeasuresHint')"
      />
      <LidarNotice
        v-else-if="!profile?.occupancy"
        :text="t('dashboards.lidar.noOccupancy')"
        :hint="t('dashboards.lidar.noOccupancyHint')"
      />
      <LidarNotice
        v-else-if="profile.occupancyIsFallback"
        type="warning"
        :text="t('dashboards.lidar.occupancyFallback', { measure: profile.occupancy.name })"
      />

      <div v-if="tiles.length" class="d-flex flex-wrap ga-4 mb-6">
        <StatTile
          v-for="tile in tiles"
          :key="tile.id"
          style="flex: 1 1 200px"
          :label="tile.label"
          :value="tile.value"
          :unit="tile.unit"
          :icon="tile.icon"
          :hint="tile.hint"
          :color="tile.color"
        />
      </div>

      <VRow class="mb-2">
        <VCol cols="12" md="4">
          <ChartCard
            :title="t('dashboards.lidar.analytics.gauge')"
            :loading="loading"
            :error="error"
            :empty="capacity === null || profile?.current === null"
            :empty-text="capacity === null ? t('dashboards.lidar.noCapacity') : undefined"
            :empty-hint="capacity === null ? t('dashboards.lidar.noCapacityHint') : undefined"
            empty-icon="mdi-gauge-empty"
            @retry="reload"
          >
            <OccupancyGauge v-if="capacity !== null" :value="profile?.current ?? null" :capacity="capacity" />
          </ChartCard>
        </VCol>
        <VCol cols="12" md="8">
          <ChartCard
            :title="t('dashboards.lidar.analytics.trend')"
            :subtitle="profile?.occupancy ? t('dashboards.lidar.measureUsed', { measure: profile.occupancy.name }) : undefined"
            :loading="seriesLoading"
            :error="seriesError"
            :empty="!hasData(trendSeries)"
            @retry="loadSeries"
          >
            <LineChart :series="trendSeries" :height="280" />
          </ChartCard>
        </VCol>
      </VRow>

      <VRow class="mb-2">
        <VCol cols="12" md="6">
          <ChartCard
            :title="t('dashboards.lidar.analytics.byHour')"
            :loading="seriesLoading"
            :error="seriesError"
            :empty="!shapePoints.length"
            @retry="loadSeries"
          >
            <BarChart
              :series="[{ name: t('dashboards.lidar.analytics.trendMean'), units: t('dashboards.lidar.people'), points: byHour.map((b) => ({ t: b.label, v: b.value })) }]"
              :height="260"
            />
            <div v-if="profileDays !== null" class="text-caption text-medium-emphasis mt-3">
              {{ t('dashboards.lidar.analytics.profileWindow', { days: profileDays }) }}
            </div>
          </ChartCard>
        </VCol>
        <VCol cols="12" md="6">
          <ChartCard
            :title="t('dashboards.lidar.analytics.byWeekday')"
            :loading="seriesLoading"
            :error="seriesError"
            :empty="!shapePoints.length"
            @retry="loadSeries"
          >
            <BarChart
              :series="[{ name: t('dashboards.lidar.analytics.trendMean'), units: t('dashboards.lidar.people'), points: byWeekday.map((b) => ({ t: b.label, v: b.value })) }]"
              :height="260"
            />
            <div v-if="profileDays !== null" class="text-caption text-medium-emphasis mt-3">
              {{ t('dashboards.lidar.analytics.profileWindow', { days: profileDays }) }}
            </div>
          </ChartCard>
        </VCol>
      </VRow>

      <VRow class="mb-2">
        <VCol cols="12">
          <ChartCard
            :title="t('dashboards.lidar.analytics.flow')"
            :subtitle="t('dashboards.lidar.analytics.flowHint')"
            :loading="seriesLoading"
            :error="seriesError"
            :empty="!hasFlowRoles || !hasData(flowSeries)"
            :empty-text="hasFlowRoles ? undefined : t('dashboards.lidar.analytics.noFlow')"
            :empty-hint="hasFlowRoles ? undefined : t('dashboards.lidar.analytics.noFlowHint')"
            empty-icon="mdi-swap-horizontal"
            @retry="loadSeries"
          >
            <BarChart :series="flowSeries" :height="280" />
          </ChartCard>
        </VCol>
      </VRow>

      <VRow>
        <VCol cols="12">
          <AttributesCard
            :title="t('dashboards.lidar.analytics.attributes')"
            :attributes="attributes"
            :confidence-id="profile?.roles.confidence?.id ?? null"
            :time-zone="timeZone"
            :loading="loading"
            :error="error"
            @retry="reload"
          />
        </VCol>
      </VRow>
    </StateBlock>
  </div>
</template>
