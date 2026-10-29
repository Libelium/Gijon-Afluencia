<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, errorMessage } from '@/api/http'
import { t } from '@/i18n'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import ConnectorEntitiesPicker from '../components/ConnectorEntitiesPicker.vue'
import PemField from '../components/PemField.vue'
import {
  createConnector,
  getConnector,
  linkEntities,
  setConnectorStatus,
  updateConnector,
} from '../api/connectors'
import {
  clientCertificateErrors,
  formatTopic,
  hostError,
  isPayloadType,
  isSnapshot,
  parseTopic,
  payloadTypeOptions,
  portError,
  topicError,
  topicVariables,
} from '../lib/display'
import type { LinkedEntity, MqttConnectorInput, PayloadType } from '../types'

const route = useRoute()
const router = useRouter()

/** Con id en la ruta se edita; sin el, se da de alta. */
const connectorId = computed(() => {
  const raw = Number(route.params.id)
  return Number.isInteger(raw) && raw > 0 ? raw : null
})
const editing = computed(() => connectorId.value !== null)

const name = ref('')
const enabled = ref(true)
const host = ref('')
const port = ref<number | string>(8883)
const ssl = ref(true)
const sslCert = ref('')
const clientCert = ref('')
const clientKey = ref('')
const hasClientKey = ref(false)
const username = ref('')
const password = ref('')
const hasPassword = ref(false)
const clientId = ref('')
const payloadType = ref<PayloadType>('occupancy_readings')
const topic = ref('')
const readableNames = ref(false)
const entities = ref<LinkedEntity[]>([])
/** La configuracion de campos del formato original no se edita aqui: se devuelve tal cual. */
const legacyConfig = ref<unknown>(undefined)

const touched = ref(false)
const loading = ref(false)
const loadError = ref<string | null>(null)
const missing = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

const formatItems = payloadTypeOptions()

const nameError = computed(() =>
  touched.value && !name.value.trim() ? t('connectors.form.nameRequired') : undefined,
)
const hostMessage = computed(() => (touched.value ? hostError(host.value) : undefined))
const portMessage = computed(() => (touched.value ? portError(port.value) : undefined))
const topicMessage = computed(() =>
  touched.value || topic.value ? topicError(topic.value, payloadType.value) : undefined,
)

const topicHint = computed(() => {
  const variables = topicVariables(payloadType.value)
  return variables.length
    ? t('connectors.form.topicHint', { variables: variables.map((v) => `{${v}}`).join(', ') })
    : t('connectors.form.topicHintStatic')
})

const entitiesHint = computed(() =>
  isSnapshot(payloadType.value)
    ? t(`connectors.form.entitiesHint.${payloadType.value}`)
    : t('connectors.form.entitiesHint.default'),
)

const certificateErrors = computed(() =>
  clientCertificateErrors(clientCert.value, clientKey.value, hasClientKey.value, ssl.value),
)
const certificateMessages = computed(() => (touched.value ? certificateErrors.value : {}))

const valid = computed(
  () =>
    !!name.value.trim() &&
    !certificateErrors.value.certificate &&
    !certificateErrors.value.key &&
    !hostError(host.value) &&
    !portError(port.value) &&
    !topicError(topic.value, payloadType.value),
)

/** El puerto habitual cambia con TLS: se ajusta solo mientras no se haya tocado a mano. */
watch(ssl, (value) => {
  if (String(port.value) === '8883' || String(port.value) === '1883') port.value = value ? 8883 : 1883
})

