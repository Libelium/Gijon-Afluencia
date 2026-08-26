<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    text?: string
    confirmText?: string
    /** Color del boton de confirmacion; 'error' para lo destructivo. */
    color?: string
    loading?: boolean
  }>(),
  { color: 'primary' },
)

const emit = defineEmits<{ 'update:modelValue': [boolean]; confirm: [] }>()

const open = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})
</script>

<template>
  <VDialog v-model="open" max-width="480" :persistent="loading">
    <VCard>
      <VCardTitle class="text-h6 pa-4">{{ title }}</VCardTitle>

      <VCardText v-if="text" class="pa-4 pt-0 text-body-2">{{ text }}</VCardText>

      <VCardActions class="pa-4 pt-0 ga-3 justify-end">
        <VBtn variant="text" :disabled="loading" @click="open = false">{{ t('common.cancel') }}</VBtn>
        <VBtn :color="color" :loading="loading" @click="$emit('confirm')">
          {{ confirmText || t('common.save') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
