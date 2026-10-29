<script setup lang="ts">
import { ref } from 'vue'
import { t } from '@/i18n'

/**
 * Certificado o clave en PEM: se pega en el area de texto o se carga de un fichero. El
 * fichero se lee en el navegador y solo viaja su contenido, igual que si se pegara.
 */
const props = defineProps<{
  modelValue: string
  label: string
  hint?: string
  errorMessages?: string
  accept?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [string] }>()

const files = ref<File[] | File | null>(null)
const readError = ref<string | undefined>()

async function load(value: File[] | File | null) {
  readError.value = undefined
  const file = Array.isArray(value) ? value[0] : value
  if (!file) return
  try {
    emit('update:modelValue', (await file.text()).trim())
  } catch {
    readError.value = t('connectors.form.pemReadError')
  } finally {
    files.value = null
  }
}
</script>

<template>
  <div class="d-flex flex-column ga-2">
    <VTextarea
      :model-value="props.modelValue"
      :label="label"
      :hint="hint"
      :persistent-hint="!!hint"
      :error-messages="readError ?? errorMessages"
      rows="3"
      auto-grow
      spellcheck="false"
      autocomplete="off"
      class="pem"
      @update:model-value="emit('update:modelValue', $event ?? '')"
    />
    <VFileInput
      v-model="files"
      :label="t('connectors.form.pemFromFile', { field: label })"
      :accept="accept ?? '.pem,.crt,.cer,.key'"
      prepend-icon="mdi-paperclip"
      density="compact"
      hide-details
      @update:model-value="load"
    />
  </div>
</template>

<style scoped>
.pem :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.8125rem;
}
</style>
