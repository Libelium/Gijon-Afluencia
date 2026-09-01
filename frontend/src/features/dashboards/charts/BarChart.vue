<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart as BarSeries } from 'echarts/charts'
import { AriaComponent, GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
// Los tipos salen del paquete raiz, no de 'echarts/charts': son declaraciones distintas
// y mezclarlas hace incompatible el objeto de opciones. La importacion es solo de tipos.
import type {
  BarSeriesOption,
  EChartsOption,
  TooltipComponentFormatterCallbackParams,
} from 'echarts'
import { formatMeasure } from '@/lib/format'
import { t } from '@/i18n'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { useChartTheme } from './useChartTheme'
import {
  asItems,
  categoryLabel,
  chartGrid,
  chartStyle,
  scrollLegend,
  timeFormatOf,
  tooltipHeader,
  tooltipRow,
  valueAxis,
} from './chartOptions'
import { useChartLabel } from './chartLabel'
import { ariaOption, seriesTable } from './a11y'
import type { ChartSeries } from './types'

// Ver LineChart.vue: `AriaComponent` da nombre accesible al lienzo (WCAG 1.1.1, ACC-002).
use([CanvasRenderer, BarSeries, GridComponent, TooltipComponent, LegendComponent, AriaComponent])

const props = withDefaults(
  defineProps<{
    series: ChartSeries[]
    units?: string
    stacked?: boolean
    height?: number | string
    /** Rotulo de la grafica. Da nombre al lienzo y encabeza la tabla equivalente. */
    title?: string
  }>(),
  { stacked: false, height: 280 },
)

const { themeName, compact, timeZone } = useChartTheme()

const showLegend = computed(() => props.series.length > 1)

const label = useChartLabel(() => props.title, () => t('dashboards.chart.bar'))

/** Las series pueden no compartir todas las categorias: se unifican conservando el orden de llegada. */
const categories = computed(() => {
  const seen: string[] = []
  for (const serie of props.series) {
    for (const point of serie.points) if (!seen.includes(point.t)) seen.push(point.t)
  }
  return seen
})

const rotate = computed(() => (categories.value.length > (compact.value ? 5 : 12) ? 40 : 0))

const unitsOf = (name?: string) =>
  props.series.find((s) => s.name === name)?.units ?? props.units

const option = computed<EChartsOption>(() => {
  const format = timeFormatOf(props.series, compact.value)
  const zone = timeZone.value
  const labels = categories.value.map((raw) => categoryLabel(raw, zone, format))

  const data: BarSeriesOption[] = props.series.map((serie) => {
    const byTime = new Map(serie.points.map((point) => [point.t, point.v]))
    return {
      name: serie.name,
      type: 'bar',
      stack: props.stacked ? 'total' : undefined,
      barMaxWidth: 28,
      emphasis: { focus: 'series' },
      data: categories.value.map((raw) => byTime.get(raw) ?? null),
    }
  })

  return {
    animationDuration: 300,
    aria: ariaOption(label.value),
    // Las etiquetas giradas ocupan mas alto que la fuente, y la leyenda va debajo de ellas.
    grid: chartGrid((showLegend.value ? 34 : 8) + (rotate.value ? 18 : 0)),
    legend: scrollLegend(showLegend.value),
    tooltip: {
      trigger: 'axis',
      confine: true,
      axisPointer: { type: 'shadow' },
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const items = asItems(params)
        if (!items.length) return ''
        const head = String(items[0].axisValue ?? '')
        const rows = items.map((item) =>
          tooltipRow(item.marker, item.seriesName ?? '', formatMeasure(item.value, unitsOf(item.seriesName))),
        )
        return [tooltipHeader(head), ...rows].join('')
      },
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        hideOverlap: rotate.value === 0,
        rotate: rotate.value,
        interval: rotate.value ? 'auto' : 0,
      },
    },
    yAxis: valueAxis(compact.value),
    series: data,
  }
})

const style = computed(() => chartStyle(props.height))

const table = computed(() =>
  seriesTable(props.series, { timeZone: timeZone.value, units: props.units }),
)
</script>

<template>
  <div>
    <VChart :option="option" :theme="themeName" :style="style" autoresize />
    <DataTableAlternative :title="label" :table="table" />
  </div>
</template>
