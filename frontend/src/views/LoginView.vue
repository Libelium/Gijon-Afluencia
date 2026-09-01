<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { brand } from '@/brand'
import { t } from '@/i18n'
import { isAuthenticated, login, takeIntendedPath } from '@/auth/keycloak'
import { useCustomizationStore } from '@/stores/customization'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const route = useRoute()
const customization = useCustomizationStore()
const ui = useUiStore()

// La tarjeta se pinta sobre `surface`, que cambia con el tema: el logotipo tambien.
const logo = computed(() => customization.logo(ui.theme))

/**
 * Aqui no hay sesion, asi que no se sabe a que organizacion pertenece quien mira la pantalla.
 * Se resuelve igual que en el tema de Keycloak (`dynamicLogo.js`): con `?organization=<id>` si
 * viene en la URL, y si no con lo ultimo que se cacheo en este navegador. Sin ninguna de las dos
 * cosas se muestran las iniciales, que es el comportamiento de siempre.
 */
async function loadBranding() {
  const raw = route.query.organization
  const id = Number(Array.isArray(raw) ? raw[0] : raw)
  if (!Number.isInteger(id) || id <= 0) return
  try {
    await customization.loadPublic(id)
  } catch {
    // Organizacion inexistente o backend caido: se deja lo que ya hubiera.
  }
}

// Esta ruta es tambien el punto de retorno del proveedor de identidad.
onMounted(() => {
  if (isAuthenticated()) {
    router.replace(takeIntendedPath() ?? '/entidades')
    return
  }
  void loadBranding()
})
</script>

<template>
  <VCard max-width="424" class="w-100 pa-2">
    <VCardText class="text-center pt-8 pb-2">
      <img v-if="logo" :src="logo" :alt="brand.name" class="login-logo mb-4" />
      <VAvatar v-else color="primary" size="56" rounded="lg" class="mb-4">
        <span class="text-subtitle-1 font-weight-bold">{{ brand.shortName }}</span>
      </VAvatar>
      <h1 class="text-h6 font-weight-bold mb-1">{{ brand.name }}</h1>
      <p class="text-body-2 text-medium-emphasis mb-0">{{ brand.tagline }}</p>
    </VCardText>

    <VCardText class="text-center text-body-2 text-medium-emphasis py-6">
      {{ t('login.text') }}
    </VCardText>

    <VCardActions class="px-6 pb-6">
      <VBtn color="primary" size="large" block @click="login('/entidades')">
        {{ t('login.action') }}
      </VBtn>
    </VCardActions>
  </VCard>
</template>

<style scoped>
/* Alto acotado y ancho libre: el logotipo del login suele ser horizontal y no debe empujar
   la tarjeta ni recortarse. */
.login-logo {
  display: block;
  margin-inline: auto;
  max-inline-size: 100%;
  max-block-size: 72px;
  object-fit: contain;
}
</style>
