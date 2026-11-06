<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import { brandRamp } from '@/customization/palette'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import { LineChart, type ChartPoint, type ChartSeries } from '../../charts'
import { levelRatio } from '../shared/aggregate'
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

const theme = useTheme()

/**
 * Los recorridos y sus extremos se pintan con el color de marca de la organizacion, en una escala
 * de menos a mas volumen. Sigue a la personalizacion y al tema claro u oscuro sin recargar.
 */
const ramp = computed(() => {
  const { colors, dark } = theme.current.value
  return brandRamp(colors.primary, colors.surface, dark)
})
const rampColor = (ratio: number) =>
  ramp.value[Math.round(Math.min(1, Math.max(0, Number.isFinite(ratio) ? ratio : 0)) * (ramp.value.length - 1))]

/**
 * Punto cuyos recorridos se miran, o null para verlos todos. Se elige en el selector o pulsando
 * el punto en el mapa; el selector es la via con teclado.
 */
const selected = ref<string | null>(null)

// Si cambia lo asignado al panel y el punto ya no esta, se vuelve a ver todo.
watch(
  () => props.nodes,
  (nodes) => {
    if (selected.value && !nodes.some((node) => node.id === selected.value)) selected.value = null
  },
)

const selectedNode = computed(() => props.nodes.find((node) => node.id === selected.value) ?? null)

/** Solo se ofrecen los puntos con algun recorrido con volumen: los demas no tendrian nada que ver. */
const nodeItems = computed(() => [
  { title: t('templates.transits.allNodes'), value: null as string | null },
  ...props.nodes
    .filter((node) => props.routes.some((route) => route.pair.origin.id === node.id || route.pair.target.id === node.id))
    .map((node) => ({ title: node.label, value: node.id as string | null })),
])

function toggle(key: string) {
  selected.value = selected.value === key ? null : key
}

/** Los recorridos que se dibujan: todos, o los que salen o llegan al punto elegido. */
const shownRoutes = computed(() =>
  selected.value
    ? props.routes.filter((route) => route.pair.origin.id === selected.value || route.pair.target.id === selected.value)
    : props.routes,
)

const legend = computed(() =>
  ramp.value.map((color, index) => ({ color, label: t(LEVEL_KEYS[index]) })),
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
        color: rampColor(ratio),
        radius: 6 + Math.round(16 * ratio),
      }
    }),
)

const mapLinks = computed<MapLink[]>(() =>
  shownRoutes.value
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
        // Por debajo de 2 px un trazo discontinuo apenas se ve sobre las teselas.
        weight: 2 + Math.round(6 * ratio),
        color: rampColor(ratio),
        curved: true,
      }
    }),
)

/** Recorridos con volumen que el mapa no puede dibujar porque les falta un extremo ubicado. */
const withoutLocation = computed(() => shownRoutes.value.length - mapLinks.value.length)

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

interface NodeRow {
  key: string
  /** El otro extremo del recorrido. */
  other: string
  total: number | null
  share: number | null
}

/** Recorridos del punto elegido en un sentido, con su parte de todo lo que sale o llega. */
function nodeRows(side: 'origin' | 'target'): NodeRow[] {
  const id = selected.value
  if (!id) return []
  const routes = props.routes.filter((route) => route.pair[side].id === id)
  const total = routes.reduce((sum, route) => sum + (route.total ?? 0), 0)
  return routes.slice(0, MAX_RANK).map((route) => ({
    key: route.pair.key,
    other: side === 'origin' ? route.pair.target.label : route.pair.origin.label,
    total: route.total,
    share: total > 0 && route.total !== null ? (route.total / total) * 100 : null,
  }))
}

const outgoing = computed(() => nodeRows('origin'))
const incoming = computed(() => nodeRows('target'))

const nodeLists = computed(() => [
  {
    key: 'out',
    title: t('templates.transits.outgoingTitle'),
    other: t('templates.transits.colTarget'),
    share: t('templates.transits.colShareOut'),
    rows: outgoing.value,
  },
  {
    key: 'in',
    title: t('templates.transits.incomingTitle'),
    other: t('templates.transits.colOrigin'),
    share: t('templates.transits.colShareIn'),
    rows: incoming.value,
  },
])

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
        <VSelect
          v-model="selected"
          :items="nodeItems"
          :label="t('templates.transits.nodeLabel')"
          density="compact"
          hide-details
          class="mb-3"
          max-width="360"
        />
        <PointMap
          :points="mapPoints"
          :links="mapLinks"
          :height="380"
          :legend="legend"
          :selected="selected"
          @select="toggle"
        />
      </ChartCard>
    </VCol>

    <VCol v-if="selectedNode" cols="12" md="5">
      <ChartCard
        :title="t('templates.transits.nodeTitle', { name: selectedNode.label })"
        :subtitle="t('templates.transits.nodeSubtitle')"
        :empty="outgoing.length === 0 && incoming.length === 0"
      >
        <template v-for="list in nodeLists" :key="list.key">
          <div class="text-body-2 font-weight-medium mt-2 mb-1">{{ list.title }}</div>
          <VTable v-if="list.rows.length" density="compact" class="text-body-2 mb-3">
            <thead>
              <tr>
                <th>{{ list.other }}</th>
                <th class="text-end">{{ t('templates.transits.volume') }}</th>
                <th class="text-end">{{ list.share }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in list.rows" :key="row.key">
                <td>{{ row.other }}</td>
                <td class="text-end">{{ formatNumber(row.total) }}</td>
                <td class="text-end">{{ shareText(row.share) }}</td>
              </tr>
            </tbody>
          </VTable>
          <div v-else class="text-body-2 text-medium-emphasis mb-3">{{ t('templates.transits.noRoutes') }}</div>
        </template>
      </ChartCard>
    </VCol>

    <VCol v-else cols="12" md="5">
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
