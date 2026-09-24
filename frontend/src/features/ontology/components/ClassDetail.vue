<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { ancestors, effectiveProperties, type OntologyIndex } from '../lib/ontology'
import { PITS } from '../lib/mapping'

/** Ficha de una clase: jerarquia, descripcion, propiedades (propias y heredadas) y uso. */
const props = defineProps<{ index: OntologyIndex; id: string }>()
const emit = defineEmits<{ select: [id: string] }>()

const cls = computed(() => props.index.classes.get(props.id))
const path = computed(() => ancestors(props.index, props.id))
const children = computed(() => props.index.children.get(props.id) ?? [])
const properties = computed(() => effectiveProperties(props.index, props.id))
const pits = computed(() => PITS.filter((p) => p.classId === props.id))

const label = (id: string) => props.index.classes.get(id)?.label ?? id
const rangeLabel = (ids: string[]) =>
  ids.length ? ids.map((id) => props.index.classes.get(id)?.label ?? id).join(', ') : '—'
</script>

<template>
  <div v-if="cls" class="d-flex flex-column ga-5">
    <div>
      <nav v-if="path.length" :aria-label="t('ontology.detail.hierarchy')" class="mb-2">
        <ol class="breadcrumb text-caption">
          <li v-for="ancestor in path" :key="ancestor">
            <a href="#" @click.prevent="emit('select', ancestor)">{{ label(ancestor) }}</a>
            <VIcon icon="mdi-chevron-right" size="14" aria-hidden="true" />
          </li>
        </ol>
      </nav>

      <h2 class="text-h6 font-weight-bold">{{ cls.label }}</h2>
      <div class="text-body-2 text-medium-emphasis">
        {{ cls.labelEn }} · <code>{{ cls.id }}</code>
      </div>
      <a
        :href="cls.uri"
        target="_blank"
        rel="noopener noreferrer"
        class="text-caption d-inline-flex align-center ga-1 mt-1 text-break"
      >
        {{ cls.uri }}
        <VIcon icon="mdi-open-in-new" size="12" :aria-label="t('ontology.detail.external')" />
      </a>
    </div>

    <p v-if="cls.comment" class="text-body-2">{{ cls.comment }}</p>
    <p v-else class="text-body-2 text-medium-emphasis">{{ t('ontology.detail.noComment') }}</p>

    <VAlert v-if="pits.length" variant="outlined" density="comfortable" icon="mdi-map-marker-check-outline">
      <div class="font-weight-medium mb-1">
        {{ pits.length === 1 ? t('ontology.detail.usedByOne') : t('ontology.detail.usedBy', { count: pits.length }) }}
      </div>
      <div class="text-body-2">{{ pits.map((p) => p.name).join(' · ') }}</div>
    </VAlert>

    <section v-if="children.length">
      <h3 class="text-subtitle-2 mb-2">
        {{ t('ontology.detail.subclasses', { count: children.length }) }}
      </h3>
      <div class="d-flex flex-wrap ga-2">
        <VChip
          v-for="child in children"
          :key="child"
          size="small"
          variant="outlined"
          @click="emit('select', child)"
        >
          {{ label(child) }}
        </VChip>
      </div>
    </section>

    <section>
      <h3 class="text-subtitle-2 mb-2">
        {{ t('ontology.detail.properties', { count: properties.length }) }}
      </h3>
      <p v-if="!properties.length" class="text-body-2 text-medium-emphasis">
        {{ t('ontology.detail.noProperties') }}
      </p>
      <VTable v-else density="compact">
        <caption class="sr-only">{{ t('ontology.detail.propertiesCaption', { name: cls.label }) }}</caption>
        <thead>
          <tr>
            <th scope="col">{{ t('ontology.col.property') }}</th>
            <th scope="col">{{ t('ontology.col.kind') }}</th>
            <th scope="col">{{ t('ontology.col.range') }}</th>
            <th scope="col">{{ t('ontology.col.from') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="{ property, from } in properties" :key="property.id">
            <td>
              <div class="text-body-2">{{ property.label }}</div>
              <code class="text-caption">{{ property.id }}</code>
            </td>
            <td class="text-body-2">
              {{ t(property.kind === 'datatype' ? 'ontology.kind.datatype' : 'ontology.kind.object') }}
            </td>
            <td class="text-body-2">{{ rangeLabel(property.range) }}</td>
            <td class="text-body-2">
              <span v-if="from === id">{{ t('ontology.detail.own') }}</span>
              <a v-else href="#" @click.prevent="emit('select', from)">{{ label(from) }}</a>
            </td>
          </tr>
        </tbody>
      </VTable>
    </section>
  </div>
</template>

<style scoped>
.breadcrumb {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
}

.breadcrumb li {
  display: inline-flex;
  align-items: center;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
