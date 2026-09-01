<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart as LineSeries } from 'echarts/charts'
import { AriaComponent, GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
// Los tipos salen del paquete raiz, no de 'echarts/charts': son declaraciones distintas
// y mezclarlas hace incompatible el objeto de opciones. La importacion es solo de tipos.
import type {
  EChartsOption,
  LineSeriesOption,
  TooltipComponentFormatterCallbackParams,
} from 'echarts'
import { t } from '@/i18n'
import { formatMeasure } from '@/lib/format'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { useChartTheme } from '../../charts/useChartTheme'
import {
  asItems,
  chartGrid,
  chartStyle,
  scrollLegend,
  timeFormatOf,
  timeLabel,
  toMillis,
  tooltipHeader,
  tooltipRow,
  valueAxis,
} from '../../charts/chartOptions'
import { useChartLabel } from '../../charts/chartLabel'
import { ariaOption, seriesTable } from '../../charts/a11y'
import type { NamedSeries } from '../shared/types'

// Ver LineChart.vue: `AriaComponent` da nombre accesible al lienzo (WCAG 1.1.1, ACC-002).
use([CanvasRenderer, LineSeries, GridComponent, TooltipComponent, LegendComponent, AriaComponent])

const props = withDefaults(
  defineProps<{
    series: NamedSeries[]
    units?: string
    height?: number
    /** Rotulo de la grafica. Da nombre al lienzo y encabeza la tabla equivalente. */
    title?: string
  }>(),
  { height: 320 },
)

const { compact, themeName, timeZone } = useChartTheme()

const label = useChartLabel(() => props.title, () => t('dashboards.chart.stackedArea'))

const option = computed<EChartsOption>(() => {
  const format = timeFormatOf(props.series, compact.value)

  const data: LineSeriesOption[] = props.series.map((serie) => ({
    name: serie.name,
    type: 'line',
    stack: 'total',
    // Apilar con nulos rompe la pila: un cubo sin lectura de esa categoria aporta 0 al total.
    data: serie.points.map((p) => [toMillis(p.t), p.v ?? 0]),
    symbol: 'none',
    smooth: false,
    lineStyle: { width: 1 },
    areaStyle: { opacity: 0.5 },
    emphasis: { focus: 'series' },
  }))

  return {
    animationDuration: 300,
    aria: ariaOption(label.value),
    grid: chartGrid(34),
    legend: scrollLegend(true),
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const items = asItems(params)
        if (!items.length) return ''
        const head = timeLabel(Number(items[0].axisValue), timeZone.value, 'dd/MM/yyyy HH:mm')
        let total = 0
        const rows = items.map((item) => {
          const raw = Array.isArray(item.value) ? Number(item.value[1]) : Number(item.value)
          if (Number.isFinite(raw)) total += raw
          return tooltipRow(item.marker, item.seriesName ?? '', formatMeasure(raw, props.units))
        })
        return [
          tooltipHeader(head),
          ...rows,
          tooltipRow('', t('dashboards.chart.total'), formatMeasure(total, props.units)),
        ].join('')
      },
    },
    xAxis: {
      type: 'time',
      splitNumber: compact.value ? 3 : 6,
      axisLabel: { hideOverlap: true, formatter: (v: number) => timeLabel(v, timeZone.value, format) },
    },
    yAxis: valueAxis(false),
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
