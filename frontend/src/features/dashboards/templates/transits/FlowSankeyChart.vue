<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { SankeyChart } from 'echarts/charts'
import { AriaComponent, TooltipComponent } from 'echarts/components'
// Los tipos salen del paquete raiz, no de 'echarts/charts': son declaraciones distintas
// y mezclarlas hace incompatible el objeto de opciones. La importacion es solo de tipos.
import type {
  EChartsOption,
  SankeySeriesOption,
  TooltipComponentFormatterCallbackParams,
} from 'echarts'
import { t } from '@/i18n'
import { formatMeasure } from '@/lib/format'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { INK, seriesColors } from '../../palette'
import { useChartTheme } from '../../charts/useChartTheme'
import { asItems, chartStyle, tooltipHeader, tooltipRow } from '../../charts/chartOptions'
import { useChartLabel } from '../../charts/chartLabel'
import { ariaOption, rowsTable } from '../../charts/a11y'

// Ver LineChart.vue: `AriaComponent` da nombre accesible al lienzo (WCAG 1.1.1, ACC-002).
use([CanvasRenderer, SankeyChart, TooltipComponent, AriaComponent])

/** Un tramo del diagrama. `source` y `target` son ya los rotulos visibles de cada extremo. */
export interface FlowLink {
  source: string
  target: string
  value: number
}

const props = withDefaults(
  defineProps<{
    links: FlowLink[]
    units?: string
    height?: number
    /** Rotulo del diagrama. Da nombre al lienzo y encabeza la tabla equivalente. */
    title?: string
  }>(),
  { height: 400 },
)

const { themeName, isDark } = useChartTheme()

const label = useChartLabel(() => props.title, () => t('templates.transits.flowLabel'))

const option = computed<EChartsOption>(() => {
  const colors = seriesColors(isDark.value)
  const ink = isDark.value ? INK.dark : INK.light

  // Los origenes se declaran antes que los destinos para que la columna izquierda sea la de
  // origen: el diagrama no ordena los nodos, respeta el orden en que llegan.
  const names: string[] = []
  for (const link of props.links) if (!names.includes(link.source)) names.push(link.source)
  for (const link of props.links) if (!names.includes(link.target)) names.push(link.target)

  const series: SankeySeriesOption = {
    type: 'sankey',
    // El rotulo de un nodo se dibuja a su derecha, tambien en la ultima columna: ese margen
    // es el hueco que necesita para no salirse del lienzo.
    left: 12,
    right: 150,
    top: 12,
    bottom: 12,
    nodeAlign: 'justify',
    nodeGap: 10,
    nodeWidth: 12,
    emphasis: { focus: 'adjacency' },
    label: { color: ink, fontSize: 11, width: 130, overflow: 'truncate' },
    lineStyle: { color: 'gradient', opacity: 0.35, curveness: 0.5 },
    data: names.map((name, index) => ({
      name,
      itemStyle: { color: colors[index % colors.length] },
    })),
    links: props.links.map((link) => ({ ...link })),
  }

  return {
    animationDuration: 300,
    aria: ariaOption(label.value),
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const item = asItems(params)[0]
        const head = String(item.name ?? '')
        const value = Number(item.value)
        // Los nodos del diagrama no traen valor propio; solo los tramos lo tienen.
        if (!Number.isFinite(value)) return tooltipHeader(head)
        return [
          tooltipHeader(head),
          tooltipRow(item.marker, t('templates.transits.volume'), formatMeasure(value, props.units)),
        ].join('')
      },
    },
    series: [series],
  }
})

const style = computed(() => chartStyle(props.height))

/**
 * El diagrama de flujos no tiene series temporales: su dato es «de donde a donde, cuanto». La
 * tabla equivalente es exactamente esa terna, que ademas es la unica forma de leer un tramo
 * fino sin apuntar con el raton.
 */
const table = computed(() =>
  rowsTable(
    [t('templates.transits.origin'), t('templates.transits.destination'), t('templates.transits.volume')],
    props.links.map((link) => [link.source, link.target, formatMeasure(link.value, props.units)]),
  ),
)
</script>

<template>
  <div>
    <VChart :option="option" :theme="themeName" :style="style" autoresize />
    <DataTableAlternative :title="label" :table="table" />
  </div>
</template>
