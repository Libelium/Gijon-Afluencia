<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage } from '@/api/http'
import PageHeader from '@/components/PageHeader.vue'
import StatTile from '@/components/StatTile.vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { formatDateTime, formatNumber, relativeFromNow, urnTail } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import type { Entity, EntityRef, Measure } from '@/types'
import { canUpdateEntity, getEntity, getEntityMeasures, latestTimestamp } from '../api/entities'
import EntityIdentityCard from '../components/EntityIdentityCard.vue'
import EntityRenameDialog from '../components/EntityRenameDialog.vue'
import EntityLocationCard from '../components/EntityLocationCard.vue'
import EntityMeasuresPanel from '../components/EntityMeasuresPanel.vue'
import { datamodelIcon } from '../lib/datamodel'
import { resolveEntityLocation } from '../lib/location'

const route = useRoute()
const session = useSessionStore()

const entity = ref<Entity | null>(null)
const pending = ref(true)
const error = ref<string | null>(null)

const measures = ref<Measure[]>([])
const measuresPending = ref(false)
const measuresError = ref<string | null>(null)
const readAt = ref<string | null>(null)

const canRename = ref(false)
const renaming = ref(false)
const snack = ref({ open: false, text: '' })

const entityId = computed(() => String(route.params.id ?? ''))

const entityRef = computed<EntityRef | null>(() => {
  const e = entity.value
  if (!e?.urn || !e.tenant || !e.scope) return null
  return { urn: e.urn, tenant: e.tenant, scope: e.scope }
})

const title = computed(
  () => entity.value?.name || urnTail(entity.value?.urn) || t('entities.detail.title'),
)

const headerIcon = computed(() => datamodelIcon(entity.value?.datamodel))

// La ubicacion puede venir de una medida, asi que se recalcula cuando llegan.
const location = computed(() => resolveEntityLocation(entity.value, measures.value))

const lastData = computed(
  () => latestTimestamp(measures.value) ?? entity.value?.time_last_data ?? null,
)

const lastDataHint = computed(() =>
  lastData.value ? formatDateTime(lastData.value, session.timeZone) : undefined,
)

const measuresCount = computed(() =>
  measuresPending.value && measures.value.length === 0
    ? t('common.noValue')
    : formatNumber(measures.value.length, 0),
)

const measuresHint = computed(() =>
  measuresPending.value ? t('entities.measures.loading') : undefined,
)

const devicesCount = computed(() => {
  const devices = entity.value?.devices
  return devices ? formatNumber(devices.length, 0) : t('common.noValue')
})

async function load() {
  pending.value = true
  error.value = null
  measures.value = []
  measuresError.value = null
  readAt.value = null
  canRename.value = false
  try {
    entity.value = await getEntity(entityId.value)
  } catch (e) {
    entity.value = null
    error.value = errorMessage(e)
  } finally {
    pending.value = false
  }
  if (entityRef.value) {
    void loadMeasures()
    void loadCanRename(entityRef.value)
  }
}

/** El boton solo se ofrece a quien puede usarlo. Si la consulta falla, no se ofrece. */
async function loadCanRename(target: EntityRef) {
  try {
    const allowed = await canUpdateEntity(target)
    if (entityRef.value?.urn === target.urn) canRename.value = allowed
  } catch {
    canRename.value = false
  }
}

function onRenamed(name: string) {
  if (entity.value) entity.value = { ...entity.value, name }
  snack.value = { open: true, text: t('entities.rename.saved') }
}

async function loadMeasures() {
  const ref_ = entityRef.value
  if (!ref_) return
  measuresPending.value = true
  measuresError.value = null
  try {
    measures.value = await getEntityMeasures(ref_)
    readAt.value = new Date().toISOString()
  } catch (e) {
    measures.value = []
    measuresError.value = errorMessage(e)
  } finally {
    measuresPending.value = false
  }
}

watch(entityId, () => void load(), { immediate: true })
</script>

<template>
  <PageHeader
    :title="title"
    :subtitle="entity?.datamodel"
    :icon="headerIcon"
    back-to="/entidades"
  >
    <template v-if="canRename" #actions>
      <VBtn variant="tonal" color="primary" prepend-icon="mdi-pencil-outline" @click="renaming = true">
        {{ t('entities.rename.action') }}
      </VBtn>
    </template>
  </PageHeader>

  <StateBlock
    :loading="pending"
    :error="error"
    :empty="!pending && !error && !entity"
    :empty-text="t('entities.detail.notFound')"
    empty-icon="mdi-help-circle-outline"
    skeleton="card"
    @retry="load()"
  >
    <div v-if="entity" class="d-flex flex-column ga-6">
      <div class="d-flex flex-wrap ga-4">
        <StatTile
          :label="t('entities.detail.lastData')"
          :value="relativeFromNow(lastData, session.timeZone)"
          :hint="lastDataHint"
          icon="mdi-clock-outline"
        />
        <StatTile
          :label="t('entities.detail.measuresCount')"
          :value="measuresCount"
          :hint="measuresHint"
          icon="mdi-gauge"
        />
        <StatTile
          :label="t('entities.detail.devices')"
          :value="devicesCount"
          icon="mdi-chip"
        />
        <StatTile
          :label="t('entities.detail.scope')"
          :value="entity.scope || t('common.noValue')"
          :hint="entity.tenant || undefined"
          icon="mdi-layers-outline"
        />
      </div>

      <div class="d-flex flex-wrap ga-6 align-stretch">
        <EntityIdentityCard :entity="entity" class="min-w-0" style="flex: 1 1 340px" />
        <EntityLocationCard
          :location="location"
          :loading="!location && measuresPending"
          class="min-w-0"
          style="flex: 1 1 340px"
        />
      </div>

      <EntityMeasuresPanel
        :measures="measures"
        :loading="measuresPending"
        :error="measuresError"
        :read-at="readAt"
        :time-zone="session.timeZone"
        :entity-ref="entityRef"
        @refresh="loadMeasures()"
      />
    </div>
  </StateBlock>

  <EntityRenameDialog v-if="entity" v-model="renaming" :entity="entity" @saved="onRenamed" />

  <VSnackbar v-model="snack.open" color="success" location="bottom">
    {{ snack.text }}
    <template #actions>
      <VBtn variant="text" @click="snack.open = false">{{ t('common.close') }}</VBtn>
    </template>
  </VSnackbar>
</template>
