<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import StateBlock from '@/components/StateBlock.vue'
import StatTile from '@/components/StatTile.vue'
import { errorMessage } from '@/api/http'
import { getEntityMeasures } from '@/features/entities/api/entities'
import { t } from '@/i18n'
import { formatDateTime, formatNumber, relativeFromNow } from '@/lib/format'
import type { Dashboard, Entity, Measure } from '@/types'
import { BarChart, toMillis, type ChartPoint } from '../../charts'
import { autoAggregation, type DateRange } from '../../lib/range'
import PredictionBandChart from './charts/PredictionBandChart.vue'
import AttributesCard from './components/AttributesCard.vue'
import ChartCard from './components/ChartCard.vue'
import LidarControlBar from './components/LidarControlBar.vue'
import LidarNotice from './components/LidarNotice.vue'
import {
  alignSeries,
  describeZone,
  extendRange,
  fetchZoneSeries,
  findPredictionTwin,
  meanByHour,
  presetHint,
  refOf,
  summarise,
  type Aligned,
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

/** Horas que se piden por delante del rango: es el horizonte que publica la tuberia de
 * prevision, y sin ampliar la ventana la parte prevista no llegaria nunca. */
const HORIZON_HOURS = 24

const twin = ref<Entity | null>(null)
const twinMeasures = ref<Measure[]>([])
const twinLoading = ref(false)
const twinError = ref<string | null>(null)
/** Hasta que la busqueda termina no se puede afirmar que la zona no tenga gemela. */
const twinResolved = ref(false)

const twinProfile = computed(() => (twinMeasures.value.length ? describeZone(twinMeasures.value) : null))

async function loadTwin() {
  twin.value = null
  twinMeasures.value = []
  twinResolved.value = false
  twinError.value = null
  if (!zone.value) return

  twinLoading.value = true
  try {
    const found = await findPredictionTwin(zone.value)
    const list = found ? await getEntityMeasures(refOf(found)) : []
    // Se asignan juntos para que el observador de las series se dispare una sola vez.
    twin.value = found
    twinMeasures.value = list
  } catch (e) {
    twinError.value = errorMessage(e)
  } finally {
    twinResolved.value = true
    twinLoading.value = false
  }
}

watch(zone, () => void loadTwin(), { immediate: true })

const chartRange = computed<DateRange>(() => extendRange(range.value, HORIZON_HOURS))

/** Medida y prevision comparten intervalo a la fuerza: con el automatico de cada ventana
 * caerian en rejillas distintas y la banda no cuadraria con la linea medida. */
const interval = computed(() => autoAggregation(chartRange.value)?.interval ?? 'PT1H')

const seriesLoading = ref(false)
const seriesError = ref<string | null>(null)
const aligned = ref<Aligned>({ times: [], values: {} })

async function fetchMeasured(): Promise<Record<string, ChartPoint[]>> {
  const entity = zone.value
  const measureId = profile.value?.occupancy?.id
  if (!entity || !measureId) return {}
  return fetchZoneSeries(refOf(entity), [{ key: 'measured', fn: 'mean', measureId }], range.value, {
    forceInterval: interval.value,
  })
}

async function fetchPredicted(): Promise<Record<string, ChartPoint[]>> {
  const entity = twin.value
  const roles = twinProfile.value?.roles
  const predictedId = roles?.predicted?.id
  if (!entity || !predictedId) return {}

  const specs: SeriesSpec[] = [{ key: 'predicted', fn: 'mean', measureId: predictedId }]
  if (roles?.predLower) specs.push({ key: 'lower', fn: 'mean', measureId: roles.predLower.id })
  if (roles?.predUpper) specs.push({ key: 'upper', fn: 'mean', measureId: roles.predUpper.id })

  return fetchZoneSeries(refOf(entity), specs, chartRange.value, { forceInterval: interval.value })
}

async function loadSeries() {
  const hasMeasured = !!zone.value && !!profile.value?.occupancy
  const hasPredicted = !!twin.value && !!twinProfile.value?.roles.predicted
  if (!hasMeasured && !hasPredicted) {
    aligned.value = { times: [], values: {} }
    seriesError.value = null
    return
  }

  seriesLoading.value = true
  seriesError.value = null
  try {
    const [measuredRes, predictedRes] = await Promise.all([fetchMeasured(), fetchPredicted()])
    aligned.value = alignSeries({
      measured: measuredRes.measured ?? [],
      predicted: predictedRes.predicted ?? [],
      lower: predictedRes.lower ?? [],
      upper: predictedRes.upper ?? [],
    })
  } catch (e) {
    seriesError.value = errorMessage(e)
    aligned.value = { times: [], values: {} }
  } finally {
    seriesLoading.value = false
  }
}

watch(
  [
    () => zone.value?.id,
    () => twin.value?.id,
    () => range.value.start,
    () => range.value.end,
    () => profile.value?.occupancy?.id,
    () => twinProfile.value?.roles.predicted?.id,
  ],
  () => void loadSeries(),
  { immediate: true },
)

const times = computed(() => aligned.value.times)
const measured = computed<(number | null)[]>(() => aligned.value.values.measured ?? [])
const predicted = computed<(number | null)[]>(() => aligned.value.values.predicted ?? [])

/** La banda se anuncia por el papel de medida, no por los datos: que la gemela publique el
 * intervalo y hoy venga vacio es un hueco de datos, no una gemela sin intervalo. */
const hasBand = computed(() => !!twinProfile.value?.roles.predLower && !!twinProfile.value?.roles.predUpper)
const bandLower = computed<(number | null)[] | null>(() =>
  hasBand.value ? (aligned.value.values.lower ?? null) : null,
)
const bandUpper = computed<(number | null)[] | null>(() =>
  hasBand.value ? (aligned.value.values.upper ?? null) : null,
)

/** Primer cubo que cae en el futuro: es donde el grafico dibuja la linea de «Ahora». */
const nowIndex = computed<number | null>(() => {
  const now = Date.now()
  const index = times.value.findIndex((iso) => toMillis(iso) > now)
  return index >= 0 ? index : null
})

/** Valor de una serie en el cubo que contiene el instante actual: el ultimo con marca pasada. */
function valueNow(values: (number | null)[]): number | null {
  const now = Date.now()
  for (let i = times.value.length - 1; i >= 0; i--) {
    if (toMillis(times.value[i]) > now) continue
    const value = values[i]
    if (value !== null && value !== undefined) return value
  }
  return null
}

const predictedNow = computed(() => valueNow(predicted.value))

/** Ultimo cubo con prevision y medida: la desviacion solo significa algo donde hay ambas. */
const lastPair = computed<{ predicted: number; measured: number } | null>(() => {
  for (let i = times.value.length - 1; i >= 0; i--) {
    const p = predicted.value[i]
    const m = measured.value[i]
    if (p !== null && p !== undefined && m !== null && m !== undefined) return { predicted: p, measured: m }
  }
  return null
})

const deviation = computed<number | null>(() =>
  lastPair.value ? lastPair.value.predicted - lastPair.value.measured : null,
)

/** Puntos de desviacion, base del error medio y del perfil por hora. */
const deviationPoints = computed<ChartPoint[]>(() =>
  times.value.flatMap((iso, i) => {
    const p = predicted.value[i]
    const m = measured.value[i]
    return p !== null && p !== undefined && m !== null && m !== undefined ? [{ t: iso, v: p - m }] : []
  }),
)

const meanError = computed<number | null>(() => {
  const points = deviationPoints.value
  if (!points.length) return null
  const sum = points.reduce((acc, p) => acc + Math.abs(p.v ?? 0), 0)
  return sum / points.length
})

const predictedSummary = computed(() =>
  summarise(
    times.value.flatMap((iso, i) => {
      const v = predicted.value[i]
      return v === null || v === undefined ? [] : [{ t: iso, v }]
    }),
  ),
)

const deviationByHour = computed(() => meanByHour(deviationPoints.value, timeZone.value))

/** El signo es la mitad de la informacion: sobra o falta gente respecto a lo previsto. */
function signed(value: number | null): string {
  if (value === null) return t('common.noValue')
  const text = formatNumber(value, 0)
  return value > 0 ? `+${text}` : text
}

const rangeHint = computed(() => presetHint(preset.value))

/** Atributos de la gemela. La fiabilidad puede llegar como numero y entonces no esta entre los
 * atributos de texto: se anade a mano para que salga con su distintivo. */
const twinAttributes = computed<Measure[]>(() => {
  const p = twinProfile.value
  if (!p) return []
  const confidence = p.roles.confidence
  const rows = [...p.text]
  if (confidence && !rows.some((m) => m.id === confidence.id)) rows.unshift(confidence)
  return rows
})

const showNoTwin = computed(() => twinResolved.value && !twinLoading.value && !twinError.value && !twin.value)
const showNoValue = computed(
  () =>
    twinResolved.value && !twinLoading.value && !!twin.value && !twinProfile.value?.roles.predicted,
)

const chartLoading = computed(() => seriesLoading.value || twinLoading.value)
const chartError = computed(() => seriesError.value ?? twinError.value)

async function reloadPrediction() {
  await loadTwin()
  await loadSeries()
}
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

      <LidarNotice
        v-if="showNoTwin"
        :text="t('dashboards.lidar.prediction.noTwin')"
        :hint="t('dashboards.lidar.prediction.noTwinHint')"
        icon="mdi-crystal-ball"
      />
      <LidarNotice
        v-else-if="showNoValue"
        type="warning"
        :text="t('dashboards.lidar.prediction.noValue')"
        icon="mdi-crystal-ball"
      />

      <div class="d-flex flex-wrap ga-4 mb-6">
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.prediction.tileNow')"
          :value="predictedNow === null ? t('common.noValue') : formatNumber(predictedNow, 0)"
          :unit="predictedNow === null ? undefined : t('dashboards.lidar.people')"
          icon="mdi-crystal-ball"
          :hint="rangeHint"
          color="secondary"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.prediction.tileMeasured')"
          :value="profile?.current === null || profile?.current === undefined ? t('common.noValue') : formatNumber(profile.current, 0)"
          :unit="t('dashboards.lidar.people')"
          icon="mdi-account-group-outline"
          :hint="profile?.updatedAt ? t('dashboards.lidar.tile.updated', { when: relativeFromNow(profile.updatedAt, timeZone) }) : t('dashboards.lidar.tile.noReading')"
          color="primary"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.prediction.tileDeviation')"
          :value="signed(deviation)"
          :unit="deviation === null ? undefined : t('dashboards.lidar.people')"
          icon="mdi-arrow-expand-vertical"
          :hint="t('dashboards.lidar.prediction.tileDeviationHint')"
          color="primary"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.prediction.tileError')"
          :value="formatNumber(meanError, 0)"
          :unit="meanError === null ? undefined : t('dashboards.lidar.people')"
          icon="mdi-target-variant"
          :hint="t('dashboards.lidar.prediction.tileErrorHint')"
          color="warning"
        />
        <StatTile
          style="flex: 1 1 200px"
          :label="t('dashboards.lidar.prediction.tileNextPeak')"
          :value="formatNumber(predictedSummary.max, 0)"
          :unit="predictedSummary.max === null ? undefined : t('dashboards.lidar.people')"
          icon="mdi-chart-bell-curve"
          :hint="predictedSummary.maxAt ? t('dashboards.lidar.tile.peakAt', { when: formatDateTime(predictedSummary.maxAt, timeZone) }) : undefined"
          color="warning"
        />
      </div>

      <VRow class="mb-2">
        <VCol cols="12">
          <ChartCard
            :title="t('dashboards.lidar.prediction.chart')"
            :subtitle="t('dashboards.lidar.prediction.chartHint', { when: formatDateTime(chartRange.end, timeZone) })"
            :loading="chartLoading"
            :error="chartError"
            :empty="!times.length"
            :min-height="360"
            @retry="reloadPrediction"
          >
            <PredictionBandChart
              :times="times"
              :measured="measured"
              :predicted="predicted"
              :lower="bandLower"
              :upper="bandUpper"
              :now-index="nowIndex"
              :units="t('dashboards.lidar.people')"
            />
            <div class="text-caption text-medium-emphasis mt-3">
              {{ hasBand ? t('dashboards.lidar.prediction.band') : t('dashboards.lidar.prediction.noBand') }}
            </div>
          </ChartCard>
        </VCol>
      </VRow>

      <VRow>
        <VCol cols="12" md="7">
          <ChartCard
            :title="t('dashboards.lidar.prediction.byHour')"
            :loading="chartLoading"
            :error="chartError"
            :empty="!deviationPoints.length"
            @retry="reloadPrediction"
          >
            <BarChart
              :series="[{ name: t('dashboards.lidar.prediction.byHourSeries'), units: t('dashboards.lidar.people'), points: deviationByHour.map((b) => ({ t: b.label, v: b.value })) }]"
              :height="280"
            />
          </ChartCard>
        </VCol>
        <VCol cols="12" md="5">
          <AttributesCard
            :title="t('dashboards.lidar.prediction.attributes')"
            :attributes="twinAttributes"
            :confidence-id="twinProfile?.roles.confidence?.id ?? null"
            :time-zone="timeZone"
            :loading="twinLoading"
            :error="twinError"
            @retry="reloadPrediction"
          />
        </VCol>
      </VRow>
    </StateBlock>
  </div>
</template>
