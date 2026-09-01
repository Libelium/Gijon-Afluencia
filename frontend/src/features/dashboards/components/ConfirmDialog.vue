<script setup lang="ts">
import { computed, useId } from 'vue'
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

/**
 * Vuetify pone `role="dialog"` y `aria-modal` en el dialogo, pero no lo asocia con su titulo:
 * al abrirse, un lector de pantalla anuncia «dialogo» sin decir cual (WCAG 4.1.2, hallazgo
 * GDTIS-PT01-ACC-007). `useId` genera un identificador unico por instancia, que es lo que hace
 * falta cuando el mismo componente se monta varias veces en una pantalla.
 */
const titleId = useId()
</script>

<template>
  <VDialog v-model="open" max-width="480" :persistent="loading" :aria-labelledby="titleId">
    <VCard>
      <VCardTitle :id="titleId" class="text-h6 pa-4">{{ title }}</VCardTitle>

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
