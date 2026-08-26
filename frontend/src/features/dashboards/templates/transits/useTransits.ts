import { computed, ref, watch, type ComputedRef, type Ref, type WritableComputedRef } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import type { ChartPoint } from '../../charts'
import type { DateRange } from '../../lib/range'
import { byDate, kpisOf, sumSeries } from '../shared/aggregate'
import { isCumulative } from '../shared/discovery'
import { fetchSeries, type SeriesRequest } from '../shared/series'
import type { MeasureOption, TemplateDashboard } from '../shared/types'
import { useTemplateData, type UseTemplateData } from '../shared/useTemplateData'
import { buildPairs, type FlowNode, type FlowPair, type PairMode, type PairSet } from './pairs'

/**
 * Medida con la que el modelo de transitos publica el volumen de un recorrido. Hace falta tenerla
 * aqui porque en modo derivado los puntos del panel no la publican: ellos cuentan personas en un
 * sitio, no recorridos entre dos, asi que la medida descubierta en los puntos no sirve para pedir
 * la serie de un par. En modo explicito el par es una entidad de verdad y la medida se descubre.
 */
const PAIR_MEASURE = 'count'

/** Un recorrido con su serie ya leida. `total` a null es «sin dato», nunca cero. */
export interface Route {
  pair: FlowPair
  points: ChartPoint[]
  total: number | null
}

interface EmptyState {
  text: string
  hint: string
  icon: string
}

interface Stat {
  key: string
  label: string
  value: string | number
  hint?: string
  icon?: string
}

interface LoadContext {
  pairs: FlowPair[]
  measureId: string
  cumulative: boolean
  range: DateRange
}

export interface UseTransits {
  /** Fase 1 compartida: puntos, rango, huso y estados. */
  data: UseTemplateData
  mode: ComputedRef<PairMode>
  modeLabel: ComputedRef<string>
  /** Medida efectiva del par, escribible desde el selector. */
  measure: WritableComputedRef<string | null>
  measureItems: ComputedRef<MeasureOption[]>
  busy: Ref<boolean>
  seriesError: Ref<string | null>
  notice: ComputedRef<string | undefined>
  emptyState: ComputedRef<EmptyState | null>
  nodes: ComputedRef<FlowNode[]>
  /** Recorridos con lectura, incluidos los que han medido cero. Los pide la matriz. */
  measured: ComputedRef<Route[]>
  /** Recorridos con volumen, de mayor a menor. Es lo que se dibuja. */
  ranked: ComputedRef<Route[]>
  /** Serie del total de todos los recorridos leidos. */
  totalSeries: ComputedRef<ChartPoint[]>
  stats: ComputedRef<Stat[]>
  refresh: () => Promise<void>
}

