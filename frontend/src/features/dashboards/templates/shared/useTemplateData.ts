import { computed, ref, shallowRef, type ComputedRef, type Ref } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { formatDateTime } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import type { Measure } from '@/types'
import { DEFAULT_RANGE, resolveRange, type DateRange, type RangePresetId } from '../../lib/range'
import { loadTemplateEntities, pointsOf } from './entities'
import {
  categoryLabelOf,
  detectCategories,
  isCumulative,
  loadMeasures,
  measureOptions,
  pickMeasure,
} from './discovery'
import type { Category, MeasureIntent, MeasureOption, Point, TemplateDashboard } from './types'

export interface UseTemplateDataOptions {
  dashboard: TemplateDashboard
  intent: MeasureIntent
  /** Descubrir tambien las categorias. Solo lo piden las dos plantillas de clasificacion. */
  withCategories?: boolean
  /** Preajuste inicial de rango. Cada plantilla tiene el suyo. */
  defaultPreset?: RangePresetId
}

export interface TemplateContext {
  points: Point[]
  measureId: string
  cumulative: boolean
  categories: Category[]
  range: DateRange
  timeZone: string
}

export interface UseTemplateData {
  /** Puntos de medida asignados al cuadro. */
  points: Ref<Point[]>
  /** Todas las medidas numericas vistas en los puntos, para los selectores. */
  measureItems: ComputedRef<MeasureOption[]>
  /** Medida principal elegida. Escribible: el VSelect de correccion manual la modifica. */
  measureId: Ref<string | null>
  /** Si la medida elegida es un contador acumulativo. */
  cumulative: ComputedRef<boolean>
  /** Medidas que forman el reparto. Escribible; vacio = usar las detectadas. */
  categoryIds: Ref<string[]>
  /** Categorias efectivas: las elegidas a mano si hay, y si no las detectadas. */
  categories: ComputedRef<Category[]>
  /** Rango: preajuste escribible y ventana resuelta. */
  preset: Ref<RangePresetId>
  range: ComputedRef<DateRange>
  timeZone: ComputedRef<string>
  /** Estado de la fase 1 (puntos + medidas). */
  loading: Ref<boolean>
  error: Ref<string | null>
  /** Puntos cuya lectura en vivo ha fallado; se avisa, no se oculta. */
  failed: Ref<string[]>
  /** null mientras falte algo. Cada plantilla observa esto para pedir sus series. */
  context: ComputedRef<TemplateContext | null>
  /** Leyenda «Datos del … al …». */
  rangeCaption: ComputedRef<string>
  /** Texto y pista del estado vacio de la fase 1, o null si no hay estado vacio. */
  emptyState: ComputedRef<{ text: string; hint: string; icon: string } | null>
  /** Recarga la fase 1 completa. Lo llama el boton actualizar y el reintento del error. */
  reload: () => Promise<void>
}

export function useTemplateData(options: UseTemplateDataOptions): UseTemplateData {
  const { dashboard, intent, withCategories = false } = options
  const session = useSessionStore()

  const points = ref<Point[]>([])
  const allMeasures = shallowRef<Measure[]>([])
  const detected = shallowRef<Category[]>([])
  const measureId = ref<string | null>(null)
  const categoryIds = ref<string[]>([])
  const preset = ref<RangePresetId>(options.defaultPreset ?? DEFAULT_RANGE)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const failed = ref<string[]>([])
  // Cambia en cada reload() para que `range` recalcule «ahora», no solo cuando cambia el preajuste.
  const refreshTick = ref(0)

  const timeZone = computed(() => dashboard.timezone || session.timeZone)

  const range = computed<DateRange>(() => {
    void refreshTick.value
    return resolveRange(preset.value, timeZone.value)
  })

  const measureItems = computed(() => measureOptions(allMeasures.value))

  const cumulative = computed(() => (measureId.value ? isCumulative(measureId.value) : false))

  const categories = computed<Category[]>(() => {
    if (categoryIds.value.length > 0) {
      return categoryIds.value.map((id, index) => ({
        measureId: id,
        label: categoryLabelOf(id, allMeasures.value),
        order: index,
      }))
    }
    return detected.value
  })

  async function reload(): Promise<void> {
    refreshTick.value += 1
    loading.value = true
    error.value = null
    try {
      const entities = await loadTemplateEntities(dashboard)
      const resolvedPoints = pointsOf(entities)
      points.value = resolvedPoints

      if (resolvedPoints.length === 0) return

      const index = await loadMeasures(resolvedPoints)
      failed.value = index.failed
      allMeasures.value = index.all

      if (measureId.value === null || !index.all.some((m) => m.id === measureId.value)) {
        measureId.value = pickMeasure(index.all, intent)
      }

      if (withCategories) detected.value = detectCategories(index.all).categories
    } catch (e) {
      error.value = errorMessage(e)
      points.value = []
    } finally {
      loading.value = false
    }
  }

  const context = computed<TemplateContext | null>(() => {
    if (loading.value || error.value) return null
    if (points.value.length === 0) return null
    if (measureId.value === null) return null
    if (withCategories && categories.value.length === 0) return null
    return {
      points: points.value,
      measureId: measureId.value,
      cumulative: cumulative.value,
      categories: categories.value,
      range: range.value,
      timeZone: timeZone.value,
    }
  })

  const emptyState = computed(() => {
    if (points.value.length === 0) {
      return {
        text: t('templates.common.noPoints'),
        hint: t('templates.common.noPointsHint'),
        icon: 'mdi-map-marker-off-outline',
      }
    }
    if (measureId.value === null) {
      return {
        text: t('templates.common.noMeasure'),
        hint: t('templates.common.noMeasureHint'),
        icon: 'mdi-help-rhombus-outline',
      }
    }
    if (withCategories && categories.value.length === 0) {
      return {
        text: t('templates.common.noCategories'),
        hint: t('templates.common.noCategoriesHint'),
        icon: 'mdi-shape-outline',
      }
    }
    return null
  })

  const rangeCaption = computed(() =>
    t('dashboards.detail.rangeCaption', {
      start: formatDateTime(range.value.start, timeZone.value),
      end: formatDateTime(range.value.end, timeZone.value),
    }),
  )

  void reload()

  return {
    points,
    measureItems,
    measureId,
    cumulative,
    categoryIds,
    categories,
    preset,
    range,
    timeZone,
    loading,
    error,
    failed,
    context,
    rangeCaption,
    emptyState,
    reload,
  }
}
