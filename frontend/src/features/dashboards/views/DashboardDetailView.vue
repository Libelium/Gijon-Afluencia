<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { errorMessage } from '@/api/http'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { formatDateTime } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import type { Panel } from '@/types'
import type { DashboardDetail } from '../api/dashboards'
import { deleteDashboard, deletePanel, getDashboard } from '../api/dashboards'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import DashboardEditDialog from '../components/DashboardEditDialog.vue'
import PanelCard from '../components/PanelCard.vue'
import PanelCreateDialog from '../components/PanelCreateDialog.vue'
import TemplateEntitiesDialog from '../components/TemplateEntitiesDialog.vue'
import TemplateHost from '../components/TemplateHost.vue'
import { placePanels, type LayoutBreakpoint } from '../lib/layout'
import { DEFAULT_RANGE, RANGE_PRESETS, resolveRange, type DateRange, type RangePresetId } from '../lib/range'
import { datamodelNames, resolveTemplate } from '../templates/registry'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const { lgAndUp, mdAndUp, xs } = useDisplay()

const dashboard = ref<DashboardDetail | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const preset = ref<RangePresetId>(DEFAULT_RANGE)
const range = ref<DateRange>(resolveRange(DEFAULT_RANGE))
const reloadKey = ref(0)

const addOpen = ref(false)
const editOpen = ref(false)
const entitiesOpen = ref(false)
const pendingDelete = ref<Panel | null>(null)
const deleting = ref(false)
const dashboardDeleteOpen = ref(false)
const deletingDashboard = ref(false)
const snack = ref<{ open: boolean; text: string; color: string }>({ open: false, text: '', color: 'success' })

const id = computed(() => String(route.params.id ?? ''))
const timeZone = computed(() => dashboard.value?.timezone || session.timeZone)

const breakpoint = computed<LayoutBreakpoint>(() => (lgAndUp.value ? 'lg' : mdAndUp.value ? 'md' : 'sm'))

const placements = computed(() =>
  placePanels(dashboard.value?.panels ?? [], dashboard.value?.responsiveLayout, breakpoint.value),
)

const rangeItems = computed(() =>
  RANGE_PRESETS.map((option) => ({ value: option.id, title: t(option.labelKey) })),
)

const isTemplate = computed(() => !!dashboard.value?.templateType)
const descriptor = computed(() => resolveTemplate(dashboard.value?.templateType))
/** Solo se afirma que faltan entidades cuando el servidor declara la lista y esta vacia. */
const missingEntities = computed(
  () => isTemplate.value && !!dashboard.value?.templateEntitiesKnown && dashboard.value.templateEntityIds.length === 0,
)

function notify(text: string, color = 'success') {
  snack.value = { open: true, text, color }
}

/** Ventana efectiva que se esta dibujando: sin ella un preajuste relativo no dice que periodo cubre. */
const rangeCaption = computed(() =>
  placements.value.length
    ? t('dashboards.detail.rangeCaption', {
        start: formatDateTime(range.value.start, timeZone.value),
        end: formatDateTime(range.value.end, timeZone.value),
      })
    : '',
)

const panelCount = computed(() => {
  const total = placements.value.length
  if (loading.value || error.value || !total) return undefined
  return total === 1 ? t('dashboards.card.onePanel') : t('dashboards.card.panels', { count: total })
})

const headerCount = computed(() => (isTemplate.value ? descriptor.value?.label : panelCount.value))

function applyRange() {
  range.value = resolveRange(preset.value, timeZone.value)
}

function refresh() {
  applyRange()
  reloadKey.value += 1
}

async function load() {
  loading.value = true
  error.value = null
  try {
    dashboard.value = await getDashboard(id.value)
    applyRange()
  } catch (e) {
    error.value = errorMessage(e)
    dashboard.value = null
  } finally {
    loading.value = false
  }
}

