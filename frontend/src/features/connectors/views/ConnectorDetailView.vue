<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ApiError, errorMessage } from '@/api/http'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { formatDateTime, parseApiDateTime, relativeFromNow, urnTail } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import ConnectorErrorsCard from '../components/ConnectorErrorsCard.vue'
import ConnectorStatusChip from '../components/ConnectorStatusChip.vue'
import { getConnector, listConnectorErrors, setConnectorStatus } from '../api/connectors'
import { connectorStatus, formatTopic, isSnapshot, payloadTypeLabel } from '../lib/display'
import type { ConnectorDetail } from '../types'
import type { LogLine } from '@/types'

const route = useRoute()
const session = useSessionStore()

const connector = ref<ConnectorDetail | null>(null)
const lastError = ref<LogLine | null>(null)
const pending = ref(true)
const error = ref<string | null>(null)
const toggling = ref(false)
const toggleError = ref<string | null>(null)
const errorsCard = ref<InstanceType<typeof ConnectorErrorsCard> | null>(null)

const connectorId = computed(() => {
  const raw = Number(route.params.id)
  return Number.isInteger(raw) && raw > 0 ? raw : null
})

const title = computed(() => connector.value?.name?.trim() || t('connectors.detail.title'))
const missing = computed(() => !pending.value && !error.value && !connector.value)
const settings = computed(() => connector.value?.connector ?? null)
const enabled = computed(() => connector.value?.status === 'active')

const status = computed(() => (connector.value ? connectorStatus(connector.value) : null))

/**
 * El servidor desactiva solo un conector que falla seguido y deja escrito por que. Se avisa
 * cuando esta desactivado y su ultimo error es posterior a su ultimo envio correcto.
 */
const deactivatedByErrors = computed(() => {
  if (!connector.value || enabled.value || !lastError.value) return false
  const errorAt = parseApiDateTime(lastError.value.datetime)
  const sentAt = parseApiDateTime(connector.value.last_connection)
  return !!errorAt && (!sentAt || errorAt > sentAt)
})

const showLastError = computed(
  () => !!lastError.value && (status.value?.key === 'failing' || deactivatedByErrors.value),
)

async function loadLastError(id: number) {
  try {
    lastError.value = (await listConnectorErrors(id, 1, 1)).rows[0] ?? null
  } catch {
    lastError.value = null
  }
}

async function load() {
  const id = connectorId.value
  pending.value = true
  error.value = null
  toggleError.value = null

  if (id === null) {
    connector.value = null
    pending.value = false
    return
  }

  try {
    connector.value = await getConnector(id)
  } catch (e) {
    connector.value = null
    if (!(e instanceof ApiError && e.kind === 'notFound')) error.value = errorMessage(e)
  } finally {
    pending.value = false
  }

  if (connector.value) {
    void loadLastError(id)
    void errorsCard.value?.reload()
  }
}

async function toggle(value: boolean | null) {
  if (!connector.value || toggling.value) return
  toggling.value = true
  toggleError.value = null
  try {
    const updated = await setConnectorStatus(connector.value.id, value ? 'active' : 'inactive')
    connector.value = { ...connector.value, status: updated.status, retries: updated.retries }
  } catch (e) {
    toggleError.value = `${t('connectors.detail.toggleError')}: ${errorMessage(e)}`
  } finally {
    toggling.value = false
  }
}

watch(connectorId, () => void load(), { immediate: true })
</script>

