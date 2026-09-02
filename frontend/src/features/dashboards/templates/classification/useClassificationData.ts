import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import type { ChartPoint } from '../../charts'
import { kpisOf, sumSeries, topByRecency } from '../shared/aggregate'
import { isCumulative } from '../shared/discovery'
import { fetchSeries, type SeriesRequest } from '../shared/series'
import type { Category, Kpis, Point, TemplateDashboard } from '../shared/types'
import { useTemplateData, type TemplateContext } from '../shared/useTemplateData'

/** Tope de puntos combinados con las categorias: mas alla de esto la peticion no aguanta. */
const MAX_POINTS = 8
const MAX_CATEGORIES = 12

/**
 * Carga y agregado por categoria que comparten las dos plantillas de clasificacion (basica y
 * avanzada). Pide una serie por cada par punto × categoria, las suma por categoria y deja tanto
 * el resultado sumado (`byCategory`, `kpisByCategory`, `grandTotal`) como los materiales sin sumar
 * (`usedPoints`, `seriesMap`) que la variante avanzada necesita para su comparativa y su tabla
 * cruzada. La plantilla basica simplemente no lee esos ultimos.
 *
 * Cada plantilla conserva sus propios computeds de presentacion (graficos, tablas, indicadores);
 * aqui vive solo lo comun.
 */
export function useClassificationData(dashboard: TemplateDashboard) {
  const data = useTemplateData({
    dashboard,
    intent: 'occupancy',
    withCategories: true,
    defaultPreset: '7d',
  })

  const busy = ref(false)
  const seriesError = ref<string | null>(null)
  const notice = ref<string | undefined>(undefined)

  const categories = ref<Category[]>([])
  const usedPoints = ref<Point[]>([])
  /** Series sin sumar, indexadas `${point.key}|${category.measureId}`: alimentan la comparativa y la tabla cruzada. */
  const seriesMap = ref<Map<string, ChartPoint[]>>(new Map())
  const byCategory = ref<Record<string, ChartPoint[]>>({})
  const kpisByCategory = ref<Record<string, Kpis>>({})
  const grandTotal = ref<number | null>(null)

  function sumTotals(values: (number | null)[]): number | null {
    const nums = values.filter((v): v is number => v !== null)
    return nums.length ? nums.reduce((a, b) => a + b, 0) : null
  }

  async function load(ctx: TemplateContext | null) {
    if (!ctx) return
    busy.value = true
    seriesError.value = null
    try {
      const cats = ctx.categories.length > MAX_CATEGORIES ? ctx.categories.slice(0, MAX_CATEGORIES) : ctx.categories
      notice.value =
        ctx.categories.length > MAX_CATEGORIES
          ? t('templates.classification.limited', { total: ctx.categories.length })
          : undefined

      const points = topByRecency(ctx.points, MAX_POINTS)

      const requests: SeriesRequest[] = []
      for (const point of points) {
        for (const category of cats) {
          requests.push({
            key: `${point.key}|${category.measureId}`,
            ref: point.ref,
            measureId: category.measureId,
            cumulative: isCumulative(category.measureId),
          })
        }
      }

      const series = await fetchSeries(requests, ctx.range)

      const nextByCategory: Record<string, ChartPoint[]> = {}
      const nextKpis: Record<string, Kpis> = {}
      for (const category of cats) {
        const perPoint = points.map((point) => series.get(`${point.key}|${category.measureId}`) ?? [])
        const summed = sumSeries(perPoint)
        nextByCategory[category.measureId] = summed
        nextKpis[category.measureId] = kpisOf(summed)
      }

      categories.value = cats
      usedPoints.value = points
      seriesMap.value = series
      byCategory.value = nextByCategory
      kpisByCategory.value = nextKpis
      grandTotal.value = sumTotals(cats.map((c) => nextKpis[c.measureId].total))
    } catch (e) {
      seriesError.value = errorMessage(e)
    } finally {
      busy.value = false
    }
  }

  watch(() => data.context.value, load, { immediate: true })

  async function refreshAll() {
    await data.reload()
  }

  const topCategory = computed<Category | null>(() => {
    let best: Category | null = null
    let bestValue = Number.NEGATIVE_INFINITY
    for (const category of categories.value) {
      const total = kpisByCategory.value[category.measureId]?.total
      if (total !== null && total !== undefined && total > bestValue) {
        bestValue = total
        best = category
      }
    }
    return best
  })

  const topPercent = computed<number | null>(() => {
    const category = topCategory.value
    if (!category || !grandTotal.value) return null
    const total = kpisByCategory.value[category.measureId]?.total
    return total === null || total === undefined ? null : (total / grandTotal.value) * 100
  })

  const donutSeries = computed(() =>
    categories.value.map((c) => ({
      name: c.label,
      points: [{ t: data.range.value.end, v: kpisByCategory.value[c.measureId]?.total ?? 0 }],
    })),
  )

  const donutEmpty = computed(() => grandTotal.value === null || grandTotal.value === 0)

  return {
    data,
    busy,
    seriesError,
    notice,
    categories,
    usedPoints,
    seriesMap,
    byCategory,
    kpisByCategory,
    grandTotal,
    topCategory,
    topPercent,
    donutSeries,
    donutEmpty,
    refreshAll,
  }
}
