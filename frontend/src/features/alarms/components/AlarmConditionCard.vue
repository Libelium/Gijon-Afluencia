<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import type { Measure } from '@/types'
import { listMeasures } from '@/features/dashboards/api/catalog'
import EntityPicker from './EntityPicker.vue'
import { TIMEOUT_UNITS, operatorArity, operatorItems } from '../lib/operators'
import type { ConditionDraft } from '../lib/draft'
import type { AlarmType } from '../types'

const props = defineProps<{
  draft: ConditionDraft
  type: AlarmType
  position: number
  removable: boolean
}>()

const emit = defineEmits<{ remove: [] }>()

const measures = ref<Measure[]>([])
const measureLoading = ref(false)
const measureError = ref<string | null>(null)

const operators = computed(() => operatorItems())
const unitItems = computed(() => TIMEOUT_UNITS.map((u) => ({ value: u.value, title: t(u.labelKey) })))
const isRange = computed(() => operatorArity(props.draft.operator) === 2)

watch(
  () => props.draft.entity,
  async (entity) => {
    props.draft.measure = null
    measures.value = []
    measureError.value = null
    if (!entity) return

    measureLoading.value = true
    try {
      const rows = await listMeasures({ urn: entity.urn, tenant: entity.tenant, scope: entity.scope })
      measures.value = rows
      // Con una sola medida no hay nada que elegir: elegirla ahorra un paso que no decide nada.
      if (rows.length === 1) props.draft.measure = rows[0]
    } catch (e) {
      measureError.value = errorMessage(e)
    } finally {
      measureLoading.value = false
    }
  },
)
</script>

<template>
  <VCard variant="outlined">
    <VCardText class="pa-4">
      <div class="d-flex align-center ga-3 mb-4">
        <h3 class="text-subtitle-2 flex-grow-1 mb-0">
          {{ t('alarms.form.conditionNumber', { number: position }) }}
        </h3>
        <VBtn
          v-if="removable"
          icon="mdi-delete-outline"
          variant="text"
          density="comfortable"
          :aria-label="t('alarms.form.removeCondition')"
          :title="t('alarms.form.removeCondition')"
          @click="emit('remove')"
        />
      </div>

      <div class="d-flex flex-column ga-4">
        <EntityPicker v-model="draft.entity" />

        <VSelect
          v-model="draft.measure"
          :items="measures"
          return-object
          item-title="name"
          item-value="id"
          :label="type === 'inactivity' ? t('alarms.form.measureOptional') : t('alarms.form.measure')"
          :hint="type === 'inactivity' ? t('alarms.form.measureInactivityHint') : undefined"
          :persistent-hint="type === 'inactivity'"
          :loading="measureLoading"
          :disabled="!draft.entity || measureLoading"
          :clearable="type === 'inactivity'"
          :no-data-text="t('alarms.form.measureEmpty')"
          :error-messages="measureError ? [t('alarms.form.measureError')] : []"
        >
          <template #item="{ item, props: itemProps }">
            <VListItem
              v-bind="itemProps"
              :subtitle="item.raw.units ? t('alarms.form.units', { units: item.raw.units }) : undefined"
            />
          </template>
        </VSelect>

        <div v-if="type === 'basic'" class="d-flex flex-wrap ga-4">
          <VSelect
            v-model="draft.operator"
            :items="operators"
            class="flex-1-1-100"
            style="min-width: 220px"
            :label="t('alarms.form.operator')"
          />
          <VTextField
            v-model="draft.from"
            class="flex-1-1-0"
            style="min-width: 140px"
            type="text"
            inputmode="decimal"
            :label="isRange ? t('alarms.form.thresholdFrom') : t('alarms.form.threshold')"
            :suffix="draft.measure?.units"
          />
          <VTextField
            v-if="isRange"
            v-model="draft.to"
            class="flex-1-1-0"
            style="min-width: 140px"
            type="text"
            inputmode="decimal"
            :label="t('alarms.form.thresholdTo')"
            :suffix="draft.measure?.units"
          />
        </div>

        <div v-else class="d-flex flex-wrap ga-4">
          <VTextField
            v-model="draft.timeout"
            class="flex-1-1-0"
            style="min-width: 140px"
            type="text"
            inputmode="numeric"
            :label="t('alarms.form.timeout')"
            :hint="t('alarms.form.timeoutHint')"
            persistent-hint
          />
          <VSelect
            v-model="draft.timeoutUnit"
            :items="unitItems"
            class="flex-1-1-0"
            style="min-width: 140px"
            :label="t('alarms.form.timeoutUnit')"
          />
        </div>
      </div>
    </VCardText>
  </VCard>
</template>
