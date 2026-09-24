<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import DOMPurify from 'dompurify'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import OperationDetail from '../components/OperationDetail.vue'
import { renderMarkdown } from '../lib/markdown'
import {
  filterOperations,
  groupByTag,
  listOperations,
  type HttpMethod,
  type OpenApiSpec,
} from '../lib/openapi'

/**
 * Referencia de la API de la plataforma, leida de las especificaciones OpenAPI del repositorio.
 *
 * Las especificaciones se cargan con `import()` dinamico: son unos cien kilobytes que solo
 * necesita quien abre esta pantalla, y asi viajan en su propio fragmento.
 */
type SpecKey = 'gestion' | 'ingesta'

const LOADERS: Record<SpecKey, () => Promise<{ default: unknown }>> = {
  gestion: () => import('../specs/gestion.json'),
  ingesta: () => import('../specs/ingesta.json'),
}

const FILE_NAMES: Record<SpecKey, string> = {
  gestion: 'openapi-gestion.json',
  ingesta: 'openapi-ingesta.json',
}

// El metodo se escribe siempre como texto; el color solo refuerza (WCAG 1.4.1).
const METHOD_COLORS: Record<HttpMethod, string> = {
  get: 'info',
  post: 'success',
  put: 'warning',
  patch: 'warning',
  delete: 'error',
  head: 'secondary',
  options: 'secondary',
}

const active = ref<SpecKey>('gestion')
const spec = shallowRef<OpenApiSpec | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const query = ref('')
const openTags = ref<string[]>([])

async function load(key: SpecKey) {
  loading.value = true
  error.value = null
  try {
    const module = await LOADERS[key]()
    spec.value = module.default as OpenApiSpec
  } catch {
    spec.value = null
    error.value = t('apiDocs.loadError')
  } finally {
    loading.value = false
  }
}

watch(active, (key) => {
  query.value = ''
  openTags.value = []
  void load(key)
}, { immediate: true })

const operations = computed(() => (spec.value ? listOperations(spec.value) : []))
const filtered = computed(() => filterOperations(operations.value, query.value))
const groups = computed(() => (spec.value ? groupByTag(spec.value, filtered.value) : []))

// Con una busqueda escrita se despliegan todos los grupos: si no, el resultado quedaria escondido.
watch(query, (value) => {
  openTags.value = value.trim() ? groups.value.map((g) => g.name) : []
})

const countText = computed(() =>
  filtered.value.length === 1
    ? t('apiDocs.countOne')
    : t('apiDocs.count', { count: filtered.value.length }),
)

const descriptionHtml = computed(() => {
  const text = spec.value?.info?.description
  return text ? DOMPurify.sanitize(renderMarkdown(text)) : ''
})

const servers = computed(() => spec.value?.servers ?? [])

