<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { DateTime } from 'luxon'
import StateBlock from '@/components/StateBlock.vue'
import StatTile from '@/components/StatTile.vue'
import { errorMessage } from '@/api/http'
import { getEntityMeasures } from '@/features/entities/api/entities'
import { geolocationLatLng } from '@/features/map/lib/geometry'
import { t } from '@/i18n'
import { formatDateTime, formatNumber, relativeFromNow } from '@/lib/format'
import type { Dashboard } from '@/types'
import { BarChart, type ChartPoint } from '../../charts'
import { rangeHours } from '../../lib/range'
import ChartCard from './components/ChartCard.vue'
import LidarControlBar from './components/LidarControlBar.vue'
import LidarNotice from './components/LidarNotice.vue'
import ZoneMapCard, { type ZoneMarker } from './components/ZoneMapCard.vue'
import OccupancyMatrixChart from './charts/OccupancyMatrixChart.vue'
import {
  describeZone,
  fetchZoneSeries,
  hourWeekdayMatrix,
  levelColor,
  levelKey,
  MATRIX_POINTS,
  meanByHour,
  presetHint,
  refOf,
  summarise,
} from './data'
import { useZone } from './useZone'
import type { DateRange } from '../../lib/range'

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

const seriesLoading = ref(false)
const seriesError = ref<string | null>(null)
const trend = ref<ChartPoint[]>([])
/** Ocupacion actual de TODAS las zonas asignadas, para colorear el mapa. */
const liveByZone = ref<Record<number, { value: number | null; ratio: number | null }>>({})
const matrix = ref<ChartPoint[]>([])

const matrixRange = computed<DateRange>(() => {
  const span = rangeHours(range.value)
  if (span >= 168) return range.value
  const end = DateTime.fromISO(range.value.end, { zone: 'utc' })
  const start = end.minus({ hours: 168 }).toISO({ suppressMilliseconds: true }) ?? range.value.start
  return { start, end: range.value.end }
})

async function loadSeries() {
  if (!zone.value || !profile.value?.occupancy) {
    trend.value = []
    matrix.value = []
    seriesError.value = null
    return
  }
  seriesLoading.value = true
  seriesError.value = null
  try {
    const measureId = profile.value.occupancy.id
    const [trendRes, matrixRes] = await Promise.all([
      fetchZoneSeries(refOf(zone.value), [{ key: 'mean', fn: 'mean', measureId }], range.value),
      fetchZoneSeries(refOf(zone.value), [{ key: 'matrix', fn: 'mean', measureId }], matrixRange.value, {
        forceInterval: 'PT1H',
        limit: MATRIX_POINTS,
      }),
    ])
    trend.value = trendRes.mean ?? []
    matrix.value = matrixRes.matrix ?? []
  } catch (e) {
    seriesError.value = errorMessage(e)
    trend.value = []
    matrix.value = []
  } finally {
    seriesLoading.value = false
  }
}

watch(
  [zone, () => range.value.start, () => range.value.end, () => profile.value?.occupancy?.id],
  () => void loadSeries(),
  { immediate: true },
)

/** Como mucho las 12 primeras, para no encadenar peticiones sin fin. */
async function loadLive() {
  const targets = zones.value.slice(0, 12)
  const results = await Promise.allSettled(targets.map((z) => getEntityMeasures(refOf(z))))
  const next: Record<number, { value: number | null; ratio: number | null }> = {}
  results.forEach((res, index) => {
    if (res.status === 'fulfilled') {
      const p = describeZone(res.value)
      next[targets[index].id] = { value: p.current, ratio: p.ratio }
    }
  })
  liveByZone.value = next
}

watch(zones, () => void loadLive(), { immediate: true })

const summary = computed(() => summarise(trend.value))

const ratio = computed(() => profile.value?.ratio ?? null)

const percentColor = computed(() => levelColor(ratio.value))

const rangeHint = computed(() => presetHint(preset.value))

const markers = computed<ZoneMarker[]>(() =>
  zones.value.flatMap((z) => {
    const latLng = geolocationLatLng(z.geolocation)
    if (!latLng) return []
    const polygon =
      z.geolocation?.type === 'Polygon'
        ? z.geolocation.coordinates[0].map(([lon, lat]) => [lat, lon] as [number, number])
        : null
    const live = liveByZone.value[z.id]
    return [
      {
        id: z.id,
        name: z.name,
        value: live?.value ?? null,
        ratio: live?.ratio ?? null,
        latLng,
        polygon,
        selected: z.id === zoneId.value,
      },
    ]
  }),
)

