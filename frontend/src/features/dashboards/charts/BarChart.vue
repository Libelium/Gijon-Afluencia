<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart as BarSeries } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
// Los tipos salen del paquete raiz, no de 'echarts/charts': son declaraciones distintas
// y mezclarlas hace incompatible el objeto de opciones. La importacion es solo de tipos.
import type {
  BarSeriesOption,
  EChartsOption,
  TooltipComponentFormatterCallbackParams,
} from 'echarts'
import { formatMeasure } from '@/lib/format'
import { useChartTheme } from './useChartTheme'
import {
  asItems,
  axisValue,
  categoryLabel,
  timeFormatOf,
  tooltipHeader,
  tooltipRow,
} from './chartOptions'
import type { ChartSeries } from './types'

use([CanvasRenderer, BarSeries, GridComponent, TooltipComponent, LegendComponent])

const props = withDefaults(
  defineProps<{
    series: ChartSeries[]
    units?: string
    stacked?: boolean
    height?: number | string
  }>(),
  { stacked: false, height: 280 },
)

const { themeName, compact, timeZone } = useChartTheme()

const showLegend = computed(() => props.series.length > 1)

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
    // Las etiquetas giradas ocupan mas alto que la fuente, y la leyenda va debajo de ellas.
    grid: {
      left: 8,
      right: 20,
      top: 20,
      bottom: (showLegend.value ? 34 : 8) + (rotate.value ? 18 : 0),
      containLabel: true,
    },
    legend: { show: showLegend.value, type: 'scroll', bottom: 0 },
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
    yAxis: {
      type: 'value',
      splitNumber: compact.value ? 3 : 5,
      axisLabel: { formatter: (value: number) => axisValue(value) },
    },
    series: data,
  }
})

const style = computed(() => ({
  height: typeof props.height === 'number' ? `${props.height}px` : props.height,
  width: '100%',
}))
</script>

<template>
  <VChart :option="option" :theme="themeName" :style="style" autoresize />
</template>
