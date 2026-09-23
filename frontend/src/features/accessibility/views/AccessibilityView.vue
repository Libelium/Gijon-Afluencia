<script setup lang="ts">
/**
 * Declaracion de accesibilidad. Contenido obligatorio del Real Decreto 1112/2018, y por eso
 * es una vista publica: tiene que poder leerse sin iniciar sesion.
 */
import { t } from '@/i18n'
import { formatDate } from '@/lib/format'
import { accessibilityContact } from '@/lib/legalConfig'

/**
 * Fecha en que se preparó esta declaracion. Es un dato del documento, no del despliegue, asi
 * que vive aqui, al lado del texto que fecha. En ISO para que sea inequivoca y se muestre con
 * el mismo formato que el resto de fechas de la aplicacion.
 */
const PREPARED_ON = '2026-09-04'

const contact = accessibilityContact()

const nonAccessible = [
  { title: t('accessibility.nonAccessible.tiles.title'), body: t('accessibility.nonAccessible.tiles.body') },
  { title: t('accessibility.nonAccessible.charts.title'), body: t('accessibility.nonAccessible.charts.body') },
  { title: t('accessibility.nonAccessible.scope.title'), body: t('accessibility.nonAccessible.scope.body') },
]
</script>

<template>
  <VContainer class="accessibility py-8">
    <h1 class="text-h5 font-weight-bold mb-4">{{ t('accessibility.title') }}</h1>

    <p class="text-body-2 mb-6">{{ t('accessibility.intro') }}</p>

    <h2 class="text-subtitle-1 font-weight-bold mb-2">{{ t('accessibility.compliance.title') }}</h2>
    <p class="text-body-2 mb-6">{{ t('accessibility.compliance.body') }}</p>

    <h2 class="text-subtitle-1 font-weight-bold mb-2">
      {{ t('accessibility.nonAccessible.title') }}
    </h2>
    <p class="text-body-2 mb-3">{{ t('accessibility.nonAccessible.intro') }}</p>
    <section v-for="item in nonAccessible" :key="item.title" class="mb-4">
      <h3 class="text-body-1 font-weight-medium mb-1">{{ item.title }}</h3>
      <p class="text-body-2 mb-0">{{ item.body }}</p>
    </section>

    <h2 class="text-subtitle-1 font-weight-bold mt-6 mb-2">
      {{ t('accessibility.preparation.title') }}
    </h2>
    <p class="text-body-2 mb-6">{{ t('accessibility.preparation.body', { date: formatDate(PREPARED_ON) }) }}</p>

    <h2 class="text-subtitle-1 font-weight-bold mb-2">{{ t('accessibility.feedback.title') }}</h2>
    <p class="text-body-2 mb-2">{{ t('accessibility.feedback.body') }}</p>
    <p v-if="contact" class="text-body-2 mb-6">
      {{ t('accessibility.feedback.contact', { contact }) }}
    </p>
    <VAlert v-else type="warning" variant="tonal" density="compact" class="mb-6 text-body-2">
      {{ t('accessibility.feedback.unset') }}
    </VAlert>

    <h2 class="text-subtitle-1 font-weight-bold mb-2">
      {{ t('accessibility.enforcement.title') }}
    </h2>
    <p class="text-body-2 mb-0">{{ t('accessibility.enforcement.body') }}</p>
  </VContainer>
</template>

<style scoped>
/* Texto legal: la medida corta se lee mejor que el ancho completo de la pantalla. */
.accessibility {
  max-inline-size: 70ch;
}
</style>
