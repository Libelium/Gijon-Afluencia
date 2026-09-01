<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'
import { t } from '@/i18n'
import BrandLogo from '@/components/BrandLogo.vue'
import AppFooter from '@/components/AppFooter.vue'
import { useUiStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { logout } from '@/auth/keycloak'

const ui = useUiStore()
const session = useSessionStore()
const route = useRoute()
const { mobile } = useDisplay()

const sections = [
  {
    label: 'app.nav.section.data',
    items: [
      { to: '/entidades', icon: 'mdi-access-point', label: 'app.nav.entities' },
      { to: '/mapa', icon: 'mdi-map-outline', label: 'app.nav.map' },
    ],
  },
  {
    label: 'app.nav.section.analysis',
    items: [
      { to: '/paneles', icon: 'mdi-view-dashboard-outline', label: 'app.nav.dashboards' },
      { to: '/alarmas', icon: 'mdi-bell-outline', label: 'app.nav.alarms' },
    ],
  },
]

const rail = computed(() => !mobile.value && ui.rail)
const pageTitle = computed(() => (route.meta.title as string | undefined) ?? '')

// En pantalla estrecha el menu es temporal y taparia el contenido: arranca cerrado
// y se cierra al navegar.
watch(mobile, (isMobile) => { ui.drawer = !isMobile }, { immediate: true })
watch(() => route.fullPath, () => { if (mobile.value) ui.drawer = false })

const initials = computed(() => {
  const name = session.displayName
  if (!name) return '·'
  const parts = name.replace(/@.*/, '').split(/[.\s_-]+/).filter(Boolean)
  return (parts[0]?.[0] ?? '').concat(parts[1]?.[0] ?? '').toUpperCase() || '·'
})

const MAIN_ID = 'contenido-principal'

/**
 * Enlace de salto al contenido (WCAG 2.4.1).
 *
 * Se mueve el foco a mano en lugar de dejar que el navegador siga el `href`: la aplicacion usa
 * enrutado por historial, asi que un salto nativo dejaria `#contenido-principal` pegado a la
 * URL y al recargar el enrutador recibiria una ruta que no es. El `href` se conserva porque es
 * lo que hace que el enlace se anuncie como tal y responda a Intro.
 */
function skipToContent(event: Event) {
  event.preventDefault()
  const main = document.getElementById(MAIN_ID)
  if (!main) return
  main.focus()
  main.scrollIntoView()
}
</script>

<template>
  <VApp>
    <!-- Primer elemento enfocable de la pagina: sin el, quien navega con teclado recorre el
         menu lateral entero y la barra superior antes de llegar al contenido, en CADA pantalla. -->
    <a class="skip-link" :href="`#${MAIN_ID}`" @click="skipToContent">
      {{ t('app.skipToContent') }}
    </a>

    <VNavigationDrawer
      v-model="ui.drawer"
      :rail="rail"
      :permanent="!mobile"
      :temporary="mobile"
      width="252"
    >
      <div class="px-4 py-5">
        <BrandLogo :compact="rail" :height="36" />
      </div>

      <VDivider />

      <template v-for="(section, index) in sections" :key="section.label">
        <VListSubheader v-if="!rail" class="text-caption font-weight-bold text-uppercase pt-4">
          {{ t(section.label) }}
        </VListSubheader>
        <VDivider v-else-if="index > 0" class="mx-3 my-2" />
        <VList nav class="px-2" :class="rail ? 'py-1' : 'pt-0'">
          <VListItem
            v-for="item in section.items"
            :key="item.to"
            :to="item.to"
            :prepend-icon="item.icon"
            :title="t(item.label)"
            color="primary"
          />
        </VList>
      </template>

      <template #append>
        <VDivider />
        <VList nav class="px-2 py-3">
          <VListItem
            to="/preferencias"
            prepend-icon="mdi-tune-variant"
            :title="t('app.nav.preferences')"
            color="primary"
          />
          <VListItem
            to="/personalizacion"
            prepend-icon="mdi-palette-outline"
            :title="t('app.nav.customization')"
            color="primary"
          />
        </VList>
      </template>
    </VNavigationDrawer>

    <VAppBar>
      <VBtn
        v-if="mobile"
        icon="mdi-menu"
        variant="text"
        :aria-label="t('app.nav.open')"
        @click="ui.drawer = !ui.drawer"
      />
      <VBtn
        v-else
        :icon="ui.rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
        variant="text"
        :aria-label="ui.rail ? t('app.nav.expand') : t('app.nav.collapse')"
        @click="ui.rail = !ui.rail"
      />

      <VToolbarTitle class="text-body-1 font-weight-medium ms-1">
        {{ pageTitle }}
      </VToolbarTitle>

      <VSpacer />

      <VBtn
        :icon="ui.theme === 'light' ? 'mdi-weather-night' : 'mdi-weather-sunny'"
        variant="text"
        :aria-label="ui.theme === 'light' ? t('app.theme.toDark') : t('app.theme.toLight')"
        @click="ui.toggleTheme()"
      />

      <VMenu location="bottom end">
        <template #activator="{ props }">
          <VBtn v-bind="props" variant="text" class="ms-1" :aria-label="t('app.user.session')">
            <VAvatar color="primary" size="32">
              <span class="text-caption font-weight-bold">{{ initials }}</span>
            </VAvatar>
          </VBtn>
        </template>
        <VCard min-width="248" class="pa-1">
          <div class="d-flex align-center ga-3 px-3 py-3">
            <VAvatar color="primary" size="38">
              <span class="text-caption font-weight-bold">{{ initials }}</span>
            </VAvatar>
            <div class="min-w-0">
              <div class="text-body-2 font-weight-medium text-truncate">
                {{ session.displayName || '—' }}
              </div>
              <div class="text-caption text-medium-emphasis text-truncate">
                {{ session.user?.organization?.name || '' }}
              </div>
            </div>
          </div>
          <VDivider />
          <VList density="comfortable" class="pt-1">
            <VListItem
              to="/preferencias"
              prepend-icon="mdi-tune-variant"
              :title="t('app.nav.preferences')"
            />
            <VListItem
              prepend-icon="mdi-logout"
              :title="t('app.user.logout')"
              @click="logout()"
            />
          </VList>
        </VCard>
      </VMenu>
    </VAppBar>

    <VMain>
      <!-- `tabindex="-1"` no anade el contenedor al recorrido de tabulacion: solo lo hace
           enfocable por programa, que es lo que necesita el enlace de salto. -->
      <VContainer
        :id="MAIN_ID"
        fluid
        tabindex="-1"
        class="pa-4 pa-md-6 main-content"
        :aria-label="t('app.mainContent')"
      >
        <RouterView />
      </VContainer>
    </VMain>

    <AppFooter />
  </VApp>
</template>

<style scoped>
/* Fuera de pantalla mientras no tiene el foco, y a la vista —sobre todo lo demas— en cuanto
   lo recibe. No se usa `display: none` a proposito: eso lo sacaria del recorrido de teclado,
   que es justo lo contrario de lo que se busca. */
.skip-link {
  position: fixed;
  inset-block-start: 8px;
  inset-inline-start: -9999px;
  z-index: 3000;
  padding: 10px 18px;
  border-radius: 8px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  font-weight: 600;
  text-decoration: none;
}

.skip-link:focus,
.skip-link:focus-visible {
  inset-inline-start: 8px;
  outline: 2px solid rgb(var(--v-theme-on-primary));
  outline-offset: 2px;
}

/* El contenedor recibe el foco por programa; el anillo del navegador ahi no aporta nada y
   solo dibuja un marco alrededor de toda la pagina. */
.main-content:focus {
  outline: none;
}
</style>
