<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { t } from '@/i18n'

const props = defineProps<{ value: string; label?: string }>()

const done = ref(false)
let timer: number | undefined

async function copy() {
  try {
    await navigator.clipboard.writeText(props.value)
    done.value = true
    window.clearTimeout(timer)
    timer = window.setTimeout(() => (done.value = false), 1800)
  } catch {
    // Sin permiso de portapapeles no hay alternativa: el valor completo sigue visible en pantalla.
  }
}

onBeforeUnmount(() => window.clearTimeout(timer))
</script>

<template>
  <VTooltip :text="done ? t('entities.detail.copied') : label || t('entities.detail.copy')" location="top">
    <template #activator="{ props: tip }">
      <VBtn
        v-bind="tip"
        :icon="done ? 'mdi-check' : 'mdi-content-copy'"
        :color="done ? 'success' : undefined"
        variant="text"
        size="small"
        density="comfortable"
        class="flex-shrink-0"
        :aria-label="label || t('entities.detail.copy')"
        @click="copy"
      />
    </template>
  </VTooltip>
</template>
