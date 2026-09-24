<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { t } from '@/i18n'
import { schemaTree, schemaType, type OpenApiSpec, type Operation } from '../lib/openapi'
import { renderMarkdown } from '../lib/markdown'
import SchemaTree from './SchemaTree.vue'

/** Detalle de una operacion: descripcion, parametros, cuerpo y respuestas. */
const props = defineProps<{ spec: OpenApiSpec; operation: Operation }>()

const descriptionHtml = computed(() =>
  props.operation.description ? DOMPurify.sanitize(renderMarkdown(props.operation.description)) : '',
)

const bodyNodes = computed(() =>
  props.operation.requestBody ? schemaTree(props.spec, props.operation.requestBody) : [],
)

const bodyType = computed(() =>
  props.operation.requestBody ? schemaType(props.spec, props.operation.requestBody) : '',
)
</script>

<template>
  <div class="d-flex flex-column ga-5">
    <!-- eslint-disable-next-line vue/no-v-html -- texto escapado y saneado con DOMPurify -->
    <div v-if="descriptionHtml" class="api-md text-body-2" v-html="descriptionHtml" />

    <section>
      <h3 class="text-subtitle-2 mb-2">{{ t('apiDocs.parameters') }}</h3>
      <p v-if="!operation.parameters.length" class="text-body-2 text-medium-emphasis">
        {{ t('apiDocs.parameters.none') }}
      </p>
      <VTable v-else density="compact" class="border rounded">
        <caption class="d-sr-only">
          {{ t('apiDocs.parameters.caption', { path: operation.path }) }}
        </caption>
        <thead>
          <tr>
            <th scope="col">{{ t('apiDocs.col.name') }}</th>
            <th scope="col">{{ t('apiDocs.col.in') }}</th>
            <th scope="col">{{ t('apiDocs.col.type') }}</th>
            <th scope="col">{{ t('apiDocs.col.required') }}</th>
            <th scope="col">{{ t('apiDocs.col.description') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="param in operation.parameters" :key="`${param.in}:${param.name}`">
            <td><code>{{ param.name }}</code></td>
            <td>{{ param.in }}</td>
            <td>{{ param.type }}</td>
            <td>{{ param.required ? t('apiDocs.yes') : t('apiDocs.no') }}</td>
            <td>{{ param.description || '—' }}</td>
          </tr>
        </tbody>
      </VTable>
    </section>

    <section v-if="operation.requestBody">
      <h3 class="text-subtitle-2 mb-2">
        {{ t('apiDocs.body') }}
        <span class="text-caption text-medium-emphasis ms-2">
          {{ bodyType }} · {{ operation.requestBodyRequired ? t('apiDocs.required') : t('apiDocs.optional') }}
        </span>
      </h3>
      <SchemaTree v-if="bodyNodes.length" :nodes="bodyNodes" />
      <p v-else class="text-body-2 text-medium-emphasis">{{ t('apiDocs.body.free') }}</p>
    </section>

    <section>
      <h3 class="text-subtitle-2 mb-2">{{ t('apiDocs.responses') }}</h3>
      <ul class="api-responses">
        <li v-for="response in operation.responses" :key="response.code" class="d-flex ga-3">
          <code class="font-weight-bold">{{ response.code }}</code>
          <span class="text-body-2">{{ response.description || '—' }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.api-responses {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
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
