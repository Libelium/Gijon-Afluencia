<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GaugeChart as GaugeSeries } from 'echarts/charts'
import { AriaComponent } from 'echarts/components'
import type { EChartsOption } from 'echarts'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { useChartTheme } from '../../../charts'
import { axisValue, chartStyle } from '../../../charts/chartOptions'
import { ariaOption, pairsTable } from '../../../charts/a11y'
import { useChartLabel } from '../../../charts/chartLabel'
import { INK, MUTED, occupancyColors } from '../../../palette'
import { occupancyRatio } from '../data'

// Ver LineChart.vue: `AriaComponent` da nombre accesible al lienzo (WCAG 1.1.1, ACC-002).
use([CanvasRenderer, GaugeSeries, AriaComponent])

const props = withDefaults(
  defineProps<{
    value: number | null
    /** Aforo maximo. Este componente NO se monta si no hay aforo. */
    capacity: number
    height?: number | string
    /** Rotulo del indicador. Da nombre al lienzo y encabeza la tabla equivalente. */
    title?: string
  }>(),
  { height: 260 },
)

const { themeName, isDark } = useChartTheme()

const label = useChartLabel(() => props.title, () => t('dashboards.lidar.analytics.gaugeLabel'))

const ratio = computed(() => occupancyRatio(props.value, props.capacity))
const clamped = computed(() => Math.min(Math.max(props.value ?? 0, 0), props.capacity))
const percentText = computed(() =>
  ratio.value === null ? t('common.noValue') : `${formatNumber(ratio.value * 100, 0)} %`,
)
const countText = computed(() =>
  t('dashboards.lidar.analytics.gaugeCount', {
    value: props.value === null ? t('common.noValue') : formatNumber(props.value, 0),
    capacity: formatNumber(props.capacity, 0),
  }),
)

const option = computed<EChartsOption>(() => {
  const steps = occupancyColors(isDark.value)
  const ink = isDark.value ? INK.dark : INK.light
  const muted = isDark.value ? MUTED.dark : MUTED.light

  return {
    animationDuration: 400,
    aria: ariaOption(label.value),
    series: [
      {
        type: 'gauge',
        min: 0,
        max: props.capacity,
        startAngle: 205,
        endAngle: -25,
        // Radio por debajo del 100 %: las etiquetas de 0 y del aforo caen en los extremos
        // y con el arco al borde se recortan contra la tarjeta.
        radius: '88%',
        center: ['50%', '64%'],
        splitNumber: 1,
        progress: { show: false },
        axisLine: {
          roundCap: false,
          lineStyle: {
            width: 18,
            color: steps.map((color, index) => [(index + 1) / steps.length, color] as [number, string]),
          },
        },
        pointer: { show: true, width: 5, length: '58%', itemStyle: { color: ink } },
        anchor: { show: true, size: 10, showAbove: true, itemStyle: { color: ink } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { distance: 24, fontSize: 11, color: muted, formatter: (v: number) => axisValue(v) },
        title: { show: true, offsetCenter: [0, '30%'], fontSize: 12, color: muted },
        detail: {
          offsetCenter: [0, '-2%'],
          fontSize: 30,
          fontWeight: 700,
          color: ink,
          formatter: () => percentText.value,
        },
        data: [{ value: clamped.value, name: countText.value }],
      },
    ],
  }
})

const style = computed(() => chartStyle(props.height))

// La aguja y el porcentaje solo existen dibujados: la tabla da las tres cifras en texto.
const table = computed(() =>
  pairsTable(
    [
      {
        label: t('dashboards.lidar.occupancyColumn'),
        value: props.value === null ? t('common.noValue') : formatNumber(props.value, 0),
      },
      { label: t('dashboards.lidar.analytics.capacity'), value: formatNumber(props.capacity, 0) },
      { label: t('dashboards.lidar.analytics.ratio'), value: percentText.value },
    ],
    [t('dashboards.lidar.analytics.magnitude'), t('dashboards.chart.value')],
  ),
)
</script>

<template>
  <div>
    <VChart :option="option" :theme="themeName" :style="style" autoresize />
    <DataTableAlternative :title="label" :table="table" />
  </div>
</template>
