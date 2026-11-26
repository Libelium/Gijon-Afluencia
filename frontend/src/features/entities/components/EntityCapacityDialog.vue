<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { ApiError, errorMessage } from '@/api/http'
import { t } from '@/i18n'
import type { Entity } from '@/types'
import { setMaxCapacity } from '../api/entities'

const props = defineProps<{ modelValue: boolean; entity: Entity; current: number | null }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [capacity: number | null] }>()

const text = ref('')
const touched = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

const open = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

watch(
  () => props.modelValue,
  (value) => {
    if (!value) return
    text.value = props.current === null ? '' : String(props.current)
    touched.value = false
    error.value = null
  },
)

/** Un aforo es un numero entero de personas mayor que cero. */
const parsed = computed(() => {
  const value = text.value.trim()
  return /^\d+$/.test(value) && Number(value) > 0 ? Number(value) : null
})
const inputError = computed(() =>
  touched.value && parsed.value === null ? t('entities.capacity.invalid') : undefined,
)
const canSubmit = computed(() => parsed.value !== null && parsed.value !== props.current)

async function save(capacity: number | null) {
  saving.value = true
  error.value = null
  try {
    await setMaxCapacity(props.entity.id, capacity)
    open.value = false
    emit('saved', capacity)
  } catch (e) {
    // El servidor responde el 403 en ingles: se sustituye por el aviso propio.
    error.value =
      e instanceof ApiError && e.kind === 'forbidden' ? t('entities.capacity.forbidden') : errorMessage(e)
  } finally {
    saving.value = false
  }
}

function submit() {
  touched.value = true
  if (canSubmit.value) void save(parsed.value)
}

/** Asocia el dialogo con su titulo para los lectores de pantalla (WCAG 4.1.2). */
const titleId = useId()
</script>

<template>
  <VDialog v-model="open" max-width="520" :persistent="saving" :aria-labelledby="titleId">
    <VCard>
      <VCardTitle :id="titleId" class="text-h6 pa-4">{{ t('entities.capacity.title') }}</VCardTitle>

      <VDivider />

      <VCardText class="pa-4">
        <form class="d-flex flex-column ga-4" @submit.prevent="submit">
          <VTextField
            v-model="text"
            :label="t('entities.capacity.label')"
            :hint="t('entities.capacity.hint')"
            persistent-hint
            autofocus
            inputmode="numeric"
            :error-messages="inputError"
            @blur="touched = true"
          />

          <VAlert v-if="error" type="error" role="alert" :text="error" />
        </form>
      </VCardText>

      <VDivider />

      <VCardActions class="pa-4 ga-3 flex-wrap">
        <VBtn
          v-if="current !== null"
          variant="text"
          color="error"
          :disabled="saving"
          :title="t('entities.capacity.clearHint')"
          @click="save(null)"
        >
          {{ t('entities.capacity.clear') }}
        </VBtn>
        <VSpacer />
        <VBtn variant="text" :disabled="saving" @click="open = false">{{ t('common.cancel') }}</VBtn>
        <VBtn
          color="primary"
          prepend-icon="mdi-content-save-outline"
          :loading="saving"
          :disabled="!canSubmit"
          @click="submit"
        >
          {{ t('common.save') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
