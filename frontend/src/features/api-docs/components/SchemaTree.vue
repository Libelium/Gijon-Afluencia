<script setup lang="ts">
import { t } from '@/i18n'
import type { SchemaNode } from '../lib/openapi'

/** Propiedades de un esquema como lista anidada: la jerarquia la anuncia el lector de pantalla. */
defineProps<{ nodes: SchemaNode[] }>()
</script>

<template>
  <ul class="schema-tree">
    <li v-for="node in nodes" :key="node.name" class="schema-tree__item">
      <div class="d-flex flex-wrap align-baseline ga-2">
        <code class="schema-tree__name">{{ node.name }}</code>
        <span class="text-caption text-medium-emphasis">{{ node.type }}</span>
        <span v-if="node.required" class="text-caption font-weight-bold">
          {{ t('apiDocs.required') }}
        </span>
        <span v-if="node.truncated" class="text-caption text-medium-emphasis">
          ({{ t('apiDocs.schema.truncated') }})
        </span>
      </div>
      <div v-if="node.description" class="text-body-2 text-medium-emphasis">
        {{ node.description }}
      </div>
      <SchemaTree v-if="node.children.length" :nodes="node.children" />
    </li>
  </ul>
</template>

<style scoped>
.schema-tree {
  list-style: none;
  padding-left: 0;
  margin: 0;
}

.schema-tree .schema-tree {
  padding-left: 16px;
  margin-top: 4px;
  border-left: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.schema-tree__item + .schema-tree__item {
  margin-top: 6px;
}

.schema-tree__name {
  font-size: 0.8125rem;
  font-weight: 600;
}
</style>
