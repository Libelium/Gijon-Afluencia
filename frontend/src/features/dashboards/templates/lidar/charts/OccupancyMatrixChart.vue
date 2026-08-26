<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import type { EChartsOption } from 'echarts'
import { t } from '@/i18n'
import { formatMeasure } from '@/lib/format'
import { useChartTheme } from '../../../charts'
import { axisValue, tooltipHeader, tooltipRow } from '../../../charts/chartOptions'
import { INK, LINE, MUTED, occupancyColors, SURFACE } from '../../../palette'
import type { MatrixCell } from '../data'

use([CanvasRenderer, HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent])

const props = withDefaults(
  defineProps<{
    cells: MatrixCell[]
    /** Techo de la escala de color: el aforo, o null para usar el maximo observado. */
    max: number | null
    units?: string
    height?: number | string
  }>(),
  { height: 320 },
)

const { themeName, isDark } = useChartTheme()

const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'))
const DAYS = [1, 2, 3, 4, 5, 6, 7].map((d) => t(`dashboards.lidar.weekdayShort.${d}`))

const option = computed<EChartsOption>(() => {
  const data = props.cells
    .filter((c) => c.value !== null)
    .map((c) => [c.hour, c.weekday - 1, c.value] as [number, number, number])

  const observed = Math.max(1, ...data.map((d) => d[2]))
  const ceiling = props.max && props.max > 0 ? props.max : observed
  const muted = isDark.value ? MUTED.dark : MUTED.light
  const surface = isDark.value ? SURFACE.dark : SURFACE.light

  return {
    animationDuration: 300,
    grid: { left: 8, right: 16, top: 12, bottom: 64, containLabel: true },
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params) => {
        const [hour, day, value] = (params as unknown as { data: [number, number, number] }).data
        const head = t('dashboards.lidar.heatmap.cellTooltip', {
          weekday: t(`dashboards.lidar.weekday.${day + 1}`),
          hour: `${HOURS[hour]}:00`,
        })
        return [
          tooltipHeader(head),
          tooltipRow(
            (params as unknown as { marker?: string }).marker,
            t('dashboards.lidar.heatmap.profileSeries'),
            formatMeasure(value, props.units),
          ),
        ].join('')
      },
    },
    xAxis: {
      type: 'category',
      data: HOURS,
      splitArea: { show: false },
      axisLine: { show: true, lineStyle: { color: isDark.value ? LINE.dark : LINE.light } },
      axisTick: { show: false },
      axisLabel: { color: muted, fontSize: 10, interval: 1, margin: 10 },
    },
    yAxis: {
      type: 'category',
      data: DAYS,
      // Lunes arriba: una semana se lee de arriba abajo.
      inverse: true,
      splitArea: { show: false },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: muted, fontSize: 11, margin: 10 },
    },
    visualMap: {
      type: 'continuous',
      min: 0,
      max: ceiling,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 12,
      itemHeight: 140,
      precision: 0,
      inRange: { color: occupancyColors(isDark.value) },
      textStyle: { color: muted, fontSize: 11 },
      formatter: (value: unknown) => axisValue(Number(value)),
    },
    series: [
      {
        type: 'heatmap',
        data,
        progressive: 0,
        itemStyle: { borderColor: surface, borderWidth: 2, borderRadius: 3 },
        label: { show: false },
        emphasis: { itemStyle: { borderColor: isDark.value ? INK.dark : INK.light, borderWidth: 2 } },
      },
    ],
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
