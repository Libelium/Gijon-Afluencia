<script setup lang="ts">
import { computed, ref } from 'vue'
import { t } from '@/i18n'
import {
  MAX_IMAGE_BYTES,
  fileToDataUri,
  isAllowedImageType,
} from '@/customization/preferences'

/**
 * Subida de un logotipo, validando en el navegador lo mismo que valida el backend.
 *
 * La validacion de aqui no es la que protege —eso lo hace `ImagePreferenceHelper`, que además
 * comprueba los magic bytes— sino la que evita subir 3 MB para recibir un 422 sin explicacion.
 * El SVG se rechaza con su propio mensaje porque es el error que se comete solo: es el formato
 * natural para un logotipo, y no se admite justamente por poder llevar script dentro.
 */
const props = defineProps<{
  modelValue: string
  label: string
  hint?: string
  /** Fondo de la previsualizacion: un logotipo blanco no se ve sobre blanco. */
  preview?: 'light' | 'dark'
}>()

const emit = defineEmits<{ 'update:modelValue': [string] }>()

const input = ref<HTMLInputElement | null>(null)
const error = ref('')

const has = computed(() => props.modelValue.trim() !== '')

const formatSize = (bytes: number) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`

async function onPick(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  error.value = ''

  if (file.type === 'image/svg+xml' || /\.svg$/i.test(file.name)) {
    error.value = t('customization.image.isSvg')
  } else if (!isAllowedImageType(file.type)) {
    error.value = t('customization.image.badType')
  } else if (file.size > MAX_IMAGE_BYTES) {
    error.value = t('customization.image.tooLarge', { size: formatSize(file.size) })
  }

  if (error.value) {
    // Se limpia para que volver a elegir el MISMO fichero corregido dispare el evento.
    if (input.value) input.value.value = ''
    return
  }

  try {
    emit('update:modelValue', await fileToDataUri(file))
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    if (input.value) input.value.value = ''
  }
}
</script>

<template>
  <div>
    <div class="text-body-2 font-weight-medium mb-1">{{ props.label }}</div>
    <p v-if="props.hint" class="text-caption text-medium-emphasis mb-3">{{ props.hint }}</p>

    <div class="d-flex flex-wrap align-center ga-4">
      <div
        class="image-preview d-flex align-center justify-center"
        :class="props.preview === 'dark' ? 'image-preview--dark' : 'image-preview--light'"
      >
        <img v-if="has" :src="props.modelValue" :alt="props.label" />
        <span v-else class="text-caption text-medium-emphasis">
          {{ t('customization.image.none') }}
        </span>
      </div>

      <div class="d-flex flex-column ga-2">
        <VBtn
          variant="tonal"
          size="small"
          prepend-icon="mdi-image-plus"
          @click="input?.click()"
        >
          {{ has ? t('customization.image.replace') : t('customization.image.choose') }}
        </VBtn>
        <VBtn
          v-if="has"
          variant="text"
          size="small"
          color="error"
          prepend-icon="mdi-delete-outline"
          @click="emit('update:modelValue', '')"
        >
          {{ t('customization.image.remove') }}
        </VBtn>
      </div>
    </div>

    <input
      ref="input"
      type="file"
      accept="image/png,image/jpeg,image/webp,image/gif"
      class="d-none"
      @change="onPick"
    />

    <VAlert v-if="error" type="error" density="compact" class="mt-3" role="alert">{{ error }}</VAlert>
  </div>
</template>

<style scoped>
.image-preview {
  inline-size: 180px;
  block-size: 72px;
  padding: 8px;
  border: 1px solid rgb(var(--v-theme-outline));
  border-radius: 12px;
  overflow: hidden;
}

.image-preview img {
  max-inline-size: 100%;
  max-block-size: 100%;
  object-fit: contain;
}

.image-preview--light {
  background: #ffffff;
}

/* Fijo, no el color del tema: la gracia de esta caja es ver el logotipo sobre el fondo para el
   que se hizo, con independencia del tema que tenga puesto quien lo sube. */
.image-preview--dark {
  background: #1a1726;
}
</style>
