<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart as LineSeries } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
// Los tipos salen del paquete raiz, no de 'echarts/charts': son declaraciones distintas
// y mezclarlas hace incompatible el objeto de opciones. La importacion es solo de tipos.
import type {
  EChartsOption,
  LineSeriesOption,
  TooltipComponentFormatterCallbackParams,
} from 'echarts'
import { formatMeasure } from '@/lib/format'
import { useChartTheme } from './useChartTheme'
import {
  asItems,
  axisValue,
  dashFor,
  nonNull,
  stepOf,
  timeFormatOf,
  timeLabel,
  toMillis,
  tooltipHeader,
  tooltipRow,
} from './chartOptions'
import type { ChartSeries } from './types'

use([CanvasRenderer, LineSeries, GridComponent, TooltipComponent, LegendComponent])

const props = withDefaults(
  defineProps<{
    series: ChartSeries[]
    units?: string
    area?: boolean
    height?: number | string
  }>(),
  { area: false, height: 280 },
)

const { themeName, compact, timeZone } = useChartTheme()

const showLegend = computed(() => props.series.length > 1)

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
    // Margenes holgados: la ultima etiqueta del eje temporal se sale por la derecha y las
    // cifras del eje de valores necesitan aire para no tocar el borde de la tarjeta.
    grid: {
      left: 8,
      right: 20,
      top: 20,
      bottom: showLegend.value ? 34 : 8,
      containLabel: true,
    },
    legend: { show: showLegend.value, type: 'scroll', bottom: 0 },
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
