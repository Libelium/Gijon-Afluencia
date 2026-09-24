<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import ClassDetail from '../components/ClassDetail.vue'
import ClassTreeNode from '../components/ClassTreeNode.vue'
import { ancestors, buildIndex, normalize, searchClasses, type OntologyIndex } from '../lib/ontology'
import {
  DESTINATION,
  MEASUREMENTS,
  PIT_PROPERTIES,
  PITS,
  RELATED,
  SITE,
  mappedClassIds,
  pitsByClass,
} from '../lib/mapping'
import type { Ontology } from '../lib/types'

/**
 * Ontologia de turismo de SEGITTUR y como la usa la plataforma.
 *
 * Los datos (unos doscientos kilobytes) se cargan con `import()` dinamico para no pesar en el
 * resto de la aplicacion. La pestana y la clase elegidas van en la URL, asi que una ficha se
 * puede enlazar o volver a abrir tal cual.
 */
const route = useRoute()
const router = useRouter()

type Tab = 'correspondencia' | 'clases' | 'tesauros'
const TABS: Tab[] = ['correspondencia', 'clases', 'tesauros']

const ontology = shallowRef<Ontology | null>(null)
const index = shallowRef<OntologyIndex | null>(null)
const error = ref<string | null>(null)

const tab = ref<Tab>(TABS.includes(route.query.tab as Tab) ? (route.query.tab as Tab) : 'correspondencia')
const selected = ref<string | null>((route.query.clase as string) || null)
const expanded = reactive(new Set<string>())
const classQuery = ref('')
const schemeQuery = ref('')

const highlighted = computed(() => new Set(mappedClassIds()))

async function load() {
  error.value = null
  try {
    const data = (await import('../data/segittur.json')).default as Ontology
    ontology.value = data
    index.value = buildIndex(data)
    if (!selected.value || !index.value.classes.has(selected.value)) selected.value = 'Square'
    reveal(selected.value)
    if (tab.value === 'clases') scrollToSelected()
  } catch {
    error.value = t('ontology.loadFailed')
  }
}

onMounted(load)

watch([tab, selected], ([currentTab, currentClass]) => {
  router.replace({
    query: { ...route.query, tab: currentTab, clase: currentTab === 'clases' ? currentClass ?? undefined : undefined },
  })
})

/** Despliega los antecesores para que la clase elegida quede a la vista en el arbol. */
function reveal(id: string) {
  if (!index.value) return
  for (const ancestor of ancestors(index.value, id)) expanded.add(ancestor)
}

function select(id: string) {
  selected.value = id
  tab.value = 'clases'
  classQuery.value = ''
  reveal(id)
  scrollToSelected()
}

/** Lleva la clase elegida a la vista del arbol, que tiene su propio desplazamiento. */
function scrollToSelected() {
  // Solo se desplaza el panel: scrollIntoView moveria tambien la pagina y dejaria las pestanas
  // bajo la barra superior.
  void nextTick(() => {
    const panel = document.querySelector<HTMLElement>('.tree-scroll')
    const row = panel?.querySelector<HTMLElement>('[aria-current="true"]')
    if (!panel || !row) return
    const offset = row.getBoundingClientRect().top - panel.getBoundingClientRect().top
    panel.scrollTop += offset - panel.clientHeight / 2
  })
}

function toggle(id: string) {
  if (expanded.has(id)) expanded.delete(id)
  else expanded.add(id)
}

const matches = computed(() => (index.value ? searchClasses(index.value, classQuery.value) : []))

const schemes = computed(() => {
  const all = ontology.value?.schemes ?? []
  const q = normalize(schemeQuery.value)
  if (!q) return all
  return all
    .map((s) =>
      normalize(s.label).includes(q)
        ? s
        : { ...s, concepts: s.concepts.filter((c) => normalize(c.label).includes(q)) },
    )
    .filter((s) => s.concepts.length || normalize(s.label).includes(q))
})

const classLabel = (id: string | null) => (id && index.value?.classes.get(id)?.label) || id || '—'
const classUri = (id: string | null) => (id && index.value?.classes.get(id)?.uri) || undefined
const propertyLabel = (id: string) => index.value?.properties.get(id)?.label ?? id