<template>
  <PageHeader
    :title="title"
    icon="mdi-transit-connection-variant"
    back-to="/conectores"
  >
    <template #actions>
      <ConnectorStatusChip v-if="connector" :connector="connector" />

      <VBtn
        v-if="connector"
        :to="`/conectores/${connector.id}/editar`"
        variant="tonal"
        prepend-icon="mdi-pencil-outline"
      >
        {{ t('connectors.detail.edit') }}
      </VBtn>

      <VBtn
        icon="mdi-refresh"
        variant="tonal"
        :loading="pending"
        :aria-label="t('common.refresh')"
        :title="t('common.refresh')"
        @click="load()"
      />
    </template>
  </PageHeader>

  <StateBlock
    :loading="pending"
    :error="error"
    :empty="missing"
    :empty-text="t('connectors.detail.notFound')"
    empty-icon="mdi-transit-connection-variant"
    skeleton="card"
    @retry="load()"
  >
    <template #empty-action>
      <VBtn to="/conectores" variant="tonal">{{ t('common.back') }}</VBtn>
    </template>

    <div v-if="connector" class="d-flex flex-column ga-6">
      <VCard>
        <VCardText class="pa-4 pa-sm-6">
          <VSwitch
            :model-value="enabled"
            color="primary"
            hide-details
            inset
            :loading="toggling"
            :disabled="toggling"
            :label="t('connectors.detail.enabled')"
            @update:model-value="toggle"
          />
          <p class="text-body-2 text-medium-emphasis mt-2 mb-0">
            {{ t('connectors.detail.enabledHint') }}
          </p>

          <VAlert v-if="toggleError" type="error" :text="toggleError" role="alert" class="mt-4" />

          <VAlert
            v-if="deactivatedByErrors"
            type="warning"
            variant="tonal"
            :text="t('connectors.detail.deactivatedByErrors')"
            class="mt-4"
          />

          <VAlert v-if="showLastError && lastError" type="error" variant="tonal" class="mt-4">
            <div class="text-subtitle-2 mb-1">
              {{ t('connectors.detail.lastError') }} ·
              {{ formatDateTime(lastError.datetime, session.timeZone) }}
            </div>
            <!-- Texto plano: el mensaje viene del servidor sin sanear. -->
            <div class="text-body-2">{{ lastError.message }}</div>
          </VAlert>
        </VCardText>
      </VCard>

      <div class="d-flex flex-wrap ga-4">
        <VCard class="flex-1-1-0" style="min-width: 150px">
          <div class="pa-4">
            <div class="text-caption text-medium-emphasis mb-2">{{ t('connectors.kpi.lastSend') }}</div>
            <div class="text-h6 font-weight-medium text-truncate">
              {{
                connector.last_connection
                  ? relativeFromNow(connector.last_connection, session.timeZone)
                  : t('connectors.kpi.neverSent')
              }}
            </div>
            <div class="text-caption text-medium-emphasis mt-1">
              {{ formatDateTime(connector.last_connection, session.timeZone) }}
            </div>
          </div>
        </VCard>
        <VCard class="flex-1-1-0" style="min-width: 150px">
          <div class="pa-4">
            <div class="text-caption text-medium-emphasis mb-2">{{ t('connectors.kpi.format') }}</div>
            <div class="text-h6 font-weight-medium text-truncate">
              {{ payloadTypeLabel(settings?.payload_type) }}
            </div>
          </div>
        </VCard>
        <VCard class="flex-1-1-0" style="min-width: 150px">
          <div class="pa-4">
            <div class="text-caption text-medium-emphasis mb-2">{{ t('connectors.kpi.entities') }}</div>
            <div class="text-h6 font-weight-medium">{{ connector.entities?.length ?? 0 }}</div>
          </div>
        </VCard>
      </div>

      <VCard v-if="settings">
        <VCardText class="pa-4 pa-sm-6">
          <h2 class="text-subtitle-1 font-weight-medium mb-4">{{ t('connectors.settings.title') }}</h2>
          <dl class="settings text-body-2">
            <dt class="text-medium-emphasis">{{ t('connectors.settings.host') }}</dt>
            <dd>{{ settings.ipAddress }}:{{ settings.port }}</dd>

            <dt class="text-medium-emphasis">{{ t('connectors.settings.tls') }}</dt>
            <dd>
              {{ settings.ssl ? t('connectors.settings.yes') : t('connectors.settings.no') }}
              <template v-if="settings.ssl && settings.sslCert">
                ({{ t('connectors.settings.ownCa') }})
              </template>
            </dd>

            <dt class="text-medium-emphasis">{{ t('connectors.settings.user') }}</dt>
            <dd>{{ settings.username || '—' }}</dd>

            <dt class="text-medium-emphasis">{{ t('connectors.settings.password') }}</dt>
            <dd>
              {{
                settings.has_password
                  ? t('connectors.settings.passwordSet')
                  : t('connectors.settings.passwordUnset')
              }}
            </dd>

            <dt class="text-medium-emphasis">{{ t('connectors.settings.clientCert') }}</dt>
            <dd>
              {{
                !settings.clientCert
                  ? t('connectors.settings.clientCertUnset')
                  : settings.has_client_key
                    ? t('connectors.settings.clientCertSet')
                    : t('connectors.settings.clientCertNoKey')
              }}
            </dd>

            <dt class="text-medium-emphasis">{{ t('connectors.settings.clientId') }}</dt>
            <dd>{{ settings.clientId || t('connectors.settings.clientIdAuto') }}</dd>

            <dt class="text-medium-emphasis">{{ t('connectors.settings.topic') }}</dt>
            <dd><code>{{ formatTopic(settings.topicTemplate) }}</code></dd>

            <dt class="text-medium-emphasis">{{ t('connectors.settings.format') }}</dt>
            <dd>{{ payloadTypeLabel(settings.payload_type) }}</dd>

            <template v-if="!isSnapshot(settings.payload_type)">
              <dt class="text-medium-emphasis">{{ t('connectors.settings.readableNames') }}</dt>
              <dd>
                {{
                  connector.use_readable_names
                    ? t('connectors.settings.yes')
                    : t('connectors.settings.no')
                }}
              </dd>
            </template>

            <dt class="text-medium-emphasis">{{ t('connectors.settings.entities') }}</dt>
            <dd>
              <div v-if="connector.entities?.length" class="d-flex flex-wrap ga-2">
                <VChip v-for="entity in connector.entities" :key="entity.id" size="small" :title="entity.urn">
                  {{ urnTail(entity.urn) }}
                </VChip>
              </div>
              <span v-else>{{ t('connectors.settings.noEntities') }}</span>
            </dd>
          </dl>
        </VCardText>
      </VCard>

      <ConnectorErrorsCard ref="errorsCard" :connector-id="connector.id" />
    </div>
  </StateBlock>
</template>

<style scoped>
.settings {
  display: grid;
  grid-template-columns: minmax(140px, max-content) 1fr;
  gap: 12px 24px;
  margin: 0;
}

.settings dd {
  margin: 0;
  overflow-wrap: anywhere;
}

@media (max-width: 600px) {
  .settings {
    grid-template-columns: 1fr;
    gap: 4px;
  }

  .settings dd {
    margin-bottom: 12px;
  }
}
</style>
