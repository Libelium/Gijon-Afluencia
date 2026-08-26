<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { brand } from '@/brand'
import { t } from '@/i18n'
import { isAuthenticated, login, takeIntendedPath } from '@/auth/keycloak'

const router = useRouter()

// Esta ruta es tambien el punto de retorno del proveedor de identidad.
onMounted(() => {
  if (isAuthenticated()) router.replace(takeIntendedPath() ?? '/entidades')
})
</script>

<template>
  <VCard max-width="424" class="w-100 pa-2">
    <VCardText class="text-center pt-8 pb-2">
      <VAvatar color="primary" size="56" rounded="lg" class="mb-4">
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
