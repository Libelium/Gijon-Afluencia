<script setup lang="ts">
import { computed, onBeforeUnmount, ref, useId, watch } from 'vue'
import { t } from '@/i18n'
import { formatDate, formatDateTime } from '@/lib/format'

const props = defineProps<{
  /** Marcas ISO de cada hora, en orden. */
  steps: string[]
  /** Posicion de la hora mostrada, o null para el resumen (total del periodo, o ahora). */
  modelValue: number | null
  /** Texto del boton que vuelve al resumen. */
  summaryLabel: string
  timeZone?: string
  /** Pasos de un dia: se rotulan con la fecha, sin hora. */
  daily?: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [value: number | null] }>()

/** Ritmo de la reproduccion: lo bastante lento para leer la hora de cada paso. */
const PLAY_INTERVAL_MS = 700

const id = useId()
const playing = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

const last = computed(() => props.steps.length - 1)
const label = computed(() =>
  props.modelValue === null
    ? props.summaryLabel
    : (props.daily ? formatDate : formatDateTime)(props.steps[props.modelValue], props.timeZone),
)

function stop() {
  playing.value = false
  if (timer) clearInterval(timer)
  timer = undefined
}

function play() {
  if (!props.steps.length) return
  playing.value = true
  if (props.modelValue === null || props.modelValue >= last.value) emit('update:modelValue', 0)
  timer = setInterval(() => {
    const next = (props.modelValue ?? -1) + 1
    if (next > last.value) stop()
    else emit('update:modelValue', next)
  }, PLAY_INTERVAL_MS)
}

function onInput(event: Event) {
  stop()
  emit('update:modelValue', Number((event.target as HTMLInputElement).value))
}

function showSummary() {
  stop()
  emit('update:modelValue', null)
}

// Otra carga cambia las horas: la posicion anterior ya no significa lo mismo.
watch(
  () => props.steps,
  () => {
    stop()
    if (props.modelValue !== null) emit('update:modelValue', null)
  },
)

onBeforeUnmount(stop)
</script>

<template>
  <div class="hour-timeline" role="group" :aria-label="t('templates.common.timeline')">
    <div class="d-flex flex-wrap align-center ga-2">
      <VBtn
        size="small"
        :variant="modelValue === null ? 'flat' : 'tonal'"
        :color="modelValue === null ? 'primary' : undefined"
        :aria-pressed="modelValue === null"
        @click="showSummary"
      >
        {{ summaryLabel }}
      </VBtn>
      <VBtn
        size="small"
        variant="text"
        :disabled="!steps.length"
        :prepend-icon="playing ? 'mdi-pause' : 'mdi-play'"
        @click="playing ? stop() : play()"
      >
        {{ playing ? t('templates.common.timelinePause') : t('templates.common.timelinePlay') }}
      </VBtn>
      <VSpacer />
      <span class="text-body-2 font-weight-medium">{{ label }}</span>
    </div>
    <template v-if="steps.length">
      <label :for="id" class="d-sr-only">{{ t('templates.common.timelineHour') }}</label>
      <input
        :id="id"
        class="hour-timeline__range"
        type="range"
        min="0"
        :max="last"
        step="1"
        :value="modelValue ?? last"
        :aria-valuetext="modelValue === null ? summaryLabel : label"
        @input="onInput"
      />
    </template>
    <div v-else class="text-caption text-medium-emphasis mt-1">{{ t('templates.common.timelineNoHours') }}</div>
  </div>
</template>

<style scoped>
.hour-timeline__range {
  inline-size: 100%;
  accent-color: rgb(var(--v-theme-primary));
  cursor: pointer;
}
</style>
