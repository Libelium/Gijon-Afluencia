<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import type { OntologyIndex } from '../lib/ontology'

/**
 * Nodo del arbol de clases. Es una lista anidada de botones y no un `role="tree"`: el patron de
 * arbol exige navegacion con flechas que un lector de pantalla solo anuncia bien si esta completa,
 * y una lista con botones de desplegar es igual de navegable con tabulador y no promete nada.
 */
const props = defineProps<{
  index: OntologyIndex
  id: string
  depth: number
  selected: string | null
  expanded: Set<string>
  highlighted: Set<string>
}>()

const emit = defineEmits<{ select: [id: string]; toggle: [id: string] }>()

const cls = computed(() => props.index.classes.get(props.id))
const children = computed(() => props.index.children.get(props.id) ?? [])
const open = computed(() => props.expanded.has(props.id))
</script>

<template>
  <li v-if="cls" class="tree-node">
    <div
      class="tree-row d-flex align-center ga-1 rounded"
      :class="{ 'tree-row--selected': selected === id }"
      :style="{ paddingInlineStart: `${depth * 16}px` }"
    >
      <VBtn
        v-if="children.length"
        :icon="open ? 'mdi-chevron-down' : 'mdi-chevron-right'"
        variant="text"
        size="x-small"
        density="comfortable"
        :aria-expanded="open"
        :aria-label="t(open ? 'ontology.tree.collapse' : 'ontology.tree.expand', { name: cls.label })"
        @click="emit('toggle', id)"
      />
      <span v-else class="tree-spacer" aria-hidden="true" />

      <button
        type="button"
        class="tree-label text-body-2 text-start flex-grow-1 min-w-0 text-truncate"
        :aria-current="selected === id ? 'true' : undefined"
        @click="emit('select', id)"
      >
        {{ cls.label }}
        <VIcon
          v-if="highlighted.has(id)"
          icon="mdi-map-marker-check-outline"
          size="14"
          color="primary"
          class="ms-1"
          :aria-label="t('ontology.tree.usedHint')"
        />
      </button>
      <span v-if="children.length" class="text-caption text-medium-emphasis pe-2">
        {{ children.length }}
      </span>
    </div>

    <ul v-if="open && children.length" class="tree-list">
      <ClassTreeNode
        v-for="child in children"
        :key="child"
        :index="index"
        :id="child"
        :depth="depth + 1"
        :selected="selected"
        :expanded="expanded"
        :highlighted="highlighted"
        @select="emit('select', $event)"
        @toggle="emit('toggle', $event)"
      />
    </ul>
  </li>
</template>

<style scoped>
.tree-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.tree-row {
  min-height: 32px;
}

.tree-row--selected {
  background: rgba(var(--v-theme-primary), 0.12);
}

.tree-row--selected .tree-label {
  font-weight: 600;
}

.tree-spacer {
  display: inline-block;
  width: 28px;
  flex: 0 0 28px;
}

.tree-label {
  background: none;
  border: 0;
  color: inherit;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
}

.tree-label:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}
</style>
