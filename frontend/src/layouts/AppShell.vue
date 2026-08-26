<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'
import { brand } from '@/brand'
import { t } from '@/i18n'
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
</script>

<template>
  <VApp>
    <VNavigationDrawer
      v-model="ui.drawer"
      :rail="rail"
      :permanent="!mobile"
      :temporary="mobile"
      width="252"
    >
      <div class="d-flex align-center ga-3 px-4 py-5">
        <VAvatar color="primary" size="36" rounded="lg">
          <span class="text-caption font-weight-bold">{{ brand.shortName }}</span>
        </VAvatar>
        <div v-if="!rail" class="min-w-0">
          <div class="text-subtitle-2 font-weight-bold text-truncate">{{ brand.name }}</div>
          <div class="text-caption text-medium-emphasis text-truncate">{{ brand.tagline }}</div>
        </div>
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
      <VContainer fluid class="pa-4 pa-md-6">
        <RouterView />
      </VContainer>
    </VMain>
  </VApp>
</template>
