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
import { formatMeasure } from '@/lib/format'
import { t } from '@/i18n'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { useChartTheme } from './useChartTheme'
import {
  asItems,
  chartGrid,
  chartStyle,
  dashFor,
  nonNull,
  scrollLegend,
  stepOf,
  timeFormatOf,
  timeLabel,
  toMillis,
  tooltipHeader,
  tooltipRow,
  valueAxis,
} from './chartOptions'
import { useChartLabel } from './chartLabel'
import { ariaOption, seriesTable } from './a11y'
import type { ChartSeries } from './types'

// `AriaComponent` es lo que hace que ECharts ponga `role="img"` y un nombre accesible en el
// contenedor del lienzo. Sin el, el `<canvas>` no tiene nombre (WCAG 1.1.1, ACC-002).
use([CanvasRenderer, LineSeries, GridComponent, TooltipComponent, LegendComponent, AriaComponent])

const props = withDefaults(
  defineProps<{
    series: ChartSeries[]
    units?: string
    area?: boolean
    height?: number | string
    /** Rotulo de la grafica. Da nombre al lienzo y encabeza la tabla equivalente. */
    title?: string
  }>(),
  { area: false, height: 280 },
)

const { themeName, compact, timeZone } = useChartTheme()

const showLegend = computed(() => props.series.length > 1)

const label = useChartLabel(() => props.title, () => t('dashboards.chart.line'))

const unitsOf = (name?: string) =>
  props.series.find((s) => s.name === name)?.units ?? props.units

const option = computed<EChartsOption>(() => {
  const format = timeFormatOf(props.series, compact.value)
  const step = stepOf(props.series)
  const zone = timeZone.value

  const data: LineSeriesOption[] = props.series.map((serie, index) => ({
    name: serie.name,
    type: 'line',
    // Con dos puntos o menos la linea no se ve: hay que marcar el dato con su simbolo.
    showSymbol: nonNull(serie.points).length <= 2,
    symbolSize: 6,
    sampling: 'lttb',
    connectNulls: false,
    smooth: props.area ? 0.2 : false,
    lineStyle: { width: 2, type: dashFor(index, props.series.length) },
    areaStyle: props.area ? { opacity: 0.12 } : undefined,
    emphasis: { focus: 'series' },
    data: serie.points.map((point) => [toMillis(point.t), point.v]),
  }))

  return {
    animationDuration: 300,
    aria: ariaOption(label.value),
    grid: chartGrid(showLegend.value ? 34 : 8),
    legend: scrollLegend(showLegend.value),
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const items = asItems(params)
        if (!items.length) return ''
        const head = timeLabel(Number(items[0].axisValue), zone, 'dd/MM/yyyy HH:mm')
        const rows = items.map((item) => {
          const raw = Array.isArray(item.value) ? item.value[1] : item.value
          return tooltipRow(
            item.marker,
            item.seriesName ?? '',
            formatMeasure(raw, unitsOf(item.seriesName)),
          )
        })
        return [tooltipHeader(head), ...rows].join('')
      },
    },
    xAxis: {
      type: 'time',
      splitNumber: compact.value ? 3 : 6,
      // El eje reparte sus marcas al margen de los datos: sin este suelo coloca varias dentro
      // del mismo dia y con lecturas diarias todas ellas se rotulan igual.
      minInterval: step || undefined,
      axisLabel: {
        hideOverlap: true,
        formatter: (value: number) => timeLabel(value, zone, format),
      },
    },
    yAxis: valueAxis(compact.value),
    series: data,
  }
})

const style = computed(() => chartStyle(props.height))

// La misma serie que dibuja el lienzo, en tabla: es la alternativa textual, no un resumen.
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
