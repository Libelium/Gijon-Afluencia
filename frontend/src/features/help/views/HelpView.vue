<script setup lang="ts">
import { computed, ref } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { FAQ, SECTIONS } from '../lib/content'
import { filterFaq, filterSections } from '../lib/search'

/**
 * Ayuda de la aplicacion: un indice a la izquierda (fijo en escritorio) y una tarjeta por
 * seccion, mas las preguntas frecuentes. El buscador filtra secciones y preguntas a la vez.
 */
const query = ref('')

const sections = computed(() => filterSections(SECTIONS, query.value))
const faq = computed(() => filterFaq(FAQ, query.value))
const nothing = computed(() => !sections.value.length && !faq.value.length)

const resultText = computed(() => {
  if (!query.value.trim()) return ''
  const total = sections.value.length + faq.value.length
  return total === 1 ? t('help.resultsOne') : t('help.results', { count: total })
})

/**
 * El indice mueve el foco al titulo de la seccion, no solo el scroll: quien navega con teclado
 * o lector de pantalla sigue leyendo desde alli (WCAG 2.4.3). Sin `#` en la URL, que el
 * enrutador tomaria por una ruta.
 */
function goTo(id: string) {
  const heading = document.getElementById(`ayuda-${id}`)
  if (!heading) return
  heading.focus()
  heading.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <div>
    <PageHeader :title="t('help.title')" :subtitle="t('help.subtitle')" icon="mdi-help-circle-outline" />

    <div class="d-flex flex-wrap align-center ga-4 mb-6">
      <VTextField
        v-model="query"
        :label="t('help.search')"
        prepend-inner-icon="mdi-magnify"
        clearable
        hide-details
        class="help-search"
      />
      <span class="text-body-2 text-medium-emphasis" role="status">{{ resultText }}</span>
    </div>

    <StateBlock
      :empty="nothing"
      :empty-text="t('help.noResults')"
      :empty-hint="t('help.noResultsHint')"
      empty-icon="mdi-magnify-remove-outline"
    >
      <VRow>
        <VCol cols="12" md="3">
          <nav class="help-index" :aria-label="t('help.index')">
            <VCard>
              <VCardText class="pa-2">
                <h2 class="text-caption font-weight-bold text-uppercase px-3 pt-2 pb-1">
                  {{ t('help.index') }}
                </h2>
                <VList density="compact" nav>
                  <VListItem
                    v-for="section in sections"
                    :key="section.id"
                    :prepend-icon="section.icon"
                    :title="section.title"
                    @click="goTo(section.id)"
                  />
                  <VListItem
                    v-if="faq.length"
                    prepend-icon="mdi-frequently-asked-questions"
                    :title="t('help.faq')"
                    @click="goTo('faq')"
                  />
                </VList>
              </VCardText>
            </VCard>
          </nav>
        </VCol>

        <VCol cols="12" md="9">
          <div class="d-flex flex-column ga-6">
            <VCard v-for="section in sections" :key="section.id" tag="section">
              <VCardText class="pa-4 pa-sm-6">
                <div class="d-flex align-center ga-3 mb-3">
                  <VIcon :icon="section.icon" size="22" class="text-primary" />
                  <h2 :id="`ayuda-${section.id}`" tabindex="-1" class="text-h6 help-heading">
                    {{ section.title }}
                  </h2>
                </div>

                <p
                  v-for="(paragraph, i) in section.paragraphs"
                  :key="i"
                  class="text-body-1 mb-3"
                >
                  {{ paragraph }}
                </p>

                <dl v-if="section.items?.length" class="help-terms mb-3">
                  <div v-for="item in section.items" :key="item.term" class="help-terms__row">
                    <dt class="font-weight-medium">{{ item.term }}</dt>
                    <dd class="text-medium-emphasis">{{ item.text }}</dd>
                  </div>
                </dl>

                <div v-if="section.links?.length" class="d-flex flex-wrap ga-3 mt-2">
                  <VBtn
                    v-for="link in section.links"
                    :key="link.label"
                    :to="link.to"
                    :href="link.href"
                    variant="tonal"
                    color="primary"
                    :append-icon="link.href ? 'mdi-email-outline' : 'mdi-arrow-right'"
                  >
                    {{ link.label }}
                  </VBtn>
                </div>
              </VCardText>
            </VCard>

            <VCard v-if="faq.length" tag="section">
              <VCardText class="pa-4 pa-sm-6">
                <div class="d-flex align-center ga-3 mb-4">
                  <VIcon icon="mdi-frequently-asked-questions" size="22" class="text-primary" />
                  <h2 id="ayuda-faq" tabindex="-1" class="text-h6 help-heading">
                    {{ t('help.faq') }}
                  </h2>
                </div>
                <VExpansionPanels multiple variant="accordion">
                  <VExpansionPanel v-for="entry in faq" :key="entry.question">
                    <VExpansionPanelTitle>
                      <span class="text-subtitle-1 font-weight-medium">{{ entry.question }}</span>
                    </VExpansionPanelTitle>
                    <VExpansionPanelText>
                      <p class="text-body-1">{{ entry.answer }}</p>
                    </VExpansionPanelText>
                  </VExpansionPanel>
                </VExpansionPanels>
              </VCardText>
            </VCard>
          </div>
        </VCol>
      </VRow>
    </StateBlock>
  </div>
</template>

<style scoped>
.help-search {
  max-width: 480px;
  min-width: 240px;
}

@media (min-width: 960px) {
  .help-index {
    position: sticky;
    top: 80px;
  }
}

.help-heading {
  scroll-margin-top: 80px;
}

.help-heading:focus {
  outline: none;
}

.help-heading:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 4px;
  border-radius: 4px;
}

.help-terms {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.help-terms__row dd {
  margin: 2px 0 0;
}
</style>
