<script setup lang="ts">
import { computed, ref } from 'vue'
import { t } from '@/i18n'
import { FAMILY_LABEL, templateList, type TemplateDescriptor, type TemplateFamily } from '../templates/registry'
import type { TemplateKey } from '../templates/contract'

const props = defineProps<{ modelValue: TemplateKey | null }>()
const emit = defineEmits<{ 'update:modelValue': [TemplateKey | null] }>()

const search = ref('')

const query = computed(() => search.value.trim().toLowerCase())

const matches = computed<TemplateDescriptor[]>(() =>
  templateList().filter((item) =>
    !query.value ||
    item.label.toLowerCase().includes(query.value) ||
    item.description.toLowerCase().includes(query.value),
  ),
)

/** Agrupado por familia, en el orden en que el registro las declara. */
const groups = computed(() => {
  const order: TemplateFamily[] = []
  const byFamily = new Map<TemplateFamily, TemplateDescriptor[]>()
  for (const item of matches.value) {
    if (!byFamily.has(item.family)) {
      byFamily.set(item.family, [])
      order.push(item.family)
    }
    byFamily.get(item.family)!.push(item)
  }
  return order.map((family) => ({ family, label: FAMILY_LABEL[family], items: byFamily.get(family)! }))
})

function select(key: TemplateKey) {
  emit('update:modelValue', props.modelValue === key ? null : key)
}
</script>

<template>
  <div class="d-flex flex-column ga-4" role="radiogroup" :aria-label="t('dashboards.picker.legend')">
    <VTextField
      v-model="search"
      :label="t('dashboards.picker.search')"
      prepend-inner-icon="mdi-magnify"
      clearable
    />

    <div v-if="!groups.length" class="text-body-2 text-medium-emphasis">
      {{ t('dashboards.picker.noMatches', { query: search }) }}
    </div>

    <div v-for="group in groups" :key="group.family" class="d-flex flex-column ga-2">
      <div class="text-caption text-medium-emphasis font-weight-medium text-uppercase">
        {{ group.label }}
      </div>

      <VRow dense>
        <VCol v-for="item in group.items" :key="item.key" cols="12" sm="6">
          <VCard
            class="card-link h-100 pa-4 d-flex align-start ga-3"
            :variant="item.key === modelValue ? 'tonal' : 'flat'"
            :color="item.key === modelValue ? 'primary' : undefined"
            :style="item.key === modelValue ? { borderColor: 'rgb(var(--v-theme-primary))', borderWidth: '2px' } : undefined"
            role="radio"
            :aria-checked="item.key === modelValue"
            tabindex="0"
            @click="select(item.key)"
            @keydown.enter.prevent="select(item.key)"
            @keydown.space.prevent="select(item.key)"
          >
            <div class="icon-tile" style="width: 40px; height: 40px">
              <VIcon :icon="item.icon" size="22" />
            </div>

            <div class="min-w-0 flex-grow-1">
              <div class="text-subtitle-2 font-weight-medium">{{ item.label }}</div>
              <div class="text-body-2 text-medium-emphasis mt-1">{{ item.description }}</div>
            </div>

            <VIcon
              v-if="item.key === modelValue"
              icon="mdi-check-circle"
              color="primary"
              size="20"
              class="flex-shrink-0"
              :aria-label="t('dashboards.picker.selected')"
            />
          </VCard>
        </VCol>
      </VRow>
    </div>
  </div>
</template>
