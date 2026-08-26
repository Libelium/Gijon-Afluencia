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
import { t } from '@/i18n'
import { formatMeasure } from '@/lib/format'
import { useChartTheme } from '../../charts/useChartTheme'
import { asItems, axisValue, timeFormatOf, timeLabel, toMillis, tooltipHeader, tooltipRow } from '../../charts/chartOptions'
import type { NamedSeries } from '../shared/types'

use([CanvasRenderer, LineSeries, GridComponent, TooltipComponent, LegendComponent])

const props = withDefaults(
  defineProps<{
    series: NamedSeries[]
    units?: string
    height?: number
  }>(),
  { height: 320 },
)

const { compact, themeName, timeZone } = useChartTheme()

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
    grid: { left: 8, right: 20, top: 20, bottom: 34, containLabel: true },
    legend: { show: true, type: 'scroll', bottom: 0 },
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
    yAxis: { type: 'value', splitNumber: 5, axisLabel: { formatter: (v: number) => axisValue(v) } },
    series: data,
  }
})

const style = computed(() => ({ height: `${props.height}px`, width: '100%' }))
</script>

<template>
  <VChart :option="option" :theme="themeName" :style="style" autoresize />
</template>
