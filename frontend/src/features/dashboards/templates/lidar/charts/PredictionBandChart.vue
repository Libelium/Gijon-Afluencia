<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart as LineSeries } from 'echarts/charts'
import { AriaComponent, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import type { EChartsOption, TooltipComponentFormatterCallbackParams } from 'echarts'
import { t } from '@/i18n'
import { formatMeasure, formatNumber } from '@/lib/format'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { useChartTheme } from '../../../charts'
import {
  asItems,
  chartGrid,
  chartStyle,
  scrollLegend,
  timeFormatFor,
  timeLabel,
  toMillis,
  tooltipHeader,
  tooltipRow,
  valueAxis,
  type TooltipItem,
} from '../../../charts/chartOptions'
import { useChartLabel } from '../../../charts/chartLabel'
import { ariaOption, rowsTable } from '../../../charts/a11y'
import { MUTED, seriesColors } from '../../../palette'

// Ver LineChart.vue: `AriaComponent` da nombre accesible al lienzo (WCAG 1.1.1, ACC-002).
use([
  CanvasRenderer,
  LineSeries,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  AriaComponent,
])

const props = withDefaults(
  defineProps<{
    /** Marcas ISO UTC, ascendentes. Rejilla comun de todas las series. */
    times: string[]
    measured: (number | null)[]
    predicted: (number | null)[]
    lower?: (number | null)[] | null
    upper?: (number | null)[] | null
    /** Indice del primer cubo que cae en el futuro, para la linea de «Ahora». */
    nowIndex?: number | null
    units?: string
    height?: number | string
    /** Rotulo de la grafica. Da nombre al lienzo y encabeza la tabla equivalente. */
    title?: string
  }>(),
  { height: 340, lower: null, upper: null, nowIndex: null },
)

const { themeName, isDark, compact, timeZone } = useChartTheme()

const colors = computed(() => seriesColors(isDark.value))
const measuredColor = computed(() => colors.value[0])
const predictedColor = computed(() => colors.value[1])
const muted = computed(() => (isDark.value ? MUTED.dark : MUTED.light))

const hasBand = computed(
  () =>
    !!props.lower &&
    !!props.upper &&
    props.lower.some((v, i) => v !== null && props.upper?.[i] !== null && props.upper?.[i] !== undefined),
)

const delta = computed(() =>
  props.times.map((_, i) => {
    const lo = props.lower?.[i] ?? null
    const hi = props.upper?.[i] ?? null
    return lo !== null && hi !== null && hi >= lo ? hi - lo : null
  }),
)

const span = computed(() => {
  if (props.times.length < 2) return 0
  return toMillis(props.times[props.times.length - 1]) - toMillis(props.times[0])
})

const labels = computed(() => {
  const format = timeFormatFor(span.value, compact.value)
  return props.times.map((iso) => timeLabel(toMillis(iso), timeZone.value, format))
})

const label = useChartLabel(() => props.title, () => t('dashboards.lidar.prediction.chartLabel'))

const option = computed<EChartsOption>(() => ({
  animationDuration: 300,
  aria: ariaOption(label.value),
  grid: chartGrid(34),
  legend: scrollLegend(true, [
    t('dashboards.lidar.prediction.measured'),
    t('dashboards.lidar.prediction.predicted'),
  ]),
  tooltip: {
    trigger: 'axis',
    confine: true,
    formatter: (params: TooltipComponentFormatterCallbackParams) => {
      const items = asItems(params).filter((i) => i.seriesName && !i.seriesName.startsWith('__'))
      if (!items.length) return ''
      const index = Number((items[0] as TooltipItem & { dataIndex?: number }).dataIndex ?? 0)
      const rows = items.map((i) => tooltipRow(i.marker, i.seriesName ?? '', formatMeasure(i.value, props.units)))
      const lo = props.lower?.[index] ?? null
      const hi = props.upper?.[index] ?? null
      if (lo !== null && hi !== null) {
        rows.push(
          tooltipRow(
            undefined,
            t('dashboards.lidar.prediction.interval'),
            `${formatNumber(lo, 0)} – ${formatNumber(hi, 0)}`,
          ),
        )
      }
      return [tooltipHeader(labels.value[index] ?? ''), ...rows].join('')
    },
  },
  xAxis: {
    type: 'category',
    // Obligatorio con areaStyle: sin esto el area arranca separada del eje.
    boundaryGap: false,
    data: labels.value,
    axisLabel: { hideOverlap: true },
  },
  yAxis: valueAxis(compact.value, 0),
  series: [
    // 1) Base invisible de la banda: solo desplaza la serie apilada hasta el minimo.
    {
      name: '__bandBase',
      type: 'line',
      stack: 'banda',
      stackStrategy: 'all',
      symbol: 'none',
      silent: true,
      z: 1,
      lineStyle: { width: 0, opacity: 0 },
      areaStyle: { opacity: 0 },
      tooltip: { show: false },
      data: hasBand.value ? (props.lower ?? []) : [],
    },
    // 2) Grosor de la banda (maximo menos minimo), pintada sobre la base.
    {
      name: '__bandSpan',
      type: 'line',
      stack: 'banda',
      stackStrategy: 'all',
      symbol: 'none',
      silent: true,
      z: 1,
      lineStyle: { width: 0, opacity: 0 },
      areaStyle: { color: predictedColor.value, opacity: 0.18 },
      tooltip: { show: false },
      data: hasBand.value ? delta.value : [],
    },
    // 3) Valor previsto: discontinuo, porque no es una medida.
    {
      name: t('dashboards.lidar.prediction.predicted'),
      type: 'line',
      z: 3,
      showSymbol: false,
      symbolSize: 5,
      connectNulls: false,
      lineStyle: { width: 2, type: 'dashed', color: predictedColor.value },
      itemStyle: { color: predictedColor.value },
      data: props.predicted,
    },
    // 4) Valor medido, con la linea vertical de «Ahora».
    {
      name: t('dashboards.lidar.prediction.measured'),
      type: 'line',
      z: 4,
      showSymbol: false,
      symbolSize: 5,
      connectNulls: false,
      lineStyle: { width: 2, color: measuredColor.value },
      itemStyle: { color: measuredColor.value },
      data: props.measured,
      markLine: {
        silent: true,
        symbol: 'none',
        label: {
          formatter: t('dashboards.lidar.prediction.now'),
          position: 'insideEndTop',
          color: muted.value,
          fontSize: 11,
        },
        lineStyle: { color: muted.value, type: 'dashed', width: 1 },
        data:
          props.nowIndex !== null && props.nowIndex !== undefined ? [{ xAxis: props.nowIndex }] : [],
      },
    },
  ],
}))

const style = computed(() => chartStyle(props.height))

/**
 * Tabla equivalente: instante, medido, previsto y los dos extremos del intervalo. El intervalo
 * de confianza solo se ve como una banda sombreada, asi que sin estas dos columnas la
 * alternativa perderia justo lo que distingue esta grafica de una de lineas.
 */
const table = computed(() =>
  rowsTable(
    [
      t('dashboards.chart.datetime'),
      t('dashboards.lidar.prediction.measured'),
      t('dashboards.lidar.prediction.predicted'),
      t('dashboards.lidar.prediction.lower'),
      t('dashboards.lidar.prediction.upper'),
    ],
    props.times.map((iso, index) => [
      labels.value[index] ?? iso,
      formatNumber(props.measured[index] ?? null),
      formatNumber(props.predicted[index] ?? null),
      formatNumber(props.lower?.[index] ?? null),
      formatNumber(props.upper?.[index] ?? null),
    ]),
  ),
)
</script>

<template>
  <div>
    <VChart :option="option" :theme="themeName" :style="style" autoresize />
    <DataTableAlternative :title="label" :table="table" />
  </div>
</template>
