<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import type { Aggregation, Measure } from '@/types'
import { listMeasures, searchEntities, type EntityOption } from '../api/catalog'
import { createPanel } from '../api/dashboards'
import {
  AGGREGATIONS,
  CHART_TYPES,
  DEFAULT_AGGREGATION,
  DEFAULT_CHART_TYPE,
  INTERVALS,
  chartTypeOption,
  type ChartTypeId,
} from '../lib/chartTypes'

const props = defineProps<{ modelValue: boolean; dashboardId: number }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; created: [] }>()

const SEARCH_DEBOUNCE = 350
/** Tamano de pagina del desplegable de entidades. Corto a proposito: es una lista para elegir. */
const ENTITY_PAGE_SIZE = 25

const title = ref('')
const titleTouched = ref(false)
const chartType = ref<ChartTypeId>(DEFAULT_CHART_TYPE)
const entity = ref<EntityOption | null>(null)
const measure = ref<Measure | null>(null)
const aggregation = ref<Aggregation>(DEFAULT_AGGREGATION)
const interval = ref('')

const entitySearch = ref('')
const entityOptions = ref<EntityOption[]>([])
const entityLoading = ref(false)
const entityCount = ref(0)
const entityPage = ref(1)
const measures = ref<Measure[]>([])
const measureLoading = ref(false)
const measureError = ref<string | null>(null)
const saving = ref(false)
const error = ref<string | null>(null)

const open = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const option = computed(() => chartTypeOption(chartType.value) ?? CHART_TYPES[0])
const lastValueOnly = computed(() => option.value.lastValueOnly)

const chartItems = computed(() => CHART_TYPES.map((o) => ({ value: o.id, title: t(o.labelKey), icon: o.icon })))
const aggregationItems = computed(() => AGGREGATIONS.map((a) => ({ value: a.value, title: t(a.labelKey) })))
const intervalItems = computed(() => INTERVALS.map((i) => ({ value: i.value, title: t(i.labelKey) })))

const titleError = computed(() =>
  titleTouched.value && !title.value.trim() ? t('dashboards.panelForm.nameRequired') : undefined,
)

const canSubmit = computed(() => !!title.value.trim() && !!entity.value && !!measure.value && !saving.value)

/** Quedan entidades por traer del servidor: se puede pedir la pagina siguiente. */
const hasMoreEntities = computed(() => entityOptions.value.length < entityCount.value)

let entitySequence = 0
let entityTimer: ReturnType<typeof setTimeout> | undefined

/**
 * Trae entidades del servidor. `reset` distingue las dos situaciones: empezar de cero (al abrir
 * el dialogo o al cambiar el texto de busqueda) o anadir la pagina siguiente a lo ya listado.
 *
 * El listado se pagina en el servidor, no en el cliente: hay decenas de miles de entidades y
 * traerlas todas para filtrarlas aqui no es viable. Por eso el desplegable lleva `no-filter`.
 */
async function loadEntities(reset: boolean) {
  const page = reset ? 1 : entityPage.value + 1
  const current = ++entitySequence
  entityLoading.value = true
  try {
    const result = await searchEntities({
      search: (entitySearch.value ?? '').trim() || undefined,
      page,
      limit: ENTITY_PAGE_SIZE,
    })
    if (current !== entitySequence) return
    entityPage.value = page
    entityCount.value = result.count
    entityOptions.value = reset ? result.rows : [...entityOptions.value, ...result.rows]
  } catch {
    if (current !== entitySequence) return
    if (reset) {
      entityOptions.value = []
      entityCount.value = 0
    }
  } finally {
    if (current === entitySequence) entityLoading.value = false
  }
}

watch(entitySearch, (value) => {
  // Al elegir una opcion, Vuetify escribe su titulo en el texto de busqueda. Sin esta guarda,
  // cada seleccion lanzaria una busqueda mas por un termino que ya no interesa a nadie.
  if (entity.value && value === entity.value.name) return
  clearTimeout(entityTimer)
  entityTimer = setTimeout(() => void loadEntities(true), SEARCH_DEBOUNCE)
})

watch(entity, async (value) => {
  measure.value = null
  measures.value = []
  measureError.value = null
  if (!value) return
  measureLoading.value = true
  try {
    const rows = await listMeasures({ urn: value.urn, tenant: value.tenant, scope: value.scope })
    measures.value = rows
    if (rows.length === 1) measure.value = rows[0]
  } catch (e) {
    measureError.value = errorMessage(e)
  } finally {
    measureLoading.value = false
  }
})

watch(measure, (value) => {
  if (!titleTouched.value && value) title.value = value.name
})

watch(
  () => props.modelValue,
  (value) => {
    if (!value) return
    title.value = ''
    titleTouched.value = false
    chartType.value = DEFAULT_CHART_TYPE
    entity.value = null
    measure.value = null
    aggregation.value = DEFAULT_AGGREGATION
    interval.value = ''
    entitySearch.value = ''
    entityOptions.value = []
    entityCount.value = 0
    entityPage.value = 1
    entityLoading.value = false
    // La primera pagina se trae al abrir: un desplegable vacio hasta que alguien acierte a
    // escribir dos letras parece roto, y ademas obliga a saber de antemano que se busca.
    void loadEntities(true)
    measures.value = []
    measureLoading.value = false
    measureError.value = null
    saving.value = false
    error.value = null
  },
)

