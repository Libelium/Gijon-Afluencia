<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import ChartCard from '../shared/ChartCard.vue'
import MatrixHeatmap from '../shared/MatrixHeatmap.vue'
import StatStrip from '../shared/StatStrip.vue'
import TemplateShell from '../shared/TemplateShell.vue'
import type { MatrixCell, TemplateDashboard } from '../shared/types'
import FlowSankeyChart, { type FlowLink } from './FlowSankeyChart.vue'
import TransitsPanels from './TransitsPanels.vue'
import { useTransits } from './useTransits'
import type { FlowNode } from './pairs'

/**
 * Una matriz de 12x12 son 144 celdas, el limite a partir del cual los rotulos de las columnas
 * dejan de caber. Se recortan los puntos de menor volumen porque son los que menos explican, y
 * se dice en el pie del panel que se ha hecho.
 */
const MAX_MATRIX_NODES = 12

/** Mas de dos docenas de tramos convierten el diagrama en una mancha. */
const MAX_SANKEY_LINKS = 24

const props = defineProps<{ dashboard: TemplateDashboard }>()

const tx = useTransits(props.dashboard)

/** Volumen total que entra y sale de cada extremo: es el criterio con el que se recorta la matriz. */
const nodeVolume = computed(() => {
  const totals = new Map<string, number>()
  for (const route of tx.measured.value) {
    const value = route.total ?? 0
    totals.set(route.pair.origin.id, (totals.get(route.pair.origin.id) ?? 0) + value)
    totals.set(route.pair.target.id, (totals.get(route.pair.target.id) ?? 0) + value)
  }
  return totals
})

const matrixNodes = computed<FlowNode[]>(() =>
  [...tx.nodes.value]
    .sort((a, b) => (nodeVolume.value.get(b.id) ?? 0) - (nodeVolume.value.get(a.id) ?? 0))
    .slice(0, MAX_MATRIX_NODES),
)

const matrixLabels = computed(() => matrixNodes.value.map((node) => node.label))

const matrixCells = computed<MatrixCell[]>(() => {
  const byKey = new Map(tx.measured.value.map((route) => [route.pair.key, route.total]))
  const cells: MatrixCell[] = []
  matrixNodes.value.forEach((origin, y) => {
    matrixNodes.value.forEach((target, x) => {
      // La diagonal no es un recorrido: un punto no transita hacia si mismo.
      if (origin.id === target.id) {
        cells.push({ x, y, value: null })
        return
      }
      cells.push({ x, y, value: byKey.get(`${origin.id}>${target.id}`) ?? null })
    })
  })
  return cells
})

const matrixEmpty = computed(() => matrixCells.value.every((cell) => cell.value === null))

const matrixHeight = computed(() => Math.max(260, 34 * matrixNodes.value.length + 120))

const matrixFootnote = computed(() =>
  tx.nodes.value.length > matrixNodes.value.length
    ? t('templates.transits.matrixLimited', {
        shown: matrixNodes.value.length,
        total: tx.nodes.value.length,
      })
    : undefined,
)

/**
 * Cada punto aparece dos veces en el diagrama, una como origen y otra como destino: sin separarlos
 * un recorrido de ida y vuelta cerraria un ciclo y el diagrama no se puede dibujar. Los rotulos se
 * desempatan con el identificador porque dos puntos distintos pueden llamarse igual.
 */
function sideNames(nodes: FlowNode[], suffix: string): Map<string, string> {
  const used = new Set<string>()
  const names = new Map<string, string>()
  for (const node of nodes) {
    // Un mismo extremo aparece en varios recorridos: su nombre se fija en la primera vuelta.
    if (names.has(node.id)) continue
    const plain = `${node.label} ${suffix}`
    const name = used.has(plain) ? `${node.label} · ${node.id} ${suffix}` : plain
    used.add(name)
    names.set(node.id, name)
  }
  return names
}

const sankeyLinks = computed<FlowLink[]>(() => {
  const routes = tx.ranked.value.slice(0, MAX_SANKEY_LINKS)
  const origins = sideNames(
    routes.map((route) => route.pair.origin),
    t('templates.transits.originSuffix'),
  )
  const targets = sideNames(
    routes.map((route) => route.pair.target),
    t('templates.transits.targetSuffix'),
  )
  return routes.map((route) => ({
    source: origins.get(route.pair.origin.id) ?? route.pair.origin.label,
    target: targets.get(route.pair.target.id) ?? route.pair.target.label,
    value: route.total ?? 0,
  }))
})

const sankeyHeight = computed(() => {
  const sides = [
    new Set(sankeyLinks.value.map((link) => link.source)).size,
    new Set(sankeyLinks.value.map((link) => link.target)).size,
  ]
  return Math.max(320, 30 * Math.max(...sides, 1) + 80)
})
</script>

<template>
  <TemplateShell
    v-model:preset="tx.data.preset.value"
    :loading="tx.data.loading.value || tx.busy.value"
    :error="tx.data.error.value || tx.seriesError.value"
    :range-caption="tx.data.rangeCaption.value"
    :empty="!!tx.emptyState.value"
    :empty-text="tx.emptyState.value?.text"
    :empty-hint="tx.emptyState.value?.hint"
    :empty-icon="tx.emptyState.value?.icon"
    :failed="tx.data.failed.value"
    :notice="tx.notice.value"
    @refresh="tx.refresh"
    @retry="tx.refresh"
  >
    <template #controls>
      <VSelect
        v-model="tx.measure.value"
        :items="tx.measureItems.value"
        :label="t('templates.transits.measureLabel')"
        min-width="240"
        max-width="380"
      />
      <VChip variant="tonal" size="small" prepend-icon="mdi-vector-polyline">
        {{ tx.modeLabel.value }}
      </VChip>
    </template>

    <StatStrip :items="tx.stats.value" />

    <TransitsPanels
      :nodes="tx.nodes.value"
      :routes="tx.ranked.value"
      :total-series="tx.totalSeries.value"
    />

    <VRow class="mt-0">
      <VCol cols="12" lg="6">
        <ChartCard
          :title="t('templates.transits.matrixTitle')"
          :subtitle="t('templates.transits.matrixSubtitle')"
          :empty="matrixEmpty"
          :footnote="matrixFootnote"
        >
          <MatrixHeatmap
            :x-labels="matrixLabels"
            :y-labels="matrixLabels"
            :cells="matrixCells"
            :height="matrixHeight"
            :x-label-rotate="40"
            :x-label-interval="0"
            :value-label="t('templates.transits.volume')"
          />
        </ChartCard>
      </VCol>

      <VCol cols="12" lg="6">
        <ChartCard
          :title="t('templates.transits.sankeyTitle')"
          :subtitle="t('templates.transits.sankeySubtitle')"
          :empty="sankeyLinks.length === 0"
          :footnote="t('templates.transits.sankeyFootnote')"
        >
          <FlowSankeyChart :links="sankeyLinks" :height="sankeyHeight" />
        </ChartCard>
      </VCol>
    </VRow>
  </TemplateShell>
</template>
