<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { urnTail } from '@/lib/format'
import { searchEntities, type EntityOption } from '../api/catalog'
import { setDashboardTemplateEntities } from '../api/dashboards'

const props = defineProps<{
  modelValue: boolean
  dashboardId: number
  /** Seleccion actual segun el servidor. */
  selected: number[]
  /** false si el servidor no declara la asignacion. */
  selectionKnown: boolean
  /** Modelos de datos del descriptor de la plantilla. */
  datamodels: string[]
}>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [] }>()

const SEARCH_DEBOUNCE = 350

const chosen = ref<number[]>([])
const search = ref('')
const rows = ref<EntityOption[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const saveError = ref<string | null>(null)
const saving = ref(false)
const onlyCompatible = ref(true)

const open = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

async function load() {
  loading.value = true
  error.value = null
  try {
    const page = await searchEntities({
      search: search.value,
      datamodels: onlyCompatible.value ? props.datamodels : undefined,
      limit: 100,
    })
    rows.value = page.rows
  } catch (e) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined

watch(
  () => props.modelValue,
  (value) => {
    if (!value) return
    chosen.value = [...props.selected]
    search.value = ''
    onlyCompatible.value = props.datamodels.length > 0
    saveError.value = null
    void load()
  },
)

watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(() => void load(), SEARCH_DEBOUNCE)
})

watch(onlyCompatible, () => void load())

function toggle(id: number) {
  chosen.value = chosen.value.includes(id)
    ? chosen.value.filter((existing) => existing !== id)
    : [...chosen.value, id]
}

const unknownSelected = computed(
  () => chosen.value.filter((id) => !rows.value.some((row) => row.id === id)).length,
)

async function submit() {
  saving.value = true
  saveError.value = null
  try {
    await setDashboardTemplateEntities(props.dashboardId, chosen.value)
    open.value = false
    emit('saved')
  } catch (e) {
    saveError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <VDialog v-model="open" scrollable :persistent="saving">
    <VCard>
      <VCardTitle class="d-flex align-center ga-3 py-4">
        <span class="text-h6">{{ t('dashboards.templateEntities.title') }}</span>
        <VSpacer />
        <VBtn
          icon="mdi-close"
          variant="text"
          density="comfortable"
          :disabled="saving"
          :aria-label="t('common.close')"
          @click="open = false"
        />
      </VCardTitle>

      <VDivider />

      <VCardText class="pa-4">
        <div class="d-flex flex-column ga-4">
          <div class="text-body-2 text-medium-emphasis">{{ t('dashboards.templateEntities.help') }}</div>

          <VAlert
            v-if="!selectionKnown"
            type="info"
            density="comfortable"
            :text="t('dashboards.templateEntities.unreadable')"
          />

          <VTextField
            v-model="search"
            :label="t('dashboards.templateEntities.search')"
            prepend-inner-icon="mdi-magnify"
            clearable
          />

          <VSwitch
            v-model="onlyCompatible"
            color="primary"
            density="comfortable"
            :disabled="!datamodels.length"
            :label="t('dashboards.templateEntities.onlyCompatible')"
          />

          <div class="d-flex flex-wrap align-center ga-2">
            <VChip variant="tonal" color="primary" prepend-icon="mdi-check">
              {{
                chosen.length === 0
                  ? t('dashboards.templateEntities.none')
                  : chosen.length === 1
                    ? t('dashboards.templateEntities.selectedOne')
                    : t('dashboards.templateEntities.selected', { count: chosen.length })
              }}
            </VChip>
            <VChip v-if="unknownSelected" variant="tonal">
              {{ t('dashboards.templateEntities.unknownSelected', { count: unknownSelected }) }}
            </VChip>
          </div>

          <StateBlock
            :loading="loading"
            :error="error"
            :empty="!rows.length"
            :empty-text="onlyCompatible ? t('dashboards.templateEntities.emptyCompatible') : t('dashboards.templateEntities.empty')"
            empty-icon="mdi-access-point-off"
            skeleton="table"
            @retry="load"
          >
            <VList density="comfortable" class="pa-0">
              <VListItem
                v-for="row in rows"
                :key="row.id"
                :title="row.name"
                :subtitle="`${urnTail(row.urn)} · ${row.datamodel}`"
                @click="toggle(row.id)"
              >
                <template #prepend>
                  <VCheckboxBtn
                    :model-value="chosen.includes(row.id)"
                    color="primary"
                    @click.stop="toggle(row.id)"
                  />
                </template>
              </VListItem>
            </VList>
          </StateBlock>

          <VAlert v-if="saveError" type="error" :text="saveError" />
        </div>
      </VCardText>

      <VDivider />

      <VCardActions class="pa-4 ga-3 justify-end">
        <VBtn variant="text" :disabled="saving" @click="open = false">{{ t('common.cancel') }}</VBtn>
        <VBtn color="primary" :loading="saving" prepend-icon="mdi-content-save-outline" @click="submit">
          {{ t('dashboards.templateEntities.submit') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
