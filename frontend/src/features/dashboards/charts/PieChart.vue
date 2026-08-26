<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart as PieSeries } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import type { EChartsOption, TooltipComponentFormatterCallbackParams } from 'echarts'
import { t } from '@/i18n'
import { formatMeasure, formatNumber } from '@/lib/format'
import { useChartTheme } from './useChartTheme'
import {
  asItems,
  categoryLabel,
  lastPoint,
  nonNull,
  timeFormatOf,
  tooltipRow,
} from './chartOptions'
import type { ChartSeries } from './types'

use([CanvasRenderer, PieSeries, TitleComponent, TooltipComponent, LegendComponent])

const props = withDefaults(
  defineProps<{
    series: ChartSeries[]
    units?: string
    height?: number | string
  }>(),
  { height: 280 },
)

/** Mas alla de esta cantidad la leyenda deja de ayudar y solo roba sitio al reparto. */
const MAX_LEGEND_ITEMS = 12

const { themeName, compact, timeZone } = useChartTheme()

const units = computed(() => props.series[0]?.units ?? props.units)

/**
 * Un sector por serie, con su ultimo valor, que es el reparto que tiene sentido leer «ahora».
 * Cuando solo hay una serie el reparto es entre sus propios puntos. Los valores negativos no
 * caben en un reparto porcentual, asi que se descartan.
 */
const slices = computed(() => {
  const format = timeFormatOf(props.series, compact.value)
  const raw =
    props.series.length > 1
      ? props.series.map((serie) => ({ name: serie.name, value: lastPoint(serie)?.v ?? 0 }))
      : nonNull(props.series[0]?.points ?? []).map((point) => ({
          name: categoryLabel(point.t, timeZone.value, format),
          value: point.v ?? 0,
        }))
  return raw.filter((slice) => Number.isFinite(slice.value) && slice.value >= 0)
})

const total = computed(() => slices.value.reduce((sum, slice) => sum + slice.value, 0))

const showLegend = computed(() => slices.value.length > 1 && slices.value.length <= MAX_LEGEND_ITEMS)

/**
 * El anillo se centra en pixeles, no en porcentaje: la cifra total tiene que caer justo en su
 * hueco y el porcentaje se desplazaria con cada altura de panel distinta.
 */
const pixels = computed(() => (typeof props.height === 'number' ? props.height : 280))
const centerY = computed(() => Math.round(pixels.value * (showLegend.value ? 0.44 : 0.5)))

const option = computed<EChartsOption>(() => {
  const figureSize = compact.value ? 18 : 22
  const titleHeight = figureSize * 1.2 + 4 + 14

  return {
    animationDuration: 300,
    title: {
      text: formatNumber(total.value),
      subtext: units.value || t('dashboards.chart.total'),
      left: 'center',
      top: Math.round(centerY.value - titleHeight / 2),
      itemGap: 4,
      textStyle: { fontSize: figureSize, fontWeight: 600 },
      subtextStyle: { fontSize: 11 },
    },
    legend: {
      show: showLegend.value,
      type: 'scroll',
      bottom: 0,
      icon: 'circle',
    },
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const item = asItems(params)[0]
        if (!item) return ''
        const value = formatMeasure(item.value, units.value)
        const percent = item.percent !== undefined ? ` · ${formatNumber(item.percent, 1)} %` : ''
        return tooltipRow(item.marker, item.name ?? '', `${value}${percent}`)
      },
    },
    series: [
      {
        type: 'pie',
        radius: compact.value ? ['48%', '68%'] : ['52%', '72%'],
        center: ['50%', centerY.value],
        avoidLabelOverlap: true,
        label: { show: false },
        labelLine: { show: false },
        emphasis: { scaleSize: 4, itemStyle: { opacity: 0.9 } },
        data: slices.value,
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