const matrixWindowNotice = computed(() => rangeHours(range.value) < 168)

const matrixCells = computed(() => hourWeekdayMatrix(matrix.value, timeZone.value))
const profileBuckets = computed(() => meanByHour(matrix.value, timeZone.value))
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
      <LidarNotice v-if="!measures.length && !loading" :text="t('dashboards.lidar.noMeasures')" :hint="t('dashboards.lidar.noMeasuresHint')" />
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
      <LidarNotice
        v-if="profile && profile.capacity === null"
        :text="t('dashboards.lidar.noCapacity')"
        :hint="t('dashboards.lidar.noCapacityHint')"
      />

      <div class="d-flex flex-wrap ga-4 mb-6">
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.tile.current')"
          :value="profile?.current !== null && profile?.current !== undefined ? formatNumber(profile.current, 0) : t('common.noValue')"
          :unit="t('dashboards.lidar.people')"
          icon="mdi-account-group-outline"
          :hint="profile?.updatedAt ? t('dashboards.lidar.tile.updated', { when: relativeFromNow(profile.updatedAt, timeZone) }) : t('dashboards.lidar.tile.noReading')"
          color="primary"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.tile.percent')"
          :value="ratio === null ? t('common.noValue') : formatNumber(ratio * 100, 0)"
          :unit="ratio === null ? undefined : '%'"
          icon="mdi-gauge"
          :hint="ratio === null ? t('dashboards.lidar.tile.noCapacityHint') : t(levelKey(ratio))"
          :color="percentColor"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.tile.average')"
          :value="formatNumber(summary.mean, 0)"
          :unit="t('dashboards.lidar.people')"
          icon="mdi-chart-timeline-variant"
          :hint="rangeHint"
          color="primary"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.tile.peak')"
          :value="formatNumber(summary.max, 0)"
          :unit="t('dashboards.lidar.people')"
          icon="mdi-arrow-up-bold-outline"
          :hint="summary.maxAt ? t('dashboards.lidar.tile.peakAt', { when: formatDateTime(summary.maxAt, timeZone) }) : undefined"
          color="warning"
        />
      </div>

      <VRow class="mb-2">
        <VCol cols="12" md="5">
          <VCard>
            <div class="d-flex align-center ga-2 px-4 pt-4 pb-2">
              <VIcon icon="mdi-map-marker-radius-outline" size="18" class="text-medium-emphasis" />
              <div class="min-w-0">
                <div class="text-subtitle-2 font-weight-medium">{{ t('dashboards.lidar.heatmap.map') }}</div>
                <div class="text-caption text-medium-emphasis">{{ t('dashboards.lidar.heatmap.mapHint') }}</div>
              </div>
            </div>
            <VDivider />
            <div class="pa-4">
              <ZoneMapCard :markers="markers" :loading="loading" :error="error" @select="zoneId = $event" @retry="reload" />
            </div>
          </VCard>
        </VCol>
        <VCol cols="12" md="7">
          <ChartCard
            :title="t('dashboards.lidar.heatmap.matrix')"
            :subtitle="profile?.occupancy ? t('dashboards.lidar.heatmap.matrixHint', { measure: profile.occupancy.name }) : undefined"
            :loading="seriesLoading"
            :error="seriesError"
            :empty="!matrix.length"
            :min-height="340"
            @retry="loadSeries"
          >
            <OccupancyMatrixChart :cells="matrixCells" :max="profile?.capacity ?? null" :units="t('dashboards.lidar.people')" />
            <div class="text-caption text-medium-emphasis mt-3">
              {{ profile?.capacity ? t('dashboards.lidar.heatmap.scaleCapacity', { capacity: formatNumber(profile.capacity, 0) }) : t('dashboards.lidar.heatmap.scaleRelative') }}
            </div>
            <div v-if="matrixWindowNotice" class="text-caption text-medium-emphasis mt-1">
              {{ t('dashboards.lidar.heatmap.matrixWindow') }}
            </div>
          </ChartCard>
        </VCol>
      </VRow>

      <VRow>
        <VCol cols="12">
          <ChartCard :title="t('dashboards.lidar.heatmap.profile')" :loading="seriesLoading" :error="seriesError" :empty="!matrix.length" @retry="loadSeries">
            <BarChart
              :series="[{ name: t('dashboards.lidar.heatmap.profileSeries'), units: t('dashboards.lidar.people'), points: profileBuckets.map((b) => ({ t: b.label, v: b.value })) }]"
              :height="260"
            />
          </ChartCard>
        </VCol>
      </VRow>
    </StateBlock>
  </div>
</template>
