<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { DateTime } from 'luxon'
import { LineChart } from 'echarts/charts'
import { AriaComponent, GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
// Ver `charts/echartsTheme.ts`: sin esta pieza ECharts 6 ignora `grid.containLabel` y recorta
// las etiquetas de los ejes. Esta tarjeta no pasa por `useChartTheme`, asi que la instala ella.
import { LegacyGridContainLabel } from 'echarts/features'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { useDisplay, useTheme } from 'vuetify'
import { ApiError, errorMessage } from '@/api/http'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import StateBlock from '@/components/StateBlock.vue'
import { ariaOption, rowsTable } from '@/features/dashboards/charts/a11y'
import { locale, t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import type { SeriesPoint } from '@/types'
import { dataScopeId, getAlarmStatusSeries } from '../api/alarms'
import { rangeFromPreset } from '../lib/display'
import type { DateRange } from '../types'

// `AriaComponent` es lo que hace que ECharts ponga `role="img"` y un nombre accesible en el
// contenedor del lienzo. Sin el, el `<canvas>` no tiene nombre (WCAG 1.1.1, ACC-002).
use([
  LineChart,
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer,
  AriaComponent,
  LegacyGridContainLabel,
])

const props = defineProps<{ alarmId: number }>()

const theme = useTheme()
const session = useSessionStore()
const { smAndDown } = useDisplay()

const points = ref<SeriesPoint[]>([])
const range = ref<DateRange>(rangeFromPreset('30d'))
const loading = ref(false)
const error = ref<string | null>(null)
/** Motivo por el que no hay grafico, cuando no es simplemente que no haya datos. */
const notice = ref<string | null>(null)

const millis = (iso: string) => DateTime.fromISO(iso, { zone: 'utc' }).toMillis()

/** El estado solo tiene dos valores; cualquier lectura por encima de la mitad es «disparada». */
const fired = (value: number | null) => (value !== null && value > 0.5 ? 1 : 0)

const rows = computed<[number, number][]>(() => {
  const valid = points.value.filter((point) => point.value !== null)
  const data: [number, number][] = valid
    .map((point) => [millis(point.timestamp), fired(point.value)] as [number, number])
    .filter(([ms]) => Number.isFinite(ms))

  // El ultimo estado conocido sigue vigente: sin este punto la linea se corta a mitad del eje.
  const end = millis(range.value.end)
  const last = data[data.length - 1]
  if (last && Number.isFinite(end) && end > last[0]) data.push([end, last[1]])

  return data
})

const changes = computed(() => {
  let count = 0
  for (let i = 1; i < rows.value.length; i += 1) {
    if (rows.value[i][1] !== rows.value[i - 1][1]) count += 1
  }
  return count
})

const changesLabel = computed(() => {
  if (changes.value === 0) return t('alarms.status.noChanges')
  if (changes.value === 1) return t('alarms.status.changesOne')
  return t('alarms.status.changes', { count: formatNumber(changes.value, 0) })
})

const stateLabel = (value: number) =>
  value > 0.5 ? t('alarms.status.up') : t('alarms.status.down')

const option = computed(() => {
  const colors = theme.current.value.colors
  const zone = session.timeZone
  const compact = smAndDown.value

  return {
    animationDuration: 300,
    aria: ariaOption(t('alarms.status.title')),
    backgroundColor: 'transparent',
    grid: { left: 4, right: 12, top: 16, bottom: 4, containLabel: true },
    // Dos tramos de color: en reposo la linea es un acento tranquilo y al dispararse pasa a
    // rojo, que es lo unico que se busca al mirar este grafico.
    visualMap: {
      show: false,
      type: 'piecewise',
      dimension: 1,
      seriesIndex: 0,
      // Los tramos van acotados a los dos extremos del eje, no abiertos con lte/gt: de una
      // escala sin cerrar la biblioteca no sabe deducir el degradado del area y se rompe al
      // dibujarla. El eje ya esta fijado a 0..1, asi que cerrarlos no cambia el reparto.
      pieces: [
        { min: 0, max: 0.5, color: colors.primary },
        { min: 0.5, max: 1, color: colors.error },
      ],
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: (params: unknown) => {
        const first = Array.isArray(params) ? params[0] : params
        const pair = (first as { value?: [number, number] })?.value
        if (!pair) return ''
        const when = DateTime.fromMillis(pair[0], { zone: zone })
          .setLocale(locale)
          .toFormat('dd/MM/yyyy HH:mm')
        return `${when}<br>${stateLabel(pair[1])}`
      },
    },
    xAxis: {
      type: 'time',
      min: millis(range.value.start),
      max: millis(range.value.end),
      axisLine: { lineStyle: { color: colors.outline } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: {
        color: colors.muted,
        hideOverlap: true,
        formatter: (value: number) =>
          DateTime.fromMillis(value, { zone }).setLocale(locale).toFormat('dd/MM'),
      },
    },
    // Solo dos marcas, y etiquetadas: «0» y «1» no dicen nada a quien lee el grafico.
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      interval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: colors.outline, type: 'dashed' } },
      axisLabel: {
        color: colors.muted,
        fontSize: compact ? 10 : 11,
        formatter: (value: number) => stateLabel(value),
      },
    },
    series: [
      {
        type: 'line',
        step: 'end',
        symbol: 'none',
        connectNulls: true,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.14 },
        data: rows.value,
      },
    ],
  }
})

