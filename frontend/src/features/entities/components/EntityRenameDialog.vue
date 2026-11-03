<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { ApiError, errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import type { Entity } from '@/types'
import { renameEntity } from '../api/entities'

const props = defineProps<{ modelValue: boolean; entity: Entity }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [name: string] }>()

const name = ref('')
const touched = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

const open = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

/** Sin nombre propio la plataforma muestra el final del identificador: es lo que se ve hoy. */
const current = computed(() => props.entity.name || urnTail(props.entity.urn))

watch(
  () => props.modelValue,
  (value) => {
    if (!value) return
    name.value = current.value
    touched.value = false
    error.value = null
  },
)

const trimmed = computed(() => name.value.trim())
const nameError = computed(() =>
  touched.value && !trimmed.value ? t('entities.rename.nameRequired') : undefined,
)
const canSubmit = computed(() => !!trimmed.value && trimmed.value !== current.value)

async function submit() {
  if (!canSubmit.value) return
  saving.value = true
  error.value = null
  try {
    await renameEntity(props.entity.id, trimmed.value)
    open.value = false
    emit('saved', trimmed.value)
  } catch (e) {
    // El servidor responde el 403 en ingles: se sustituye por el aviso propio.
    error.value =
      e instanceof ApiError && e.kind === 'forbidden' ? t('entities.rename.forbidden') : errorMessage(e)
  } finally {
    saving.value = false
  }
}

/** Asocia el dialogo con su titulo para los lectores de pantalla (WCAG 4.1.2). */
const titleId = useId()
</script>

<template>
  <VDialog v-model="open" max-width="520" :persistent="saving" :aria-labelledby="titleId">
    <VCard>
      <VCardTitle :id="titleId" class="text-h6 pa-4">{{ t('entities.rename.title') }}</VCardTitle>

      <VDivider />

      <VCardText class="pa-4">
        <form class="d-flex flex-column ga-4" @submit.prevent="submit">
          <VTextField
            v-model="name"
            :label="t('entities.rename.name')"
            :hint="t('entities.rename.hint')"
            persistent-hint
            autofocus
            maxlength="120"
            :error-messages="nameError"
            @blur="touched = true"
          />

          <VAlert v-if="error" type="error" role="alert" :text="error" />
        </form>
      </VCardText>

      <VDivider />

      <VCardActions class="pa-4 ga-3 justify-end">
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
