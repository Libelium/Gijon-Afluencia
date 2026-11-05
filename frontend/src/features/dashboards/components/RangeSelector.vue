<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { t } from '@/i18n'
import {
  MAX_CUSTOM_DAYS,
  RANGE_PRESETS,
  customRange,
  rangeDays,
  resolveRange,
  type DateRange,
  type RangePresetId,
} from '../lib/range'

const CUSTOM = 'custom'

const props = defineProps<{
  preset: RangePresetId
  /** Solo se ofrece «Personalizado» si el padre enlaza `v-model:custom`, aunque sea a null. */
  custom?: DateRange | null
  timeZone?: string
  /** Ocupa todo el ancho: en movil el selector va en su propia fila. */
  block?: boolean
}>()

const emit = defineEmits<{
  'update:preset': [RangePresetId]
  'update:custom': [DateRange | null]
}>()

const allowCustom = computed(() => props.custom !== undefined)
const customMode = ref(!!props.custom)
const startDay = ref('')
const endDay = ref('')

const items = computed(() => {
  const presets = RANGE_PRESETS.map((p) => ({ value: p.id as string, title: t(p.labelKey) }))
  return allowCustom.value ? [...presets, { value: CUSTOM, title: t('dashboards.range.custom') }] : presets
})

const selected = computed(() => (customMode.value ? CUSTOM : props.preset))

const invalid = computed(
  () => customMode.value && !!startDay.value && !!endDay.value && !customRange(startDay.value, endDay.value, props.timeZone),
)

function fillDays(range: DateRange) {
  const days = rangeDays(range, props.timeZone)
  startDay.value = days?.start ?? ''
  endDay.value = days?.end ?? ''
}

function onSelect(value: string) {
  if (value === CUSTOM) {
    // Se parte de la ventana que ya se esta viendo, que es lo que se suele querer acotar.
    customMode.value = true
    fillDays(resolveRange(props.preset, props.timeZone))
    emitCustom()
    return
  }
  customMode.value = false
  if (allowCustom.value) emit('update:custom', null)
  emit('update:preset', value as RangePresetId)
}

function emitCustom() {
  const range = customRange(startDay.value, endDay.value, props.timeZone)
  if (range) emit('update:custom', range)
}

// Mantiene sincronizadas las dos copias del selector (escritorio y movil) de la misma vista, y
// vuelve al preajuste si el padre borra el rango (el historico lo hace al cerrarse).
watch(
  () => props.custom,
  (range) => {
    customMode.value = !!range
    if (!range) return
    fillDays(range)
  },
  { immediate: true },
)
</script>

<template>
  <div class="d-flex flex-wrap align-center ga-3" :class="{ 'flex-grow-1': block }">
    <VSelect
      :model-value="selected"
      :items="items"
      :label="t('dashboards.range.label')"
      min-width="190"
      :max-width="block ? undefined : 220"
      :class="{ 'flex-grow-1': block }"
      @update:model-value="onSelect"
    />
    <template v-if="customMode">
      <VTextField
        v-model="startDay"
        type="date"
        :label="t('dashboards.range.from')"
        :max="endDay || undefined"
        :error="invalid"
        min-width="170"
        max-width="190"
        @update:model-value="emitCustom"
      />
      <VTextField
        v-model="endDay"
        type="date"
        :label="t('dashboards.range.to')"
        :min="startDay || undefined"
        :error="invalid"
        :error-messages="invalid ? t('dashboards.range.invalid', { max: MAX_CUSTOM_DAYS }) : undefined"
        min-width="170"
        max-width="190"
        @update:model-value="emitCustom"
      />
    </template>
  </div>
</template>
