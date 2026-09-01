<script setup lang="ts">
import { computed } from 'vue'
import { brand } from '@/brand'
import { useCustomizationStore } from '@/stores/customization'
import { useUiStore } from '@/stores/ui'

/**
 * Marca de la aplicacion: el logotipo de la organizacion si lo ha subido, y si no las iniciales
 * sobre el color primario, que es lo que habia antes.
 *
 * Hay dos imagenes porque un logotipo suele estar hecho para un fondo: el de Gijon es rojo sobre
 * claro y desaparece sobre el fondo oscuro, asi que la variante en blanco se sube como
 * `themeDarkIcon` y se elige por tema. Si solo hay una, se usa en los dos.
 */
const props = withDefaults(defineProps<{ compact?: boolean; height?: number }>(), {
  compact: false,
  height: 32,
})

const customization = useCustomizationStore()
const ui = useUiStore()

const src = computed(() => customization.logo(ui.theme))
</script>

<template>
  <div class="d-flex align-center ga-3 min-w-0">
    <img
      v-if="src"
      :src="src"
      :alt="brand.name"
      :style="{ height: `${props.height}px` }"
      class="brand-logo"
    />
    <VAvatar v-else color="primary" :size="props.height + 4" rounded="lg">
      <span class="text-caption font-weight-bold">{{ brand.shortName }}</span>
    </VAvatar>

    <div v-if="!props.compact" class="min-w-0">
      <div class="text-subtitle-2 font-weight-bold text-truncate">{{ brand.name }}</div>
      <div class="text-caption text-medium-emphasis text-truncate">{{ brand.tagline }}</div>
    </div>
  </div>
</template>

<style scoped>
/* Ancho libre y alto fijo: un logotipo puede ser cuadrado o muy alargado, y recortarlo o
   deformarlo es peor que dejarlo crecer a lo ancho dentro de su hueco. */
.brand-logo {
  width: auto;
  max-width: 160px;
  object-fit: contain;
}
</style>