async function confirmDelete() {
  const panel = pendingDelete.value
  if (!panel) return
  deleting.value = true
  try {
    await deletePanel(panel.id)
    pendingDelete.value = null
    await load()
    notify(t('dashboards.detail.panelDeleted'))
  } catch (e) {
    notify(errorMessage(e), 'error')
  } finally {
    deleting.value = false
  }
}

/**
 * Al borrar el panel se vuelve al listado: quedarse aqui dejaria la pantalla mostrando algo que
 * ya no existe, y el siguiente refresco daria un 404. El aviso de exito no se traslada al
 * listado a proposito: la ausencia del panel en la lista ya es la confirmacion.
 */
async function confirmDeleteDashboard() {
  const current = dashboard.value
  if (!current) return
  deletingDashboard.value = true
  try {
    await deleteDashboard(current.id)
    dashboardDeleteOpen.value = false
    await router.replace('/paneles')
  } catch (e) {
    notify(errorMessage(e), 'error')
  } finally {
    deletingDashboard.value = false
  }
}

async function onPanelCreated() {
  await load()
  notify(t('dashboards.detail.panelCreated'))
}

async function onEdited() {
  await load()
  notify(t('dashboards.detail.saved'))
}

async function onEntitiesSaved() {
  await load()
  notify(t('dashboards.detail.entitiesSaved'))
}