const stats = computed(() => ({
  classes: ontology.value?.classes.length ?? 0,
  properties: ontology.value?.properties.length ?? 0,
  schemes: ontology.value?.schemes.length ?? 0,
  concepts: ontology.value?.schemes.reduce((n, s) => n + s.concepts.length, 0) ?? 0,
}))

const pitClasses = computed(() => [...pitsByClass().entries()])
</script>

<template>
  <div>
    <PageHeader :title="t('ontology.title')" :subtitle="t('ontology.subtitle')" icon="mdi-graph-outline" />

    <StateBlock :loading="!ontology && !error" :error="error" skeleton="card" @retry="load">
      <template v-if="ontology && index">
        <VCard class="mb-6">
          <VCardText class="pa-4 pa-sm-6">
            <div class="d-flex flex-wrap align-start justify-space-between ga-3">
              <div class="min-w-0">
                <h2 class="text-subtitle-1 font-weight-bold">{{ ontology.meta.title }}</h2>
                <p class="text-body-2 text-medium-emphasis mt-1 mb-0">{{ ontology.meta.description }}</p>
              </div>
              <div class="d-flex flex-wrap ga-2">
                <VChip size="small" variant="tonal">
                  {{ t('ontology.meta.version', { version: ontology.meta.version }) }}
                </VChip>
                <VChip size="small" variant="outlined">{{ ontology.meta.issued }}</VChip>
              </div>
            </div>

            <div class="d-flex flex-wrap ga-6 mt-4 text-body-2">
              <div><strong>{{ stats.classes }}</strong> {{ t('ontology.meta.classes') }}</div>
              <div><strong>{{ stats.properties }}</strong> {{ t('ontology.meta.properties') }}</div>
              <div><strong>{{ stats.schemes }}</strong> {{ t('ontology.meta.schemes') }}</div>
              <div><strong>{{ stats.concepts }}</strong> {{ t('ontology.meta.concepts') }}</div>
            </div>

            <p class="text-caption text-medium-emphasis mt-4 mb-0">
              {{ t('ontology.meta.source') }}
              <a :href="ontology.meta.source" target="_blank" rel="noopener noreferrer">
                {{ ontology.meta.source }}
              </a>
              · {{ ontology.meta.rights }}
            </p>
          </VCardText>
        </VCard>

        <VTabs v-model="tab" color="primary" class="mb-4">
          <VTab value="correspondencia" prepend-icon="mdi-map-marker-path">{{ t('ontology.tab.mapping') }}</VTab>
          <VTab value="clases" prepend-icon="mdi-file-tree-outline">{{ t('ontology.tab.classes') }}</VTab>
          <VTab value="tesauros" prepend-icon="mdi-book-open-variant">{{ t('ontology.tab.schemes') }}</VTab>
        </VTabs>

        <VWindow v-model="tab">
          <!-- Correspondencia: que clase de SEGITTUR es cada elemento de la plataforma. -->
          <VWindowItem value="correspondencia">
            <div class="d-flex flex-column ga-6">
              <VAlert variant="outlined" icon="mdi-information-outline">
                {{ t('ontology.mapping.intro') }}
              </VAlert>

              <VRow>
                <VCol v-for="element in [DESTINATION, SITE]" :key="element.element" cols="12" md="6">
                  <VCard class="h-100">
                    <VCardText class="pa-4 pa-sm-6">
                      <div class="text-caption text-medium-emphasis text-uppercase">
                        {{ element === DESTINATION ? t('ontology.mapping.destination') : t('ontology.mapping.site') }}
                      </div>
                      <h3 class="text-subtitle-1 font-weight-bold">{{ element.element }}</h3>
                      <div class="d-flex align-center ga-2 mt-2">
                        <VIcon icon="mdi-arrow-right" size="16" aria-hidden="true" />
                        <a href="#" class="text-body-2 font-weight-medium" @click.prevent="select(element.classId!)">
                          {{ classLabel(element.classId) }}
                        </a>
                        <code class="text-caption">seg:{{ element.classId }}</code>
                      </div>
                      <p class="text-body-2 text-medium-emphasis mt-2">{{ element.description }}</p>
                      <ul v-if="element.properties" class="text-body-2 ps-4">
                        <li v-for="p in element.properties" :key="p.property">
                          <strong>{{ propertyLabel(p.property) }}</strong>
                          (<code>{{ p.property }}</code>): {{ p.source }}
                        </li>
                      </ul>
                    </VCardText>
                  </VCard>
                </VCol>
              </VRow>

              <VCard>
                <VCardText class="pa-4 pa-sm-6">
                  <h3 class="text-subtitle-1 font-weight-bold">
                    {{ t('ontology.mapping.pits', { count: PITS.length }) }}
                  </h3>
                  <p class="text-body-2 text-medium-emphasis mb-3">{{ t('ontology.mapping.pitsHelp') }}</p>

                  <div class="d-flex flex-wrap ga-2 mb-4">
                    <VChip
                      v-for="[classId, count] in pitClasses"
                      :key="classId"
                      size="small"
                      variant="tonal"
                      color="primary"
                      @click="select(classId)"
                    >
                      {{ classLabel(classId) }} · {{ count }}
                    </VChip>
                  </div>

                  <VTable density="comfortable">
                    <caption class="sr-only">{{ t('ontology.mapping.pitsCaption') }}</caption>
                    <thead>
                      <tr>
                        <th scope="col">{{ t('ontology.col.pit') }}</th>
                        <th scope="col">{{ t('ontology.col.zone') }}</th>
                        <th scope="col">{{ t('ontology.col.class') }}</th>
                        <th scope="col">URI</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="pit in PITS" :key="pit.zoneId">
                        <td class="text-body-2 font-weight-medium">{{ pit.name }}</td>
                        <td><code class="text-caption">{{ pit.zoneId }}</code></td>
                        <td>
                          <a href="#" class="text-body-2" @click.prevent="select(pit.classId)">
                            {{ classLabel(pit.classId) }}
                          </a>
                        </td>
                        <td>
                          <a
                            :href="classUri(pit.classId)"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-caption"
                          >seg:{{ pit.classId }}</a>
                        </td>
                      </tr>
                    </tbody>
                  </VTable>

                  <h4 class="text-subtitle-2 mt-6 mb-2">{{ t('ontology.mapping.pitProperties') }}</h4>
                  <ul class="text-body-2 ps-4">
                    <li v-for="p in PIT_PROPERTIES" :key="p.property">
                      <strong>{{ propertyLabel(p.property) }}</strong>
                      (<code>{{ p.property }}</code>): {{ p.source }}
                    </li>
                  </ul>

                  <template v-if="RELATED.length">
                    <h4 class="text-subtitle-2 mt-6 mb-2">{{ t('ontology.mapping.related') }}</h4>
                    <ul class="text-body-2 ps-4">
                      <li v-for="r in RELATED" :key="r.element">
                        {{ r.element }} →
                        <a href="#" @click.prevent="select(r.classId!)">{{ classLabel(r.classId) }}</a>.
                        {{ r.description }}
                      </li>
                    </ul>
                  </template>
                </VCardText>
              </VCard>

              <VCard>
                <VCardText class="pa-4 pa-sm-6">
                  <h3 class="text-subtitle-1 font-weight-bold">{{ t('ontology.mapping.measurements') }}</h3>
                  <p class="text-body-2 text-medium-emphasis mb-3">{{ t('ontology.mapping.measurementsHelp') }}</p>
                  <VTable density="comfortable">
                    <caption class="sr-only">{{ t('ontology.mapping.measurements') }}</caption>
                    <thead>
                      <tr>
                        <th scope="col">{{ t('ontology.col.datamodel') }}</th>
                        <th scope="col">{{ t('ontology.col.content') }}</th>
                        <th scope="col">{{ t('ontology.col.relation') }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="m in MEASUREMENTS" :key="m.datamodel">
                        <td><code class="text-body-2">{{ m.datamodel }}</code></td>
                        <td class="text-body-2">{{ m.description }}</td>
                        <td class="text-body-2">{{ m.relation }}</td>
                      </tr>
                    </tbody>
                  </VTable>
                </VCardText>
              </VCard>
            </div>
          </VWindowItem>

          <!-- Clases: arbol navegable y ficha de la clase elegida. -->
          <VWindowItem value="clases">
            <VRow>
              <VCol cols="12" md="5" lg="4">
                <VCard>
                  <VCardText class="pa-3">
                    <VTextField
                      v-model="classQuery"
                      :label="t('ontology.classes.search')"
                      prepend-inner-icon="mdi-magnify"
                      clearable
                      class="mb-2"
                    />
                    <p class="text-caption text-medium-emphasis mb-2 d-flex align-center ga-1">
                      <VIcon icon="mdi-map-marker-check-outline" size="14" color="primary" aria-hidden="true" />
                      {{ t('ontology.tree.legend') }}
                    </p>

                    <div class="tree-scroll">
                      <ul v-if="classQuery" class="result-list" :aria-label="t('ontology.classes.results')">
                        <li v-if="!matches.length" class="text-body-2 text-medium-emphasis pa-2">
                          {{ t('ontology.classes.noResults') }}
                        </li>
                        <li v-for="c in matches" :key="c.id">
                          <button
                            type="button"
                            class="result-item text-body-2 text-start"
                            :aria-current="selected === c.id ? 'true' : undefined"
                            @click="select(c.id)"
                          >
                            {{ c.label }}
                            <span class="text-caption text-medium-emphasis">· {{ c.labelEn }}</span>
                          </button>
                        </li>
                      </ul>
                      <ul v-else class="tree-root" :aria-label="t('ontology.classes.tree')">
                        <ClassTreeNode
                          v-for="root in index.roots"
                          :key="root"
                          :index="index"
                          :id="root"
                          :depth="0"
                          :selected="selected"
                          :expanded="expanded"
                          :highlighted="highlighted"
                          @select="select"
                          @toggle="toggle"
                        />
                      </ul>
                    </div>
                  </VCardText>
                </VCard>
              </VCol>

              <VCol cols="12" md="7" lg="8">
                <VCard>
                  <VCardText class="pa-4 pa-sm-6">
                    <ClassDetail v-if="selected" :index="index" :id="selected" @select="select" />
                  </VCardText>
                </VCard>
              </VCol>
            </VRow>
          </VWindowItem>

          <!-- Tesauros SKOS: vocabularios controlados de los valores. -->
          <VWindowItem value="tesauros">
            <VCard class="mb-4">
              <VCardText class="pa-4">
                <p class="text-body-2 text-medium-emphasis mb-3">{{ t('ontology.schemes.help') }}</p>
                <VTextField
                  v-model="schemeQuery"
                  :label="t('ontology.schemes.search')"
                  prepend-inner-icon="mdi-magnify"
                  clearable
                  max-width="420"
                />
              </VCardText>
            </VCard>

            <p v-if="!schemes.length" class="text-body-2 text-medium-emphasis">
              {{ t('ontology.schemes.noResults') }}
            </p>
            <VExpansionPanels v-else multiple variant="accordion">
              <VExpansionPanel v-for="scheme in schemes" :key="scheme.id">
                <VExpansionPanelTitle>
                  <span class="font-weight-medium">{{ scheme.label }}</span>
                  <span class="text-caption text-medium-emphasis ms-2">
                    {{ t('ontology.schemes.count', { count: scheme.concepts.length }) }}
                  </span>
                </VExpansionPanelTitle>
                <VExpansionPanelText>
                  <a :href="scheme.uri" target="_blank" rel="noopener noreferrer" class="text-caption text-break">
                    {{ scheme.uri }}
                  </a>
                  <div class="d-flex flex-wrap ga-2 mt-3">
                    <VChip
                      v-for="concept in scheme.concepts"
                      :key="concept.uri"
                      size="small"
                      variant="outlined"
                      :href="concept.uri"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {{ concept.label }}
                    </VChip>
                  </div>
                </VExpansionPanelText>
              </VExpansionPanel>
            </VExpansionPanels>
          </VWindowItem>
        </VWindow>
      </template>
    </StateBlock>
  </div>
</template>

<style scoped>
.tree-scroll {
  max-height: 65vh;
  overflow-y: auto;
}

.tree-root,
.result-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.result-item {
  width: 100%;
  background: none;
  border: 0;
  color: inherit;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
}

.result-item[aria-current='true'] {
  background: rgba(var(--v-theme-primary), 0.12);
  font-weight: 600;
}

.result-item:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
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
