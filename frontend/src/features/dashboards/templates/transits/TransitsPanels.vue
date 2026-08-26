<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import { LineChart, type ChartPoint, type ChartSeries } from '../../charts'
import { useChartTheme } from '../../charts/useChartTheme'
import { levelRatio } from '../shared/aggregate'
import { occupancyColor, occupancyColors } from '../../palette'
import ChartCard from '../shared/ChartCard.vue'
import PointMap, { type MapLink, type MapPoint } from '../shared/PointMap.vue'
import type { FlowNode } from './pairs'
import type { Route } from './useTransits'

/** Los paneles que comparten la plantilla sencilla y la avanzada. */

/** Lo que dice el rotulo del panel: diez en el ranking, cinco en la evolucion. */
const MAX_RANK = 10
const MAX_TREND = 5

const LEVEL_KEYS = [
  'templates.common.levelVeryLow',
  'templates.common.levelLow',
  'templates.common.levelMedium',
  'templates.common.levelHigh',
  'templates.common.levelVeryHigh',
]

const props = defineProps<{
  nodes: FlowNode[]
  /** Recorridos con volumen, de mayor a menor. */
  routes: Route[]
  totalSeries: ChartPoint[]
}>()

const { isDark } = useChartTheme()

const legend = computed(() =>
  occupancyColors(isDark.value).map((color, index) => ({ color, label: t(LEVEL_KEYS[index]) })),
)

interface NodeLoad {
  volume: number
  routes: number
}

/** Volumen y numero de recorridos que pasan por cada extremo, para el tamano de su circulo. */
const nodeLoad = computed(() => {
  const load = new Map<string, NodeLoad>()
  const add = (id: string, volume: number) => {
    const current = load.get(id) ?? { volume: 0, routes: 0 }
    load.set(id, { volume: current.volume + volume, routes: current.routes + 1 })
  }
  for (const route of props.routes) {
    add(route.pair.origin.id, route.total ?? 0)
    add(route.pair.target.id, route.total ?? 0)
  }
  return load
})

const maxNodeVolume = computed(() =>
  Math.max(0, ...[...nodeLoad.value.values()].map((load) => load.volume)),
)

const maxRouteVolume = computed(() => Math.max(0, ...props.routes.map((route) => route.total ?? 0)))

const mapPoints = computed<MapPoint[]>(() =>
  props.nodes
    .filter((node) => node.lat !== null && node.lon !== null)
    .map((node) => {
      const load = nodeLoad.value.get(node.id)
      const ratio = levelRatio(load?.volume ?? null, maxNodeVolume.value)
      return {
        key: node.id,
        lat: node.lat as number,
        lon: node.lon as number,
        label: node.label,
        text: t('templates.transits.pointText', { count: load?.routes ?? 0 }),
        color: occupancyColor(ratio, isDark.value),
        radius: 6 + Math.round(16 * ratio),
      }
    }),
)

const mapLinks = computed<MapLink[]>(() =>
  props.routes
    .filter(
      (route) =>
        route.pair.origin.lat !== null &&
        route.pair.origin.lon !== null &&
        route.pair.target.lat !== null &&
        route.pair.target.lon !== null,
    )
    .map((route) => {
      const ratio = levelRatio(route.total, maxRouteVolume.value)
      return {
        key: route.pair.key,
        from: [route.pair.origin.lat as number, route.pair.origin.lon as number],
        to: [route.pair.target.lat as number, route.pair.target.lon as number],
        label: route.pair.label,
        text: formatNumber(route.total),
        weight: 1 + Math.round(7 * ratio),
        color: occupancyColor(ratio, isDark.value),
      }
    }),
)

/** Recorridos con volumen que el mapa no puede dibujar porque les falta un extremo ubicado. */
const withoutLocation = computed(() => props.routes.length - mapLinks.value.length)

interface RankRow {
  key: string
  origin: string
  target: string
  total: number | null
  share: number | null
}

const headers = [
  { title: t('templates.transits.colOrigin'), key: 'origin', align: 'start' as const, sortable: true },
  { title: t('templates.transits.colTarget'), key: 'target', align: 'start' as const, sortable: true },
  { title: t('templates.transits.volume'), key: 'total', align: 'end' as const, sortable: true },
  { title: t('templates.transits.colShare'), key: 'share', align: 'end' as const, sortable: true },
]

const rankTotal = computed(() =>
  props.routes.reduce((sum, route) => sum + (route.total ?? 0), 0),
)

const rankRows = computed<RankRow[]>(() =>
  props.routes.slice(0, MAX_RANK).map((route) => ({
    key: route.pair.key,
    origin: route.pair.origin.label,
    target: route.pair.target.label,
    total: route.total,
    share:
      rankTotal.value > 0 && route.total !== null ? (route.total / rankTotal.value) * 100 : null,
  })),
)

function shareText(share: number | null): string {
  return share === null ? t('common.noValue') : `${formatNumber(share, 1)} %`
}

const trendSeries = computed<ChartSeries[]>(() => [
  ...props.routes.slice(0, MAX_TREND).map((route) => ({
    name: route.pair.label,
    points: route.points,
  })),
  { name: t('dashboards.chart.total'), points: props.totalSeries },
])

const trendEmpty = computed(() => props.routes.length === 0)
</script>

<template>
  <VRow>
    <VCol cols="12" md="7">
      <ChartCard
        :title="t('templates.transits.mapTitle')"
        :subtitle="t('templates.transits.mapSubtitle')"
        :empty="mapLinks.length === 0"
        :empty-text="t('templates.transits.emptyMap')"
        empty-icon="mdi-map-marker-off-outline"
        :footnote="
          withoutLocation > 0
            ? t('templates.transits.mapWithoutLocation', { count: withoutLocation })
            : undefined
        "
      >
        <PointMap :points="mapPoints" :links="mapLinks" :height="380" :legend="legend" />
      </ChartCard>
    </VCol>

    <VCol cols="12" md="5">
      <ChartCard :title="t('templates.transits.rankTitle')" :empty="rankRows.length === 0">
        <div class="overflow-x-auto">
          <VDataTable
            :headers="headers"
            :items="rankRows"
            :items-per-page="-1"
            hide-default-footer
            item-value="key"
            class="text-body-2"
          >
            <template #[`item.total`]="{ item }">{{ formatNumber(item.total) }}</template>
            <template #[`item.share`]="{ item }">{{ shareText(item.share) }}</template>
          </VDataTable>
        </div>
      </ChartCard>
    </VCol>
  </VRow>

  <VRow class="mt-0">
    <VCol cols="12">
      <ChartCard
        :title="t('templates.transits.trendTitle')"
        :subtitle="t('templates.transits.trendSubtitle')"
        :empty="trendEmpty"
      >
        <LineChart :series="trendSeries" :height="320" />
      </ChartCard>
    </VCol>
  </VRow>
</template>