const chartStyle = computed(() => ({
  height: smAndDown.value ? '200px' : '240px',
  width: '100%',
}))

/**
 * Tabla equivalente del cronograma de estado (WCAG 1.1.1). Se listan los CAMBIOS de estado, no
 * los cientos de lecturas identicas: es la misma informacion que se lee en el escalon del
 * grafico, y una tabla con una fila por lectura seria ilegible.
 */
const table = computed(() =>
  rowsTable(
    [t('dashboards.chart.datetime'), t('alarms.status.stateColumn')],
    rows.value
      .filter((row, index) => index === 0 || row[1] !== rows.value[index - 1][1])
      .map(([ms, value]) => [
        DateTime.fromMillis(ms, { zone: session.timeZone }).setLocale(locale).toFormat('dd/MM/yyyy HH:mm'),
        stateLabel(value),
      ]),
  ),
)

async function load() {
  loading.value = true
  error.value = null
  notice.value = null
  range.value = rangeFromPreset('30d')

  try {
    const series = await getAlarmStatusSeries(
      { id: props.alarmId },
      { range: range.value, scopeId: dataScopeId(session.preferences) },
    )

    if (series.state === 'ok') {
      points.value = series.points
    } else {
      points.value = []
      notice.value =
        series.state === 'unconfigured'
          ? t('alarms.status.unconfigured')
          : t('alarms.status.unresolved')
    }
  } catch (e) {
    points.value = []
    // Sin permiso sobre las series no hay nada que reintentar: se explica y no se ofrece error.
    if (e instanceof ApiError && e.kind === 'forbidden') notice.value = t('alarms.status.forbidden')
    else error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

watch(() => props.alarmId, load, { immediate: true })
</script>

<template>
  <VCard>
    <div class="d-flex flex-wrap align-center ga-3 pa-4">
      <div class="flex-grow-1 min-w-0">
        <div class="text-subtitle-2">{{ t('alarms.status.title') }}</div>
        <div class="text-caption text-medium-emphasis">{{ t('alarms.status.subtitle') }}</div>
      </div>
      <VBtn
        icon="mdi-refresh"
        variant="text"
        density="comfortable"
        :loading="loading"
        :aria-label="t('common.refresh')"
        @click="load"
      />
    </div>

    <VDivider />

    <StateBlock
      :loading="loading && !rows.length"
      :error="error"
      :empty="!loading && !error && !rows.length"
      :empty-text="notice || t('alarms.status.empty')"
      empty-icon="mdi-chart-timeline-variant"
      skeleton="card"
      @retry="load"
    >
      <div class="pa-4">
        <VChart :option="option" :style="chartStyle" autoresize />
        <div class="text-caption text-medium-emphasis mt-3">{{ changesLabel }}</div>
        <DataTableAlternative :title="t('alarms.status.title')" :table="table" />
      </div>
    </StateBlock>
  </VCard>
</template>