watch([preset, timeZone], applyRange)
watch(id, load)
onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      :title="dashboard?.name || t('dashboards.detail.title')"
      :count="headerCount"
      :subtitle="dashboard?.description"
      icon="mdi-view-dashboard-outline"
      back-to="/paneles"
    >
      <template #actions>
        <template v-if="!isTemplate && !xs">
          <VSelect
            v-model="preset"
            :items="rangeItems"
            :label="t('dashboards.range.label')"
            min-width="190"
            max-width="220"
          />
          <VBtn
            icon="mdi-refresh"
            variant="tonal"
            :loading="loading"
            :aria-label="t('common.refresh')"
            :title="t('common.refresh')"
            @click="refresh"
          />
        </template>

        <VBtn
          v-if="!isTemplate"
          color="primary"
          prepend-icon="mdi-plus"
          :disabled="!dashboard"
          @click="addOpen = true"
        >
          {{ t('dashboards.detail.addPanel') }}
        </VBtn>

        <VBtn
          v-if="isTemplate"
          variant="tonal"
          color="primary"
          :disabled="!dashboard"
          prepend-icon="mdi-map-marker-multiple-outline"
          @click="entitiesOpen = true"
        >
          {{ t('dashboards.detail.entities') }}
        </VBtn>

        <VMenu>
          <template #activator="{ props: menuProps }">
            <VBtn
              v-bind="menuProps"
              icon="mdi-dots-vertical"
              variant="text"
              density="comfortable"
              :disabled="!dashboard"
              :aria-label="t('dashboards.detail.actions')"
            />
          </template>
          <VList>
            <VListItem
              prepend-icon="mdi-pencil-outline"
              :title="t('dashboards.detail.edit')"
              @click="editOpen = true"
            />
            <VDivider class="my-1" />
            <VListItem
              prepend-icon="mdi-delete-outline"
              :title="t('dashboards.detail.delete')"
              base-color="error"
              @click="dashboardDeleteOpen = true"
            />
          </VList>
        </VMenu>
      </template>
    </PageHeader>

    <!-- A 390 px el selector no cabe junto al titulo: pasa a su propia fila. -->
    <div v-if="xs && !isTemplate" class="d-flex align-center ga-3 mb-4">
      <VSelect
        v-model="preset"
        :items="rangeItems"
        :label="t('dashboards.range.label')"
        class="flex-grow-1"
      />
      <VBtn
        icon="mdi-refresh"
        variant="tonal"
        :loading="loading"
        :aria-label="t('common.refresh')"
        :title="t('common.refresh')"
        @click="refresh"
      />
    </div>

    <div v-if="!isTemplate && rangeCaption" class="text-caption text-medium-emphasis mb-6">{{ rangeCaption }}</div>

    <StateBlock :loading="loading" :error="error" :empty="false" skeleton="card" @retry="load">
      <template v-if="dashboard">
        <template v-if="isTemplate">
          <VCard v-if="missingEntities" class="pa-6 mb-6">
            <div class="d-flex flex-column align-center text-center ga-3">
              <div class="icon-tile" style="width: 56px; height: 56px">
                <VIcon icon="mdi-map-marker-off-outline" size="28" />
              </div>
              <div class="text-subtitle-1 font-weight-medium">{{ t('dashboards.detail.noEntities') }}</div>
              <div class="text-body-2 text-medium-emphasis">{{ t('dashboards.detail.noEntitiesHint') }}</div>
              <VBtn color="primary" prepend-icon="mdi-plus" class="mt-2" @click="entitiesOpen = true">
                {{ t('dashboards.detail.assignEntities') }}
              </VBtn>
            </div>
          </VCard>

          <TemplateHost v-else :dashboard="dashboard" :type-id="dashboard.templateType ?? null" />
        </template>

        <template v-else>
          <StateBlock
            :empty="!placements.length"
            :empty-text="t('dashboards.detail.noPanels')"
            :empty-hint="t('dashboards.detail.noPanelsHint')"
            empty-icon="mdi-chart-box-outline"
          >
            <template #empty-action>
              <VBtn color="primary" prepend-icon="mdi-plus" @click="addOpen = true">
                {{ t('dashboards.detail.addPanel') }}
              </VBtn>
            </template>

            <VRow>
              <VCol
                v-for="placement in placements"
                :key="placement.key"
                cols="12"
                :md="placement.span"
                :offset-md="placement.offset"
              >
                <PanelCard
                  :panel="placement.panel"
                  :range="range"
                  :height="placement.height"
                  :time-zone="timeZone"
                  :reload-key="reloadKey"
                  removable
                  @remove="pendingDelete = placement.panel"
                />
              </VCol>
            </VRow>
          </StateBlock>
        </template>
      </template>
    </StateBlock>

    <PanelCreateDialog
      v-if="dashboard && !isTemplate"
      v-model="addOpen"
      :dashboard-id="dashboard.id"
      @created="onPanelCreated"
    />

    <DashboardEditDialog v-if="dashboard" v-model="editOpen" :dashboard="dashboard" @saved="onEdited" />

    <TemplateEntitiesDialog
      v-if="dashboard && isTemplate"
      v-model="entitiesOpen"
      :dashboard-id="dashboard.id"
      :selected="dashboard.templateEntityIds"
      :selection-known="dashboard.templateEntitiesKnown"
      :datamodels="descriptor ? datamodelNames(descriptor) : []"
      @saved="onEntitiesSaved"
    />

    <ConfirmDialog
      :model-value="!!pendingDelete"
      :title="t('dashboards.panel.deleteTitle')"
      :text="t('dashboards.panel.deleteText', { title: pendingDelete?.title || t('dashboards.panel.untitled') })"
      :confirm-text="t('dashboards.panel.deleteConfirm')"
      color="error"
      :loading="deleting"
      @update:model-value="(v) => { if (!v) pendingDelete = null }"
      @confirm="confirmDelete"
    />

    <ConfirmDialog
      v-model="dashboardDeleteOpen"
      :title="t('dashboards.detail.deleteTitle')"
      :text="t('dashboards.detail.deleteText', { name: dashboard?.name || t('dashboards.detail.title') })"
      :confirm-text="t('dashboards.detail.deleteConfirm')"
      color="error"
      :loading="deletingDashboard"
      @confirm="confirmDeleteDashboard"
    />

    <VSnackbar v-model="snack.open" :color="snack.color" :timeout="4000" location="bottom">
      {{ snack.text }}
      <template #actions>
        <VBtn variant="text" @click="snack.open = false">{{ t('common.close') }}</VBtn>
      </template>
    </VSnackbar>
  </div>
</template>