onBeforeUnmount(() => clearTimeout(entityTimer))

async function submit() {
  if (!canSubmit.value) return
  saving.value = true
  error.value = null
  try {
    await createPanel({
      dashboardId: props.dashboardId,
      title: title.value,
      chartType: chartType.value,
      chartTitle: t(option.value.labelKey),
      entity: entity.value!,
      measure: { id: measure.value!.id, name: measure.value!.name, units: measure.value!.units },
      aggregation: lastValueOnly.value ? DEFAULT_AGGREGATION : aggregation.value,
      interval: lastValueOnly.value ? '' : interval.value,
    })
    open.value = false
    emit('created')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <VDialog v-model="open" scrollable :persistent="saving">
    <VCard>
      <VCardTitle class="d-flex align-center ga-3 py-4">
        <span class="text-h6">{{ t('dashboards.panelForm.title') }}</span>
        <VSpacer />
        <VBtn
          icon="mdi-close"
          variant="text"
          density="comfortable"
          :disabled="saving"
          :aria-label="t('common.close')"
          @click="open = false"
        />
      </VCardTitle>

      <VDivider />

      <VCardText class="pa-4">
        <div class="d-flex flex-column ga-4">
          <VTextField
            v-model="title"
            :label="t('dashboards.panelForm.name')"
            maxlength="120"
            :error-messages="titleError"
            @input="titleTouched = true"
          />

          <VSelect
            v-model="chartType"
            :items="chartItems"
            item-title="title"
            item-value="value"
            :label="t('dashboards.panelForm.chartType')"
          >
            <template #item="{ item, props: itemProps }">
              <VListItem v-bind="itemProps">
                <template #prepend>
                  <VIcon :icon="item.raw.icon" class="me-2" />
                </template>
              </VListItem>
            </template>
            <template #selection="{ item }">
              <VIcon :icon="item.raw.icon" class="me-2" />
              {{ item.title }}
            </template>
          </VSelect>

          <VAutocomplete
            v-model="entity"
            v-model:search="entitySearch"
            :items="entityOptions"
            return-object
            item-title="name"
            item-value="urn"
            :loading="entityLoading"
            :label="t('dashboards.panelForm.entity')"
            :hint="t('dashboards.panelForm.entityHint')"
            persistent-hint
            :no-data-text="entityLoading ? t('common.loading') : t('dashboards.panelForm.entityEmpty')"
            no-filter
            clearable
            prepend-inner-icon="mdi-magnify"
          >
            <template #item="{ item, props: itemProps }">
              <VListItem v-bind="itemProps" :subtitle="`${urnTail(item.raw.urn)} · ${item.raw.datamodel}`" />
            </template>

            <!-- Paginacion explicita en lugar de scroll infinito: el numero de entidades es
                 informacion util por si el filtro que se busca es otro. -->
            <template v-if="hasMoreEntities" #append-item>
              <VDivider />
              <div class="pa-2">
                <VBtn
                  variant="text"
                  color="primary"
                  block
                  :loading="entityLoading"
                  @click="loadEntities(false)"
                >
                  {{ t('dashboards.panelForm.entityMore', { shown: entityOptions.length, total: entityCount }) }}
                </VBtn>
              </div>
            </template>
          </VAutocomplete>

          <VSelect
            v-model="measure"
            :items="measures"
            return-object
            item-title="name"
            item-value="id"
            :label="t('dashboards.panelForm.measure')"
            :loading="measureLoading"
            :disabled="!entity || measureLoading"
            :no-data-text="t('dashboards.panelForm.measureEmpty')"
            :error-messages="measureError ? [t('dashboards.panelForm.measureError')] : []"
          >
            <template #item="{ item, props: itemProps }">
              <VListItem
                v-bind="itemProps"
                :subtitle="item.raw.units ? t('dashboards.panelForm.units', { units: item.raw.units }) : undefined"
              />
            </template>
          </VSelect>

          <div v-if="!lastValueOnly" class="d-flex ga-4">
            <VSelect
              v-model="aggregation"
              :items="aggregationItems"
              class="flex-1-1-0"
              :label="t('dashboards.panelForm.aggregation')"
            />
            <VSelect
              v-model="interval"
              :items="intervalItems"
              class="flex-1-1-0"
              :label="t('dashboards.panelForm.interval')"
            />
          </div>

          <div v-if="!lastValueOnly" class="text-caption text-medium-emphasis">
            {{ t('dashboards.panelForm.aggregationHint') }} · {{ t('dashboards.panelForm.intervalHint') }}
          </div>

          <VAlert v-else type="info" density="comfortable" :text="t('dashboards.panelForm.lastValueOnly')" />

          <VAlert v-if="error" type="error" :text="error" />
        </div>
      </VCardText>

      <VDivider />

      <VCardActions class="pa-4 ga-3 justify-end">
        <VBtn variant="text" :disabled="saving" @click="open = false">{{ t('common.cancel') }}</VBtn>
        <VBtn
          color="primary"
          prepend-icon="mdi-plus"
          :loading="saving"
          :disabled="!canSubmit"
          @click="submit"
        >
          {{ t('dashboards.panelForm.submit') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
