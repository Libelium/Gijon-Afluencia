import { registerTheme } from 'echarts/core'
import { INK, LINE, MUTED, SURFACE, seriesColors } from '../palette'

/** Misma pila que usa la aplicacion; en lienzo hay que darla escrita, no se hereda del CSS. */
const FONT_FAMILY = 'Roboto, system-ui, sans-serif'

/** Separacion entre el eje y sus etiquetas: sin ella el texto queda pegado a la linea. */
const LABEL_MARGIN = 10

export const CHART_THEME = { light: 'pid-light', dark: 'pid-dark' } as const

export type ChartThemeName = (typeof CHART_THEME)[keyof typeof CHART_THEME]

export function chartThemeFor(theme: 'light' | 'dark'): ChartThemeName {
  return theme === 'dark' ? CHART_THEME.dark : CHART_THEME.light
}

function build(isDark: boolean) {
  const ink = isDark ? INK.dark : INK.light
  const line = isDark ? LINE.dark : LINE.light
  const muted = isDark ? MUTED.dark : MUTED.light
  const surface = isDark ? SURFACE.dark : SURFACE.light

  const label = { color: muted, fontSize: 11, fontFamily: FONT_FAMILY, margin: LABEL_MARGIN }

  // Ejes discretos: sin marcas, con la linea de base tenue y sin rejilla propia.
  const categoryAxis = {
    axisLine: { show: true, lineStyle: { color: line } },
    axisTick: { show: false },
    axisLabel: label,
    splitLine: { show: false },
    splitArea: { show: false },
  }

  // El eje de valores no dibuja su propia linea: la referencia es la rejilla horizontal,
  // trazada en solido y muy tenue para que no compita con las series.
  const valueAxis = {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: label,
    splitLine: { show: true, lineStyle: { color: line, width: 1 } },
    splitArea: { show: false },
  }

  return {
    color: seriesColors(isDark),
    backgroundColor: 'transparent',
    textStyle: { fontFamily: FONT_FAMILY, fontSize: 12, color: ink },
    title: {
      textStyle: { color: ink, fontSize: 14, fontWeight: 500, fontFamily: FONT_FAMILY },
      subtextStyle: { color: muted, fontSize: 12, fontFamily: FONT_FAMILY },
    },
    grid: { left: 8, right: 16, top: 20, bottom: 8, containLabel: true },
    legend: {
      bottom: 0,
      left: 'center',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 16,
      padding: [4, 8],
      textStyle: { color: muted, fontSize: 11, fontFamily: FONT_FAMILY, padding: [0, 0, 0, 2] },
      pageTextStyle: { color: muted },
      pageIconColor: muted,
      pageIconInactiveColor: line,
      pageIconSize: 10,
      inactiveColor: line,
    },
    tooltip: {
      backgroundColor: surface,
      borderColor: line,
      borderWidth: 1,
      borderRadius: 10,
      padding: [10, 12],
      textStyle: { color: ink, fontSize: 12, fontFamily: FONT_FAMILY },
      extraCssText: `border-radius:10px;box-shadow:0 4px 16px rgba(28,24,48,${isDark ? '.5' : '.12'});`,
      axisPointer: {
        lineStyle: { color: muted, width: 1, type: 'dashed' },
        crossStyle: { color: muted, width: 1 },
        shadowStyle: { color: isDark ? 'rgba(233,230,242,.06)' : 'rgba(28,24,48,.05)' },
        label: { backgroundColor: muted, color: surface, borderRadius: 4, padding: [4, 6] },
      },
    },
    categoryAxis,
    timeAxis: categoryAxis,
    logAxis: valueAxis,
    valueAxis,
    line: { symbol: 'circle', symbolSize: 5, lineStyle: { width: 2 }, smooth: false },
    bar: { itemStyle: { borderRadius: [4, 4, 0, 0] } },
    pie: {
      itemStyle: { borderColor: surface, borderWidth: 2 },
      label: { color: muted, fontFamily: FONT_FAMILY },
      labelLine: { lineStyle: { color: line } },
    },
    gauge: {
      title: { color: muted, fontFamily: FONT_FAMILY },
      detail: { color: ink, fontFamily: FONT_FAMILY },
      axisLine: { lineStyle: { color: [[1, line]] } },
      axisLabel: { color: muted, fontFamily: FONT_FAMILY },
      axisTick: { lineStyle: { color: line } },
      splitLine: { lineStyle: { color: line } },
    },
  }
}

registerTheme(CHART_THEME.light, build(false))
registerTheme(CHART_THEME.dark, build(true))
