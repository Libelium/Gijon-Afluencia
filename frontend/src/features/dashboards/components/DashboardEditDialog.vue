<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import type { Dashboard } from '@/types'
import { updateDashboard } from '../api/dashboards'

const props = defineProps<{ modelValue: boolean; dashboard: Dashboard }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [] }>()

const name = ref('')
const description = ref('')
const nameTouched = ref(false)
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
    name.value = props.dashboard.name
    description.value = props.dashboard.description ?? ''
    nameTouched.value = false
    error.value = null
  },
)

const dirty = computed(
  () => name.value !== props.dashboard.name || description.value !== (props.dashboard.description ?? ''),
)

const nameError = computed(() =>
  nameTouched.value && !name.value.trim() ? t('dashboards.create.nameRequired') : undefined,
)

const canSubmit = computed(() => !!name.value.trim() && dirty.value)

async function submit() {
  if (!canSubmit.value) return
  saving.value = true
  error.value = null
  try {
    await updateDashboard(props.dashboard.id, { name: name.value, description: description.value })
    open.value = false
    emit('saved')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

/**
 * Vuetify pone `role="dialog"` y `aria-modal` en el dialogo, pero no lo asocia con su titulo:
 * al abrirse, un lector de pantalla anuncia «dialogo» sin decir cual (WCAG 4.1.2, hallazgo
 * GDTIS-PT01-ACC-007). `useId` genera un identificador unico por instancia, que es lo que hace
 * falta cuando el mismo componente se monta varias veces en una pantalla.
 */
const titleId = useId()
</script>

<template>
  <VDialog v-model="open" max-width="560" :persistent="saving" :aria-labelledby="titleId">
    <VCard>
      <VCardTitle :id="titleId" class="text-h6 pa-4">{{ t('dashboards.edit.title') }}</VCardTitle>

      <VDivider />

      <VCardText class="pa-4">
        <div class="d-flex flex-column ga-4">
          <VTextField
            v-model="name"
            :label="t('dashboards.create.name')"
            autofocus
            maxlength="120"
            :error-messages="nameError"
            @blur="nameTouched = true"
          />

          <VTextarea
            v-model="description"
            :label="t('dashboards.create.description')"
            rows="2"
            auto-grow
            maxlength="255"
          />

          <VAlert v-if="error" type="error" role="alert" :text="error" />
        </div>
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
          {{ t('dashboards.edit.submit') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
