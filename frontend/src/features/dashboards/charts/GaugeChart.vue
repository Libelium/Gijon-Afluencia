<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GaugeChart as GaugeSeries } from 'echarts/charts'
import { AriaComponent } from 'echarts/components'
import type { EChartsOption } from 'echarts'
import { formatMeasure } from '@/lib/format'
import { t } from '@/i18n'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { LINE, occupancyColors, seriesColors } from '../palette'
import { useChartTheme } from './useChartTheme'
import { axisValue, chartStyle, lastPoint, niceCeil } from './chartOptions'
import { useChartLabel } from './chartLabel'
import { ariaOption, seriesTable } from './a11y'
import type { ChartSeries } from './types'

// Ver LineChart.vue: `AriaComponent` da nombre accesible al lienzo (WCAG 1.1.1, ACC-002).
use([CanvasRenderer, GaugeSeries, AriaComponent])

const props = withDefaults(
  defineProps<{
    series: ChartSeries[]
    units?: string
    min?: number
    max?: number
    /** 'occupancy' pinta la escala de niveles; el resto de medidas no admiten ese significado. */
    scale?: 'neutral' | 'occupancy'
    height?: number | string
    /** Rotulo del indicador. Da nombre al lienzo y encabeza la tabla equivalente. */
    title?: string
  }>(),
  { scale: 'neutral', height: 280 },
)

const { themeName, isDark, compact, timeZone } = useChartTheme()

const units = computed(() => props.series[0]?.units ?? props.units)
const value = computed(() => lastPoint(props.series[0])?.v ?? null)

const min = computed(() => props.min ?? Math.min(0, value.value ?? 0))
const max = computed(() => props.max ?? niceCeil(Math.max(value.value ?? 0, 1)))

const label = useChartLabel(
  () => props.title || props.series[0]?.name,
  () => t('dashboards.chart.gauge'),
)

const option = computed<EChartsOption>(() => {
  const track = isDark.value ? LINE.dark : LINE.light
  const accent = seriesColors(isDark.value)[0]
  const graded = props.scale === 'occupancy'
  const steps = occupancyColors(isDark.value)
  const width = compact.value ? 12 : 16

  return {
    animationDuration: 400,
    aria: ariaOption(label.value),
    series: [
      {
        type: 'gauge',
        min: min.value,
        max: max.value,
        startAngle: 205,
        endAngle: -25,
        // El arco no llega al borde: las etiquetas de minimo y maximo caen a sus extremos
        // y con el radio al 94 % se recortaban contra la tarjeta.
        radius: '86%',
        center: ['50%', '62%'],
        splitNumber: 1,
        progress: graded ? { show: false } : { show: true, width, roundCap: true, itemStyle: { color: accent } },
        axisLine: {
          roundCap: !graded,
          lineStyle: {
            width,
            color: graded
              ? steps.map((color, index) => [(index + 1) / steps.length, color] as [number, string])
              : [[1, track]],
          },
        },
        pointer: graded
          ? { show: true, width: 4, length: '62%', itemStyle: { color: accent } }
          : { show: false },
        anchor: graded ? { show: true, size: 8, itemStyle: { color: accent } } : { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          distance: width + 6,
          fontSize: 11,
          formatter: (raw: number) => axisValue(raw),
        },
        title: { show: false },
        detail: {
          offsetCenter: [0, '-8%'],
          fontSize: compact.value ? 20 : 26,
          fontWeight: 600,
          formatter: () => (value.value === null ? '—' : formatMeasure(value.value, units.value)),
        },
        data: [{ value: value.value ?? min.value }],
      },
    ],
  }
})

const style = computed(() => chartStyle(props.height))

// La aguja marca el ultimo valor, pero la serie completa es el dato que llega: se ofrece entera,
// que es mas —no menos— de lo que el dibujo deja leer.
const table = computed(() =>
  seriesTable(props.series, { timeZone: timeZone.value, units: props.units, order: 'desc' }),
)
</script>

<template>
  <div>
    <VChart :option="option" :theme="themeName" :style="style" autoresize />
    <DataTableAlternative :title="label" :table="table" />
  </div>
</template>