async function load() {
  const id = connectorId.value
  if (id === null) return
  loading.value = true
  loadError.value = null
  missing.value = false
  try {
    const detail = await getConnector(id)
    const settings = detail.connector
    name.value = detail.name ?? ''
    enabled.value = detail.status === 'active'
    readableNames.value = !!detail.use_readable_names
    entities.value = detail.entities ?? []
    if (settings) {
      host.value = settings.ipAddress ?? ''
      port.value = settings.port ?? 8883
      ssl.value = !!settings.ssl
      sslCert.value = settings.sslCert ?? ''
      clientCert.value = settings.clientCert ?? ''
      hasClientKey.value = !!settings.has_client_key
      username.value = settings.username ?? ''
      hasPassword.value = !!settings.has_password
      clientId.value = settings.clientId ?? ''
      topic.value = formatTopic(settings.topicTemplate)
      if (isPayloadType(settings.payload_type)) payloadType.value = settings.payload_type
      legacyConfig.value = settings.payload_config
    }
  } catch (e) {
    if (e instanceof ApiError && e.kind === 'notFound') missing.value = true
    else loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

watch(connectorId, () => void load(), { immediate: true })

function payload(): MqttConnectorInput {
  return {
    name: name.value.trim(),
    use_readable_names: !isSnapshot(payloadType.value) && readableNames.value,
    ipAddress: host.value.trim(),
    port: Number(port.value),
    username: username.value.trim() || null,
    // Vacia no se envia: al editar, el servidor conserva la contrasena que ya tenia.
    ...(password.value ? { password: password.value } : {}),
    clientId: clientId.value.trim() || null,
    ssl: ssl.value,
    sslCert: ssl.value && sslCert.value.trim() ? sslCert.value.trim() : null,
    // Sin certificado el servidor borra los dos; la clave vacia conserva la guardada.
    clientCert: ssl.value && clientCert.value.trim() ? clientCert.value.trim() : null,
    ...(ssl.value && clientKey.value.trim() ? { clientKey: clientKey.value.trim() } : {}),
    topicTemplate: parseTopic(topic.value.trim()),
    payload_type: payloadType.value,
    // El servidor solo admite payload_config con el formato original.
    ...(payloadType.value === 'legacy' && Array.isArray(legacyConfig.value)
      ? { payload_config: legacyConfig.value }
      : {}),
  }
}

async function submit() {
  touched.value = true
  if (!valid.value || saving.value) return
  saving.value = true
  error.value = null

  let id = connectorId.value
  try {
    const saved = id === null ? await createConnector(payload()) : await updateConnector(id, payload())
    id = saved.id
    // El alta lo deja activo: solo hace falta una llamada mas si se quiere desactivado, o si
    // al editar se ha cambiado el estado.
    const wanted = enabled.value ? 'active' : 'inactive'
    if (saved.status !== wanted) await setConnectorStatus(id, wanted)
  } catch (e) {
    error.value = errorMessage(e)
    saving.value = false
    return
  }

  try {
    await linkEntities(id, entities.value.map((entity) => entity.id))
  } catch (e) {
    // El conector ya existe: se dice que falta la asociacion en lugar de perder lo guardado.
    error.value = t('connectors.form.linkError', { error: errorMessage(e) })
    saving.value = false
    if (connectorId.value === null) await router.replace(`/conectores/${id}/editar`)
    return
  }

  saving.value = false
  await router.push(`/conectores/${id}`)
}
</script>

<template>
  <PageHeader
    :title="editing ? t('connectors.form.titleEdit') : t('connectors.form.titleNew')"
    :subtitle="t('connectors.form.subtitle')"
    icon="mdi-transit-connection-variant"
    :back-to="editing ? `/conectores/${connectorId}` : '/conectores'"
  />

  <StateBlock
    :loading="loading"
    :error="loadError"
    :empty="missing"
    :empty-text="t('connectors.detail.notFound')"
    empty-icon="mdi-transit-connection-variant"
    skeleton="card"
    @retry="load()"
  >
    <form class="d-flex flex-column ga-4" style="max-width: 900px" novalidate @submit.prevent="submit">
      <VCard>
        <VCardText class="pa-4 pa-sm-6">
          <h2 class="text-subtitle-1 font-weight-medium mb-4">{{ t('connectors.form.general') }}</h2>
          <div class="d-flex flex-column ga-4">
            <VTextField
              v-model="name"
              :label="t('connectors.form.name')"
              maxlength="255"
              :error-messages="nameError"
            />
            <VSwitch
              v-model="enabled"
              color="primary"
              inset
              hide-details
              :label="t('connectors.form.enabled')"
            />
          </div>
        </VCardText>
      </VCard>

      <VCard>
        <VCardText class="pa-4 pa-sm-6">
          <h2 class="text-subtitle-1 font-weight-medium mb-4">{{ t('connectors.form.broker') }}</h2>
          <VRow>
            <VCol cols="12" sm="8">
              <VTextField
                v-model="host"
                :label="t('connectors.form.host')"
                :hint="t('connectors.form.hostHint')"
                persistent-hint
                autocomplete="off"
                spellcheck="false"
                :error-messages="hostMessage"
              />
            </VCol>
            <VCol cols="12" sm="4">
              <VTextField
                v-model="port"
                type="number"
                min="1"
                max="65535"
                :label="t('connectors.form.port')"
                :error-messages="portMessage"
              />
            </VCol>
            <VCol cols="12">
              <VSwitch v-model="ssl" color="primary" inset hide-details :label="t('connectors.form.ssl')" />
            </VCol>
            <VCol v-if="ssl" cols="12">
              <PemField
                v-model="sslCert"
                :label="t('connectors.form.sslCert')"
                :hint="t('connectors.form.sslCertHint')"
              />
            </VCol>
            <template v-if="ssl">
              <VCol cols="12">
                <h3 class="text-subtitle-2 mb-1">{{ t('connectors.form.clientAuth') }}</h3>
                <p class="text-body-2 text-medium-emphasis mb-0">{{ t('connectors.form.clientAuthHint') }}</p>
              </VCol>
              <VCol cols="12" md="6">
                <PemField
                  v-model="clientCert"
                  :label="t('connectors.form.clientCert')"
                  :error-messages="certificateMessages.certificate"
                />
              </VCol>
              <VCol cols="12" md="6">
                <PemField
                  v-model="clientKey"
                  :label="t('connectors.form.clientKey')"
                  :hint="hasClientKey ? t('connectors.form.clientKeyKeep') : t('connectors.form.clientKeyHint')"
                  :error-messages="certificateMessages.key"
                  accept=".key,.pem"
                />
              </VCol>
            </template>
            <VCol cols="12" sm="6">
              <VTextField
                v-model="username"
                :label="t('connectors.form.username')"
                autocomplete="off"
              />
            </VCol>
            <VCol cols="12" sm="6">
              <VTextField
                v-model="password"
                type="password"
                :label="t('connectors.form.password')"
                :hint="editing && hasPassword ? t('connectors.form.passwordKeep') : undefined"
                :persistent-hint="editing && hasPassword"
                autocomplete="new-password"
              />
            </VCol>
            <VCol cols="12" sm="6">
              <VTextField
                v-model="clientId"
                :label="t('connectors.form.clientId')"
                :hint="t('connectors.form.clientIdHint')"
                persistent-hint
                autocomplete="off"
              />
            </VCol>
          </VRow>
        </VCardText>
      </VCard>

      <VCard>
        <VCardText class="pa-4 pa-sm-6">
          <h2 class="text-subtitle-1 font-weight-medium mb-4">{{ t('connectors.form.message') }}</h2>
          <div class="d-flex flex-column ga-4">
            <VSelect v-model="payloadType" :items="formatItems" :label="t('connectors.form.format')">
              <template #item="{ item, props: itemProps }">
                <VListItem v-bind="itemProps" :subtitle="item.raw.subtitle" />
              </template>
            </VSelect>

            <VTextField
              v-model="topic"
              :label="t('connectors.form.topic')"
              :hint="topicHint"
              persistent-hint
              spellcheck="false"
              autocomplete="off"
              :error-messages="topicMessage"
            />

            <VSwitch
              v-if="!isSnapshot(payloadType)"
              v-model="readableNames"
              color="primary"
              inset
              hide-details
              :label="t('connectors.form.readableNames')"
            />

            <VAlert v-if="payloadType === 'legacy'" type="info" variant="tonal" density="comfortable">
              {{ t('connectors.form.legacyNotice') }}
            </VAlert>
          </div>
        </VCardText>
      </VCard>

      <VCard>
        <VCardText class="pa-4 pa-sm-6">
          <h2 class="text-subtitle-1 font-weight-medium mb-1">{{ t('connectors.form.entities') }}</h2>
          <p class="text-body-2 text-medium-emphasis mb-4">{{ entitiesHint }}</p>
          <ConnectorEntitiesPicker v-model="entities" />
        </VCardText>
      </VCard>

      <VAlert v-if="error" type="error" :text="error" role="alert" />

      <div class="d-flex flex-wrap ga-3 justify-end">
        <VBtn
          variant="text"
          :to="editing ? `/conectores/${connectorId}` : '/conectores'"
          :disabled="saving"
        >
          {{ t('common.cancel') }}
        </VBtn>
        <VBtn type="submit" color="primary" prepend-icon="mdi-check" :loading="saving">
          {{ t('connectors.form.submit') }}
        </VBtn>
      </div>
    </form>
  </StateBlock>
</template>
