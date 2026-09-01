<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { useSessionStore } from '@/stores/session'
import { createDashboard, setDashboardTemplate, NAME_MIN_LENGTH } from '../api/dashboards'
import TemplatePicker from './TemplatePicker.vue'
import { typeIdOf } from '../templates/contract'
import type { TemplateKey } from '../templates/contract'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; created: [id: number] }>()

const session = useSessionStore()

type Mode = 'custom' | 'template'

const step = ref<1 | 2>(1)
const mode = ref<Mode>('custom')
const name = ref('')
const description = ref('')
const templateKey = ref<TemplateKey | null>(null)
const saving = ref(false)
const error = ref<string | null>(null)
/** Identificador ya creado cuando falla solo el segundo paso: no se vuelve a crear el panel. */
const createdId = ref<number | null>(null)
const nameTouched = ref(false)

const open = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

watch(
  () => props.modelValue,
  (value) => {
    if (!value) return
    step.value = 1
    mode.value = 'custom'
    name.value = ''
    description.value = ''
    templateKey.value = null
    error.value = null
    createdId.value = null
    nameTouched.value = false
  },
)

/**
 * El minimo de longitud lo impone el servidor. Si no se comprueba aqui, el unico aviso que
 * recibe quien escribe un nombre de dos letras es un 422 en el pie del dialogo.
 */
const nameTooShort = computed(() => {
  const value = name.value.trim()
  return value.length > 0 && value.length < NAME_MIN_LENGTH
})

const nameError = computed(() => {
  if (!nameTouched.value) return undefined
  if (!name.value.trim()) return t('dashboards.create.nameRequired')
  if (nameTooShort.value) return t('dashboards.create.nameTooShort', { min: NAME_MIN_LENGTH })
  return undefined
})

const canSubmit = computed(
  () =>
    !!name.value.trim() &&
    !nameTooShort.value &&
    (mode.value === 'custom' || !!templateKey.value),
)

async function submit() {
  if (!canSubmit.value) return
  saving.value = true
  error.value = null
  try {
    const id = createdId.value ?? (await createDashboard({
      name: name.value,
      description: description.value,
      timezone: session.timeZone,
      // El servidor distingue las dos naturalezas y de ella depende como se abre el panel.
      type: mode.value === 'template' ? 'Template' : 'Custom',
    }))
    createdId.value = id
    if (mode.value === 'template' && templateKey.value) {
      await setDashboardTemplate(id, typeIdOf(templateKey.value))
    }
    open.value = false
    emit('created', id)
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
  <VDialog v-model="open" scrollable :persistent="saving" :aria-labelledby="titleId">
    <VCard>
      <VCardTitle class="d-flex align-center ga-3 py-4">
        <span :id="titleId" class="text-h6">{{ t('dashboards.create.title') }}</span>
        <VSpacer />
        <span class="text-caption text-medium-emphasis">{{ t('dashboards.create.step', { current: step }) }}</span>
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
        <template v-if="step === 1">
          <div class="text-body-2 mb-4">{{ t('dashboards.create.kindQuestion') }}</div>
          <VRow>
            <VCol cols="12" sm="6">
              <VCard
                class="card-link h-100 pa-4 d-flex align-start ga-3"
                :variant="mode === 'custom' ? 'tonal' : 'flat'"
                :color="mode === 'custom' ? 'primary' : undefined"
                :style="mode === 'custom' ? { borderColor: 'rgb(var(--v-theme-primary))', borderWidth: '2px' } : undefined"
                role="radio"
                :aria-checked="mode === 'custom'"
                tabindex="0"
                @click="mode = 'custom'"
                @keydown.enter.prevent="mode = 'custom'"
                @keydown.space.prevent="mode = 'custom'"
              >
                <div class="icon-tile" style="width: 40px; height: 40px">
                  <VIcon icon="mdi-tune-variant" size="22" />
                </div>
                <div class="min-w-0 flex-grow-1">
                  <div class="text-subtitle-2 font-weight-medium">{{ t('dashboards.create.custom') }}</div>
                  <div class="text-body-2 text-medium-emphasis mt-1">{{ t('dashboards.create.customHelp') }}</div>
                </div>
                <VIcon v-if="mode === 'custom'" icon="mdi-check-circle" color="primary" size="20" class="flex-shrink-0" />
              </VCard>
            </VCol>

            <VCol cols="12" sm="6">
              <VCard
                class="card-link h-100 pa-4 d-flex align-start ga-3"
                :variant="mode === 'template' ? 'tonal' : 'flat'"
                :color="mode === 'template' ? 'primary' : undefined"
                :style="mode === 'template' ? { borderColor: 'rgb(var(--v-theme-primary))', borderWidth: '2px' } : undefined"
                role="radio"
                :aria-checked="mode === 'template'"
                tabindex="0"
                @click="mode = 'template'"
                @keydown.enter.prevent="mode = 'template'"
                @keydown.space.prevent="mode = 'template'"
              >
                <div class="icon-tile" style="width: 40px; height: 40px">
                  <VIcon icon="mdi-shape-outline" size="22" />
                </div>
                <div class="min-w-0 flex-grow-1">
                  <div class="text-subtitle-2 font-weight-medium">{{ t('dashboards.create.template') }}</div>
                  <div class="text-body-2 text-medium-emphasis mt-1">{{ t('dashboards.create.templateHelp') }}</div>
                </div>
                <VIcon v-if="mode === 'template'" icon="mdi-check-circle" color="primary" size="20" class="flex-shrink-0" />
              </VCard>
            </VCol>
          </VRow>
        </template>

        <div v-else class="d-flex flex-column ga-4">
          <VTextField
            v-model="name"
            :label="t('dashboards.create.name')"
            :hint="t('dashboards.create.nameHint')"
            persistent-hint
            autofocus
            :error-messages="nameError"
            maxlength="120"
            counter
            @blur="nameTouched = true"
          />

          <VTextarea
            v-model="description"
            :label="t('dashboards.create.description')"
            rows="2"
            auto-grow
            maxlength="255"
          />

          <VDivider v-if="mode === 'template'" />

          <TemplatePicker v-if="mode === 'template'" v-model="templateKey" />

          <!-- `role="alert"` para que el fallo se anuncie en cuanto aparece: sin el, quien usa
               lector de pantalla se queda esperando junto a un boton que no ha hecho nada
               visible (WCAG 4.1.3, hallazgo GDTIS-PT01-ACC-009). -->
          <VAlert
            v-if="error"
            type="error"
            role="alert"
            :title="createdId ? t('dashboards.create.templateFailed') : undefined"
            :text="error"
          />
        </div>
      </VCardText>

      <VDivider />

      <VCardActions class="pa-4 ga-3 justify-end">
        <VBtn variant="text" :disabled="saving" @click="open = false">{{ t('common.cancel') }}</VBtn>
        <VBtn v-if="step === 2" variant="tonal" :disabled="saving" prepend-icon="mdi-arrow-left" @click="step = 1">
          {{ t('dashboards.create.back') }}
        </VBtn>
        <VBtn v-if="step === 1" color="primary" append-icon="mdi-arrow-right" @click="step = 2">
          {{ t('dashboards.create.next') }}
        </VBtn>
        <VBtn
          v-else
          color="primary"
          :loading="saving"
          :disabled="!canSubmit"
          prepend-icon="mdi-plus"
          @click="submit"
        >
          {{ createdId ? t('dashboards.create.retryTemplate') : t('dashboards.create.submit') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
