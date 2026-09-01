<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart } from 'echarts/charts'
import { AriaComponent, CalendarComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import type { EChartsOption, TooltipComponentFormatterCallbackParams } from 'echarts'
import { t } from '@/i18n'
import { formatDate, formatMeasure } from '@/lib/format'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { LINE, MUTED, occupancyColors } from '../../palette'
import { useChartTheme } from '../../charts/useChartTheme'
import { asItems, axisValue, chartStyle, tooltipHeader, tooltipRow } from '../../charts/chartOptions'
import { ariaOption, rowsTable } from '../../charts/a11y'
import { useChartLabel } from '../../charts/chartLabel'

// Ver LineChart.vue: `AriaComponent` da nombre accesible al lienzo (WCAG 1.1.1, ACC-002).
use([
  CanvasRenderer,
  HeatmapChart,
  CalendarComponent,
  TooltipComponent,
  VisualMapComponent,
  AriaComponent,
])

const props = withDefaults(
  defineProps<{
    /** Un elemento por dia natural del rango. `date` en formato 'yyyy-MM-dd'. */
    days: { date: string; value: number | null }[]
    units?: string
    height?: number
    /** Rotulo del calendario. Da nombre al lienzo y encabeza la tabla equivalente. */
    title?: string
  }>(),
  { height: 240 },
)

const { themeName, isDark, timeZone } = useChartTheme()

const label = useChartLabel(() => props.title, () => t('templates.heatmap.calendarLabel'))

const MONTHS_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
// El array de dias empieza siempre en domingo; firstDay: 1 hace que se dibuje lunes primero.
const DAYS_ES = ['D', 'L', 'M', 'X', 'J', 'V', 'S']

const option = computed<EChartsOption>(() => {
  const withValue = props.days.filter((d) => d.value !== null)
  const max = Math.max(0, ...withValue.map((d) => d.value as number))
  const range: [string, string] = [props.days[0]?.date ?? '', props.days.at(-1)?.date ?? '']
  const muted = isDark.value ? MUTED.dark : MUTED.light
  const line = isDark.value ? LINE.dark : LINE.light

  return {
    animationDuration: 300,
    aria: ariaOption(label.value),
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const item = asItems(params)[0]
        const [date, v] = item.value as [string, number | null]
        return [
          tooltipHeader(formatDate(date, timeZone.value)),
          tooltipRow(
            item.marker,
            t('templates.heatmap.dayTotal'),
            v === null ? t('common.noValue') : formatMeasure(v, props.units),
          ),
        ].join('')
      },
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
    calendar: {
      top: 24,
      left: 44,
      right: 20,
      bottom: 56,
      cellSize: ['auto', 13],
      range,
      splitLine: { show: false },
      itemStyle: { color: 'transparent', borderColor: line, borderWidth: 1 },
      yearLabel: { show: false },
      monthLabel: { color: muted, fontSize: 11, nameMap: MONTHS_ES },
      dayLabel: { color: muted, fontSize: 10, firstDay: 1, nameMap: DAYS_ES },
    },
    series: [
      {
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: props.days.map((d) => [d.date, d.value]),
      },
    ],
  }
})

const style = computed(() => chartStyle(props.height))

/**
 * En un calendario de intensidad el color es el unico portador del dato: la tabla es la unica
 * forma de leer el total de un dia concreto. Se listan solo los dias con lectura.
 */
const table = computed(() =>
  rowsTable(
    [t('templates.heatmap.dayColumn'), t('templates.heatmap.dayTotal')],
    props.days
      .filter((day) => day.value !== null)
      .map((day) => [formatDate(day.date, timeZone.value), formatMeasure(day.value, props.units)]),
    // Un ano natural son 366 filas y todas son dato: aqui el tope general no vale.
    400,
  ),
)
</script>

<template>
  <div>
    <VChart :option="option" :theme="themeName" :style="style" autoresize />
    <DataTableAlternative :title="label" :table="table" />
  </div>
</template>
