<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { contrast, ensureContrast, AA_TEXT, AA_NON_TEXT } from '@/customization/palette'
import { isHexColor } from '@/customization/preferences'

/**
 * Campo de color con lectura de contraste.
 *
 * Se muestra el contraste obtenido en ambos temas mientras se escribe, no despues de guardar:
 * quien personaliza necesita saber que el color que ha elegido cumple ANTES de aplicarlo a toda
 * la organizacion. Y si en oscuro hay que aclararlo, se dice a que valor, para que no parezca que
 * la aplicacion ignora lo que se ha puesto.
 */
const props = defineProps<{
  modelValue: string
  label: string
  hint?: string
  /** Los colores de acento no llevan texto encima, asi que les basta el minimo no textual. */
  nonText?: boolean
  lightSurface?: string
  darkSurface?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [string] }>()

const LIGHT = computed(() => props.lightSurface ?? '#FFFFFF')
const DARK = computed(() => props.darkSurface ?? '#1A1726')

const target = computed(() => (props.nonText ? AA_NON_TEXT : AA_TEXT))
const valid = computed(() => isHexColor(props.modelValue))

const lightRatio = computed(() => (valid.value ? contrast(props.modelValue, LIGHT.value) : 0))

/** En oscuro se informa del color YA ajustado, que es el que se va a ver de verdad. */
const darkValue = computed(() =>
  valid.value
    ? ensureContrast(props.modelValue, DARK.value, target.value, 'lighter')
    : props.modelValue,
)
const darkRatio = computed(() => (valid.value ? contrast(darkValue.value, DARK.value) : 0))
const darkAdjusted = computed(
  () => valid.value && darkValue.value.toUpperCase() !== props.modelValue.toUpperCase(),
)

const fmt = (n: number) => n.toFixed(2)

interface Reading {
  mode: string
  swatch: string
  surface: string
  ratio: number
}

const readings = computed<Reading[]>(() => [
  {
    mode: t('customization.color.light'),
    swatch: props.modelValue,
    surface: LIGHT.value,
    ratio: lightRatio.value,
  },
  {
    mode: t('customization.color.dark'),
    swatch: darkValue.value,
    surface: DARK.value,
    ratio: darkRatio.value,
  },
])
</script>

<template>
  <div>
    <VTextField
      :model-value="props.modelValue"
      :label="props.label"
      :hint="props.hint"
      persistent-hint
      spellcheck="false"
      autocapitalize="off"
      :error="props.modelValue !== '' && !valid"
      :error-messages="props.modelValue !== '' && !valid ? t('customization.color.invalid') : undefined"
      @update:model-value="emit('update:modelValue', $event)"
    >
      <template #prepend-inner>
        <!-- El selector nativo es lo unico que ofrece una rueda de color accesible sin
             dependencias; el texto sigue siendo editable a mano para pegar un hex exacto. -->
        <input
          type="color"
          class="color-swatch"
          :value="valid ? props.modelValue : '#000000'"
          :aria-label="props.label"
          @input="emit('update:modelValue', ($event.target as HTMLInputElement).value.toUpperCase())"
        />
      </template>
    </VTextField>

    <div v-if="valid" class="d-flex flex-wrap ga-2 mt-2">
      <VChip
        v-for="r in readings"
        :key="r.mode"
        :color="r.ratio >= target ? 'success' : 'error'"
        variant="tonal"
        size="small"
      >
        <span
          class="contrast-dot me-2"
          :style="{ background: r.swatch, borderColor: r.surface }"
          aria-hidden="true"
        />
        {{ r.mode }} · {{ fmt(r.ratio) }}:1
        <span class="ms-1">
          {{ r.ratio >= target ? t('customization.color.pass') : t('customization.color.fail') }}
        </span>
      </VChip>
    </div>

    <p v-if="darkAdjusted" class="text-caption text-medium-emphasis mt-2 mb-0">
      {{ t('customization.color.adjusted', { value: darkValue }) }}
    </p>
  </div>
</template>

<style scoped>
.color-swatch {
  inline-size: 28px;
  block-size: 28px;
  padding: 0;
  border: 1px solid rgb(var(--v-theme-outline-strong));
  border-radius: 6px;
  background: none;
  cursor: pointer;
}

.contrast-dot {
  display: inline-block;
  inline-size: 12px;
  block-size: 12px;
  border-radius: 50%;
  border: 2px solid;
}
</style>