export function useTransits(dashboard: TemplateDashboard): UseTransits {
  const data = useTemplateData({ dashboard, intent: 'transit', defaultPreset: '7d' })

  const busy = ref(false)
  const seriesError = ref<string | null>(null)
  const routes = ref<Route[]>([])
  /** Distingue «aun no se ha pedido nada» de «se ha pedido y no hay ni un par con datos». */
  const loaded = ref(false)
  const measureOverride = ref<string | null>(null)

  const pairSet = computed<PairSet>(() => buildPairs(data.points.value))
  const mode = computed<PairMode>(() => pairSet.value.mode)

  const modeLabel = computed(() =>
    mode.value === 'derived'
      ? t('templates.transits.modeDerived')
      : t('templates.transits.modeExplicit'),
  )

  const measure = computed<string | null>({
    get: () => {
      if (measureOverride.value) return measureOverride.value
      return mode.value === 'derived' ? PAIR_MEASURE : data.measureId.value
    },
    set: (value) => {
      measureOverride.value = value
    },
  })

  const measureItems = computed<MeasureOption[]>(() => {
    const items = [...data.measureItems.value]
    // La medida del par no aparece entre las de los puntos del panel, y sin ofrecerla no habria
    // forma de volver a ella despues de probar otra.
    if (!items.some((item) => item.value === PAIR_MEASURE)) {
      items.unshift({ value: PAIR_MEASURE, title: t('templates.transits.measureCount') })
    }
    return items
  })

  const loadContext = computed<LoadContext | null>(() => {
    if (data.loading.value || data.error.value) return null
    const measureId = measure.value
    if (!measureId) return null
    const pairs = pairSet.value.pairs
    if (!pairs.length) return null
    return { pairs, measureId, cumulative: isCumulative(measureId), range: data.range.value }
  })

  async function load(ctx: LoadContext | null): Promise<void> {
    if (!ctx) return
    busy.value = true
    seriesError.value = null
    try {
      const requests: SeriesRequest[] = ctx.pairs.map((pair) => ({
        key: pair.key,
        ref: pair.ref,
        // El par se lee por su propio URN, que no es el de la entidad de la que salen tenant y scope.
        urn: pair.urn,
        measureId: ctx.measureId,
        cumulative: ctx.cumulative,
      }))

      const series = await fetchSeries(requests, ctx.range)

      routes.value = ctx.pairs.map((pair) => {
        const points = series.get(pair.key) ?? []
        return { pair, points, total: kpisOf(points).total }
      })
      loaded.value = true
    } catch (e) {
      seriesError.value = errorMessage(e)
      routes.value = []
    } finally {
      busy.value = false
    }
  }

  watch(loadContext, load, { immediate: true })

  const withData = computed(() => routes.value.filter((route) => route.total !== null))

  const ranked = computed(() =>
    withData.value
      .filter((route) => (route.total ?? 0) > 0)
      .sort((a, b) => (b.total ?? 0) - (a.total ?? 0)),
  )

  const totalSeries = computed(() => sumSeries(withData.value.map((route) => route.points)))

  const grandTotal = computed<number | null>(() => {
    const totals = withData.value.map((route) => route.total).filter((v): v is number => v !== null)
    return totals.length ? totals.reduce((a, b) => a + b, 0) : null
  })

  const dailyMean = computed<number | null>(() => {
    const days = byDate(totalSeries.value, data.timeZone.value, 'sum')
      .map((bucket) => bucket.value)
      .filter((v): v is number => v !== null)
    return days.length ? days.reduce((a, b) => a + b, 0) / days.length : null
  })

  const notice = computed<string | undefined>(() => {
    const limited = pairSet.value.limited
    if (!limited) return undefined
    const params = { shown: limited.shown, total: limited.total }
    return limited.kind === 'sources'
      ? t('templates.transits.limitedSources', params)
      : t('templates.transits.limitedPairs', params)
  })

  const emptyState = computed<EmptyState | null>(() => {
    // Sin puntos asignados no hay ni modo ni pares: manda el estado de la fase compartida.
    if (data.points.value.length === 0) return data.emptyState.value
    if (mode.value === 'derived' && pairSet.value.sources < 2) {
      return {
        text: t('templates.transits.needTwo'),
        hint: t('templates.transits.needTwoHint'),
        icon: 'mdi-map-marker-multiple-outline',
      }
    }
    // En modo explicito la medida sale de los propios pares: sin ninguna no hay nada que pedir.
    if (measure.value === null) return data.emptyState.value
    if (pairSet.value.pairs.length === 0 || (loaded.value && withData.value.length === 0)) {
      return {
        text: t('templates.transits.emptyPairs'),
        hint: t('templates.transits.emptyPairsHint'),
        icon: 'mdi-transit-connection-variant',
      }
    }
    return null
  })

  const stats = computed<Stat[]>(() => {
    const top = ranked.value[0]
    return [
      {
        key: 'total',
        label: t('templates.transits.statTotal'),
        value: formatNumber(grandTotal.value),
        icon: 'mdi-sigma',
      },
      {
        key: 'pairs',
        label: t('templates.transits.statPairs'),
        value: withData.value.length,
        icon: 'mdi-vector-polyline',
      },
      {
        key: 'top',
        label: t('templates.transits.statTop'),
        value: top ? top.pair.label : t('common.noValue'),
        hint: top
          ? t('templates.transits.statTopHint', { volume: formatNumber(top.total) })
          : undefined,
        icon: 'mdi-trophy-outline',
      },
      {
        key: 'daily',
        label: t('templates.transits.statDaily'),
        value: formatNumber(dailyMean.value),
        hint: t('templates.transits.statDailyHint'),
        icon: 'mdi-calendar-clock',
      },
    ]
  })

  async function refresh(): Promise<void> {
    await data.reload()
  }

  return {
    data,
    mode,
    modeLabel,
    measure,
    measureItems,
    busy,
    seriesError,
    notice,
    emptyState,
    nodes: computed(() => pairSet.value.nodes),
    measured: withData,
    ranked,
    totalSeries,
    stats,
    refresh,
  }
}