function download() {
  if (!spec.value) return
  const blob = new Blob([JSON.stringify(spec.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = FILE_NAMES[active.value]
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div>
    <PageHeader
      :title="t('apiDocs.title')"
      :subtitle="t('apiDocs.subtitle')"
      icon="mdi-api"
    >
      <template #actions>
        <VBtn
          variant="tonal"
          color="primary"
          prepend-icon="mdi-download"
          :disabled="!spec"
          @click="download"
        >
          {{ t('apiDocs.download') }}
        </VBtn>
      </template>
    </PageHeader>

    <VTabs v-model="active" color="primary" class="mb-4" :aria-label="t('apiDocs.tabs')">
      <VTab value="gestion" prepend-icon="mdi-cog-outline">{{ t('apiDocs.tab.gestion') }}</VTab>
      <VTab value="ingesta" prepend-icon="mdi-import">{{ t('apiDocs.tab.ingesta') }}</VTab>
    </VTabs>

    <StateBlock :loading="loading" :error="error" skeleton="card" @retry="load(active)">
      <template v-if="spec">
        <VCard class="mb-6">
          <VCardText class="pa-4 pa-sm-6">
            <div class="d-flex flex-wrap align-center ga-3 mb-3">
              <h2 class="text-h6 flex-grow-1 min-w-0">{{ spec.info?.title }}</h2>
              <VChip v-if="spec.info?.version" variant="tonal" size="small">
                {{ t('apiDocs.version', { version: spec.info.version }) }}
              </VChip>
              <VChip v-if="spec.openapi" variant="outlined" size="small">
                OpenAPI {{ spec.openapi }}
              </VChip>
            </div>

            <!-- eslint-disable-next-line vue/no-v-html -- texto escapado y saneado con DOMPurify -->
            <div v-if="descriptionHtml" class="api-md text-body-2 mb-4" v-html="descriptionHtml" />

            <VRow dense>
              <VCol cols="12" md="6">
                <div class="text-caption text-medium-emphasis mb-1">{{ t('apiDocs.auth') }}</div>
                <p class="text-body-2">{{ t(`apiDocs.auth.${active}`) }}</p>
              </VCol>
              <VCol cols="12" md="6">
                <div class="text-caption text-medium-emphasis mb-1">{{ t('apiDocs.servers') }}</div>
                <ul class="api-servers">
                  <li v-for="server in servers" :key="server.url" class="text-body-2">
                    <code>{{ server.url }}</code>
                    <span v-if="server.description" class="text-medium-emphasis">
                      — {{ server.description }}
                    </span>
                  </li>
                </ul>
              </VCol>
            </VRow>
          </VCardText>
        </VCard>

        <div class="d-flex flex-wrap align-center ga-4 mb-4">
          <VTextField
            v-model="query"
            :label="t('apiDocs.search')"
            prepend-inner-icon="mdi-magnify"
            clearable
            hide-details
            class="api-search"
          />
          <span class="text-body-2 text-medium-emphasis" role="status">{{ countText }}</span>
        </div>

        <StateBlock
          :empty="!groups.length"
          :empty-text="t('apiDocs.noResults')"
          empty-icon="mdi-magnify-remove-outline"
        >
          <VExpansionPanels v-model="openTags" multiple variant="accordion">
            <VExpansionPanel v-for="group in groups" :key="group.name" :value="group.name">
              <VExpansionPanelTitle>
                <div class="d-flex flex-wrap align-center ga-3 min-w-0">
                  <span class="text-subtitle-1 font-weight-medium">{{ group.name }}</span>
                  <span class="text-caption text-medium-emphasis">
                    {{ group.operations.length === 1
                      ? t('apiDocs.countOne')
                      : t('apiDocs.count', { count: group.operations.length }) }}
                  </span>
                </div>
              </VExpansionPanelTitle>
              <VExpansionPanelText>
                <p v-if="group.description" class="text-body-2 text-medium-emphasis mb-3">
                  {{ group.description }}
                </p>
                <VExpansionPanels variant="accordion" class="api-operations">
                  <VExpansionPanel
                    v-for="op in group.operations"
                    :key="`${op.method} ${op.path}`"
                    elevation="0"
                    class="border"
                  >
                    <VExpansionPanelTitle>
                      <div class="d-flex flex-wrap align-center ga-3 min-w-0">
                        <VChip
                          :color="METHOD_COLORS[op.method]"
                          variant="tonal"
                          size="small"
                          label
                          class="api-method font-weight-bold"
                        >
                          {{ op.method.toUpperCase() }}
                        </VChip>
                        <code class="api-path">{{ op.path }}</code>
                        <span class="text-body-2 text-medium-emphasis">{{ op.summary }}</span>
                      </div>
                    </VExpansionPanelTitle>
                    <VExpansionPanelText>
                      <OperationDetail :spec="spec" :operation="op" />
                    </VExpansionPanelText>
                  </VExpansionPanel>
                </VExpansionPanels>
              </VExpansionPanelText>
            </VExpansionPanel>
          </VExpansionPanels>
        </StateBlock>
      </template>
    </StateBlock>
  </div>
</template>

<style scoped>
.api-search {
  max-width: 480px;
  min-width: 240px;
}

.api-servers {
  list-style: none;
  padding: 0;
  margin: 0;
}

.api-method {
  min-width: 68px;
  justify-content: center;
}

.api-path {
  font-size: 0.875rem;
  word-break: break-all;
}

.api-operations {
  gap: 8px;
}

.api-md :deep(p + p),
.api-md :deep(p + ol),
.api-md :deep(p + ul) {
  margin-top: 8px;
}

.api-md :deep(ol),
.api-md :deep(ul) {
  padding-left: 20px;
}
</style>
