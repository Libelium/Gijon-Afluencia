<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { errorMessage } from '@/api/http'
import StateBlock from '@/components/StateBlock.vue'
import { LineChart, toMillis, type ChartPoint, type ChartSeries } from '@/features/dashboards/charts'
import RangeSelector from '@/features/dashboards/components/RangeSelector.vue'
import {
  DEFAULT_RANGE,
  FORECAST_HORIZON_HOURS,
  extendRange,
  intervalHours,
  resolveRange,
  type AggregationOption,
  type DateRange,
  type RangePresetId,
} from '@/features/dashboards/lib/range'
import { isPredictionEntity } from '@/features/dashboards/templates/contract'
import { t } from '@/i18n'
import { formatDateTime, formatMeasure } from '@/lib/format'
import type { EntityRef, Measure } from '@/types'
import { getMeasureHistory } from '../api/history'

const props = defineProps<{
  modelValue: boolean
  /** Nulo mientras no hay medida elegida: el dialogo se abre desde una tarjeta o una fila. */
  measure: Measure | null
  /** Nulo si la entidad no tiene ambito de datos y por tanto no se le puede preguntar. */
  entityRef: EntityRef | null
  timeZone: string
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const CHART_HEIGHT = 320

const preset = ref<RangePresetId>(DEFAULT_RANGE)
const custom = ref<DateRange | null>(null)
const points = ref<ChartPoint[]>([])
const aggregation = ref<AggregationOption | null>(null)
const queried = ref<DateRange | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const open = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

/** El identificador solo aporta cuando difiere del nombre; las unidades siempre. */
const subtitle = computed(() => {
  const measure = props.measure
  if (!measure) return ''
  const parts = [measure.id === measure.name ? '' : measure.id, measure.units ?? '']
  return parts.filter(Boolean).join(' · ')
})

const series = computed<ChartSeries[]>(() => {
  const measure = props.measure
  if (!measure) return []
  return [{ name: measure.name, units: measure.units, points: points.value }]
})

const drawn = computed(() => points.value.filter((point) => point.v !== null))

/** Una ventana entera de huecos es tan vacia como una respuesta sin valores. */
const empty = computed(() => drawn.value.length === 0)

const windowCaption = computed(() => {
  const range = queried.value
  if (!range) return ''
  return t('entities.history.window', {
    start: formatDateTime(range.start, props.timeZone),
    end: formatDateTime(range.end, props.timeZone),
  })
})

const aggregationCaption = computed(() => {
  const hours = intervalHours(aggregation.value?.interval)
  return hours ? t('entities.history.aggregated', { hours }) : ''
})

const countCaption = computed(() => {
  const count = drawn.value.length
  if (!count) return ''
  return count === 1
    ? t('entities.history.pointsOne')
    : t('entities.history.points', { count })
})

const lastCaption = computed(() => {
  // En una prevision los ultimos puntos son horas futuras: el ultimo dato es el de «ahora».
  const now = Date.now()
  const past = drawn.value.filter((point) => toMillis(point.t) <= now)
  const last = past[past.length - 1] ?? drawn.value[drawn.value.length - 1]
  if (!last) return ''
  return t('entities.history.last', {
    value: formatMeasure(last.v, props.measure?.units),
    when: formatDateTime(last.t, props.timeZone),
  })
})

async function load() {
  const entity = props.entityRef
  const measure = props.measure
  if (!entity || !measure) return

  const past = custom.value ?? resolveRange(preset.value, props.timeZone)
  // Una prevision publica horas por delante de «ahora»: cortando ahi solo se verian las pasadas.
  const range = isPredictionEntity(entity) ? extendRange(past, FORECAST_HORIZON_HOURS) : past
  loading.value = true
  error.value = null
  queried.value = range
  try {
    const history = await getMeasureHistory(entity, measure.id, range)
    points.value = history.points
    aggregation.value = history.aggregation
  } catch (e) {
    points.value = []
    aggregation.value = null
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

/**
 * Un solo observador para apertura, medida y rango: Vue agrupa los cambios del mismo ciclo,
 * asi que abrir con otra medida dispara una unica consulta en lugar de dos.
 */
watch([() => props.modelValue, () => props.measure?.id, preset, custom], ([isOpen]) => {
  if (isOpen) {
    void load()
    return
  }
  // Al cerrar se vuelve al rango corto: es el que responde antes y el mas habitual al abrir.
  preset.value = DEFAULT_RANGE
  custom.value = null
  points.value = []
  aggregation.value = null
  queried.value = null
  error.value = null
})

/**
 * Vuetify pone `role="dialog"` y `aria-modal` en el dialogo, pero no lo asocia con su titulo:
 * al abrirse, un lector de pantalla anuncia «dialogo» sin decir cual (WCAG 4.1.2, hallazgo
 * GDTIS-PT01-ACC-007). `useId` genera un identificador unico por instancia, que es lo que hace
 * falta cuando el mismo componente se monta varias veces en una pantalla.
 */
const titleId = useId()
</script>

<template>
  <VDialog v-model="open" max-width="920" scrollable :aria-labelledby="titleId">
    <VCard v-if="measure">
      <VCardTitle class="d-flex align-center ga-3 py-4">
        <div class="min-w-0">
          <div :id="titleId" class="text-h6 text-truncate" :title="measure.name">{{ measure.name }}</div>
          <div v-if="subtitle" class="text-caption text-medium-emphasis text-truncate">
            {{ subtitle }}
          </div>
        </div>
        <VSpacer />
        <VBtn
          icon="mdi-close"
          variant="text"
          density="comfortable"
          :aria-label="t('common.close')"
          @click="open = false"
        />
      </VCardTitle>

      <VDivider />

      <VCardText class="pa-4">
        <div class="d-flex flex-column ga-4">
          <div class="d-flex flex-wrap align-center ga-3">
            <RangeSelector v-model:preset="preset" v-model:custom="custom" :time-zone="timeZone" />
            <VBtn
              icon="mdi-refresh"
              variant="tonal"
              :loading="loading"
              :aria-label="t('common.refresh')"
              :title="t('common.refresh')"
              @click="load()"
            />
            <VSpacer />
            <!-- Un preajuste relativo no dice que periodo cubre: se rotula la ventana efectiva. -->
            <div class="text-caption text-medium-emphasis">
              <div v-if="windowCaption">{{ windowCaption }}</div>
              <div v-if="aggregationCaption">{{ aggregationCaption }}</div>
            </div>
          </div>

          <StateBlock
            :loading="loading"
            :error="error"
            :empty="!loading && !error && empty"
            :empty-text="t('entities.history.empty')"
            :empty-hint="t('entities.history.emptyHint')"
            empty-icon="mdi-chart-line-variant"
            skeleton="card"
            @retry="load()"
          >
            <LineChart
              :series="series"
              :units="measure.units"
              :title="measure.name"
              area
              :height="CHART_HEIGHT"
            />
            <div class="d-flex flex-wrap ga-4 mt-2 text-caption text-medium-emphasis">
              <span v-if="countCaption">{{ countCaption }}</span>
              <span v-if="lastCaption">{{ lastCaption }}</span>
            </div>
          </StateBlock>
        </div>
      </VCardText>
    </VCard>
  </VDialog>
</template>
