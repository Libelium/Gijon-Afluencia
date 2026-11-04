<script setup lang="ts">
import { computed, ref } from 'vue'
import { t } from '@/i18n'
import { avisoComplete, isEmail, newEmailAvisoDraft, type EmailAvisoDraft } from '../lib/draft'
import type { AlarmTrigger } from '../types'

const props = defineProps<{ modelValue: EmailAvisoDraft[] }>()
const emit = defineEmits<{ 'update:modelValue': [EmailAvisoDraft[]] }>()

// El alta de un aviso se compone aparte y solo entra en la lista cuando esta completo.
const draft = ref(newEmailAvisoDraft())

const triggerItems = computed(() => [
  { value: 'up' as AlarmTrigger, title: t('alarms.avisos.triggerUp') },
  { value: 'down' as AlarmTrigger, title: t('alarms.avisos.triggerDown') },
])

// El combobox deja en la lista lo que se teclea sin confirmar: se marca si algun correo no vale.
const invalidRecipients = computed(() => draft.value.to.filter((address) => !isEmail(address)))
const canAdd = computed(() => avisoComplete(draft.value))

function triggerLabel(trigger: AlarmTrigger): string {
  return trigger === 'down' ? t('alarms.avisos.triggerDown') : t('alarms.avisos.triggerUp')
}

function addAviso() {
  if (!canAdd.value) return
  emit('update:modelValue', [...props.modelValue, draft.value])
  draft.value = newEmailAvisoDraft()
}

function removeAviso(key: number) {
  emit('update:modelValue', props.modelValue.filter((aviso) => aviso.key !== key))
}
</script>

<template>
  <div>
    <h2 class="text-subtitle-1 font-weight-medium mb-1">{{ t('alarms.avisos.title') }}</h2>
    <p class="text-body-2 text-medium-emphasis mb-4">{{ t('alarms.avisos.hint') }}</p>

    <div v-if="modelValue.length" class="d-flex flex-column ga-3 mb-4">
      <VCard v-for="aviso in modelValue" :key="aviso.key" variant="outlined">
        <VCardText class="d-flex align-center ga-3 pa-3">
          <VIcon icon="mdi-email-outline" />
          <div class="flex-grow-1">
            <div class="text-body-2 font-weight-medium">{{ aviso.subject }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ aviso.to.join(', ') }} · {{ triggerLabel(aviso.trigger) }}
            </div>
          </div>
          <VBtn
            icon="mdi-delete-outline"
            variant="text"
            density="comfortable"
            :aria-label="t('alarms.avisos.remove')"
            :title="t('alarms.avisos.remove')"
            @click="removeAviso(aviso.key)"
          />
        </VCardText>
      </VCard>
    </div>
    <p v-else class="text-body-2 text-medium-emphasis mb-4">{{ t('alarms.avisos.empty') }}</p>

    <VCard variant="tonal">
      <VCardText class="d-flex flex-column ga-4 pa-4">
        <h3 class="text-subtitle-2 mb-0">{{ t('alarms.avisos.addTitle') }}</h3>

        <VCombobox
          v-model="draft.to"
          :label="t('alarms.avisos.recipients')"
          :hint="t('alarms.avisos.recipientsHint')"
          persistent-hint
          multiple
          chips
          closable-chips
          prepend-inner-icon="mdi-at"
          :error-messages="invalidRecipients.length ? [t('alarms.avisos.recipientsInvalid', { emails: invalidRecipients.join(', ') })] : []"
        />

        <VTextField v-model="draft.subject" :label="t('alarms.avisos.subject')" maxlength="200" />

        <VTextarea
          v-model="draft.body"
          :label="t('alarms.avisos.body')"
          :hint="t('alarms.avisos.bodyHint')"
          persistent-hint
          rows="3"
          auto-grow
        />

        <VSelect v-model="draft.trigger" :items="triggerItems" :label="t('alarms.avisos.trigger')" />

        <div class="d-flex justify-end">
          <VBtn variant="tonal" prepend-icon="mdi-plus" :disabled="!canAdd" @click="addAviso">
            {{ t('alarms.avisos.add') }}
          </VBtn>
        </div>
      </VCardText>
    </VCard>
  </div>
</template>
