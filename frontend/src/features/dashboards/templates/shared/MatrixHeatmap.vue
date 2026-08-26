<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import type { EChartsOption, TooltipComponentFormatterCallbackParams } from 'echarts'
import { t } from '@/i18n'
import { formatMeasure } from '@/lib/format'
import { occupancyColors, INK, MUTED, SURFACE } from '../../palette'
import { useChartTheme } from '../../charts/useChartTheme'
import { asItems, axisValue, tooltipHeader, tooltipRow } from '../../charts/chartOptions'
import type { MatrixCell } from './types'

use([CanvasRenderer, HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent])

const props = withDefaults(
  defineProps<{
    /** Rotulos del eje X, de izquierda a derecha. */
    xLabels: string[]
    /** Rotulos del eje Y, DE ARRIBA A ABAJO. El componente los invierte por dentro. */
    yLabels: string[]
    /** Celdas con `x` indice en xLabels e `y` indice en yLabels (arriba = 0). */
    cells: MatrixCell[]
    units?: string
    /** Rotulo del valor en el tooltip. Por defecto t('templates.common.value'). */
    valueLabel?: string
    height?: number
    xLabelRotate?: number
    xLabelInterval?: number | 'auto'
  }>(),
  { height: 320, xLabelRotate: 0, xLabelInterval: 'auto' },
)

const { themeName, isDark } = useChartTheme()

const option = computed<EChartsOption>(() => {
  const rows = props.yLabels.length
  const max = Math.max(0, ...props.cells.map((c) => c.value ?? 0))
  const surface = isDark.value ? SURFACE.dark : SURFACE.light
  const muted = isDark.value ? MUTED.dark : MUTED.light
  const ink = isDark.value ? INK.dark : INK.light

  return {
    animationDuration: 300,
    // El fondo reserva 56 px para la barra de intensidad horizontal.
    grid: { left: 8, right: 12, top: 8, bottom: 56, containLabel: true },
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const item = asItems(params)[0]
        const [x, y, v] = item.value as [number, number, number | string]
        const head = `${props.yLabels[rows - 1 - y]} · ${props.xLabels[x]}`
        const text = v === '-' ? t('common.noValue') : formatMeasure(v, props.units)
        return [
          tooltipHeader(head),
          tooltipRow(item.marker, props.valueLabel ?? t('templates.common.value'), text),
        ].join('')
      },
    },
    xAxis: {
      type: 'category',
      data: props.xLabels,
      splitArea: { show: false },
      axisLabel: {
        interval: props.xLabelInterval,
        rotate: props.xLabelRotate,
        hideOverlap: props.xLabelRotate === 0,
        width: props.xLabelRotate ? 90 : undefined,
        overflow: props.xLabelRotate ? 'truncate' : undefined,
      },
    },
    yAxis: {
      type: 'category',
      data: [...props.yLabels].reverse(),
      splitArea: { show: false },
      axisLabel: { width: 96, overflow: 'truncate' },
    },
    visualMap: {
      min: 0,
      max: max > 0 ? max : 1,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 12,
      itemHeight: 110,
      inRange: { color: occupancyColors(isDark.value) },
      textStyle: { color: muted, fontSize: 11 },
      formatter: (value: unknown) => axisValue(Number(value)),
    },
    series: [
      {
        type: 'heatmap',
        // Coordenada Y invertida: la fila 0 de `yLabels` tiene que salir arriba.
        data: props.cells.map((c) => [c.x, rows - 1 - c.y, c.value ?? '-']),
        itemStyle: { borderColor: surface, borderWidth: 1, borderRadius: 3 },
        emphasis: { itemStyle: { borderColor: ink, borderWidth: 2 } },
        label: { show: false },
        progressive: 0,
      },
    ],
  }
})

const style = computed(() => ({ height: `${props.height}px`, width: '100%' }))
</script>

<template>
  <VChart :option="option" :theme="themeName" :style="style" autoresize />
</template>
