<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import PageHeader from '@/components/PageHeader.vue'
import AlarmConditionCard from '../components/AlarmConditionCard.vue'
import {
  createAlarm,
  getAlarm,
  getConditions,
  getInactivityConditions,
  saveConditions,
  saveInactivityConditions,
  updateAlarm,
} from '../api/alarms'
import {
  conditionComplete,
  fromInactivityCondition,
  fromThresholdCondition,
  newConditionDraft,
  toBulkInactivityCondition,
  toBulkThresholdCondition,
  toInactivityCondition,
  toThresholdCondition,
} from '../lib/draft'
import type { AlarmFunction, AlarmType, NewAlarm, UpdateAlarm } from '../types'

const route = useRoute()
const router = useRouter()

/** El id solo esta en la ruta de edicion; sin el, el formulario es de alta. */
const alarmId = computed(() => {
  const raw = Number(route.params.id)
  return Number.isInteger(raw) && raw > 0 ? raw : null
})
const isEdit = computed(() => alarmId.value !== null)
const backTo = computed(() => (alarmId.value !== null ? `/alarmas/${alarmId.value}` : '/alarmas'))

const name = ref('')
const nameTouched = ref(false)
const type = ref<AlarmType>('basic')
const enabled = ref(true)
const combination = ref<AlarmFunction>('AND')
const conditions = ref([newConditionDraft()])
const saving = ref(false)
const error = ref<string | null>(null)

// La carga previa solo ocurre al editar; en el alta el formulario arranca listo.
const loading = ref(false)
const loadError = ref<string | null>(null)

const typeItems = computed(() => [
  { value: 'basic' as const, title: t('alarms.type.basic'), subtitle: t('alarms.form.typeBasicHint') },
  {
    value: 'inactivity' as const,
    title: t('alarms.type.inactivity'),
    subtitle: t('alarms.form.typeInactivityHint'),
  },
])

const combinationItems = computed(() => [
  { value: 'AND' as const, title: t('alarms.form.fnAnd') },
  { value: 'OR' as const, title: t('alarms.form.fnOr') },
  { value: 'XOR' as const, title: t('alarms.form.fnXor') },
])

const nameError = computed(() =>
  nameTouched.value && !name.value.trim() ? t('alarms.form.nameRequired') : undefined,
)

/** La combinacion solo decide algo cuando hay varias condiciones que combinar. */
const showCombination = computed(() => type.value === 'basic' && conditions.value.length > 1)

const conditionsComplete = computed(() =>
  conditions.value.every((draft) => conditionComplete(draft, type.value)),
)

const canSubmit = computed(() => !!name.value.trim() && conditionsComplete.value && !saving.value)

function addCondition() {
  conditions.value.push(newConditionDraft())
}

function removeCondition(key: number) {
  conditions.value = conditions.value.filter((draft) => draft.key !== key)
}

async function loadForEdit(id: number) {
  loading.value = true
  loadError.value = null
  try {
    const alarm = await getAlarm(id)
    name.value = alarm.name ?? ''
    type.value = (alarm.type as AlarmType) || 'basic'
    enabled.value = !alarm.disabled
    combination.value = (alarm.function as AlarmFunction) || 'AND'

    // Las condiciones viven en una tabla u otra segun el tipo: se piden las del tipo de la alarma.
    if (type.value === 'inactivity') {
      const list = await getInactivityConditions(id)
      conditions.value = list.length ? list.map(fromInactivityCondition) : [newConditionDraft()]
    } else {
      const list = await getConditions(id)
      conditions.value = list.length ? list.map(fromThresholdCondition) : [newConditionDraft()]
    }
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!canSubmit.value) return
  saving.value = true
  error.value = null
  try {
    // El servidor exige la combinacion siempre, tambien cuando no combina nada.
    const fn: AlarmFunction = showCombination.value ? combination.value : 'AND'

    if (isEdit.value && alarmId.value !== null) {
      const id = alarmId.value
      // No se manda `up`: es estado de disparo, y reenviarlo reiniciaria una alarma ya disparada.
      const payload: UpdateAlarm = {
        name: name.value.trim(),
        type: type.value,
        function: fn,
        disabled: !enabled.value,
      }
      await updateAlarm(id, payload)
      // Las condiciones van por su endpoint bulk: el servidor no las toca en el PUT de la alarma.
      if (type.value === 'inactivity') {
        await saveInactivityConditions(id, conditions.value.map(toBulkInactivityCondition))
      } else {
        await saveConditions(id, conditions.value.map(toBulkThresholdCondition))
      }
      await router.push(`/alarmas/${id}`)
      return
    }

    const payload: NewAlarm = {
      name: name.value.trim(),
      type: type.value,
      function: fn,
      // Una alarma nace en reposo: `up` es estado de disparo, no una preferencia que elegir.
      up: false,
      disabled: !enabled.value,
      conditions: conditions.value.map((draft) =>
        type.value === 'inactivity' ? toInactivityCondition(draft) : toThresholdCondition(draft),
      ),
    }

    const id = await createAlarm(payload)
    await router.push(id ? `/alarmas/${id}` : '/alarmas')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (alarmId.value !== null) void loadForEdit(alarmId.value)
})
</script>

<template>
  <PageHeader
    :title="isEdit ? t('alarms.form.editTitle') : t('alarms.form.title')"
    :subtitle="isEdit ? t('alarms.form.editSubtitle') : t('alarms.form.subtitle')"
    :icon="isEdit ? 'mdi-bell-cog-outline' : 'mdi-bell-plus-outline'"
    :back-to="backTo"
  />

  <div v-if="loading" class="d-flex justify-center pa-8">
    <VProgressCircular indeterminate color="primary" :aria-label="t('common.loading')" />
  </div>

  <VAlert v-else-if="loadError" type="error" variant="tonal" role="alert" style="max-width: 900px">
    {{ loadError }}
    <template #append>
      <VBtn variant="text" @click="alarmId !== null && loadForEdit(alarmId)">
        {{ t('alarms.form.retry') }}
      </VBtn>
    </template>
  </VAlert>

  <div v-else class="d-flex flex-column ga-4" style="max-width: 900px">
    <VCard>
      <VCardText class="pa-4 pa-sm-6">
        <div class="d-flex flex-column ga-4">
          <VTextField
            v-model="name"
            :label="t('alarms.form.name')"
            :hint="t('alarms.form.nameHint')"
            persistent-hint
            maxlength="120"
            :error-messages="nameError"
            @input="nameTouched = true"
          />

          <VSelect
            v-model="type"
            :items="typeItems"
            :label="t('alarms.form.type')"
            :disabled="isEdit"
            :hint="isEdit ? t('alarms.form.typeLocked') : undefined"
            :persistent-hint="isEdit"
          >
            <template #item="{ item, props: itemProps }">
              <VListItem v-bind="itemProps" :subtitle="item.raw.subtitle" />
            </template>
          </VSelect>

          <VSwitch
            v-model="enabled"
            color="primary"
            hide-details
            :label="enabled ? t('alarms.form.enabled') : t('alarms.form.disabled')"
          />
          <p class="text-body-2 text-medium-emphasis mt-n2 mb-0">
            {{ enabled ? t('alarms.form.enabledHint') : t('alarms.form.disabledHint') }}
          </p>
        </div>
      </VCardText>
    </VCard>

    <VCard>
      <VCardText class="pa-4 pa-sm-6">
        <h2 class="text-subtitle-1 font-weight-medium mb-1">{{ t('alarms.form.conditions') }}</h2>
        <p class="text-body-2 text-medium-emphasis mb-4">
          {{ type === 'inactivity' ? t('alarms.form.conditionsInactivityHint') : t('alarms.form.conditionsBasicHint') }}
        </p>

        <VSelect
          v-if="showCombination"
          v-model="combination"
          :items="combinationItems"
          :label="t('alarms.form.combination')"
          class="mb-4"
        />

        <div class="d-flex flex-column ga-4">
          <AlarmConditionCard
            v-for="(draft, index) in conditions"
            :key="draft.key"
            :draft="draft"
            :type="type"
            :position="index + 1"
            :removable="conditions.length > 1"
            @remove="removeCondition(draft.key)"
          />
        </div>

        <VBtn
          variant="tonal"
          prepend-icon="mdi-plus"
          class="mt-4"
          @click="addCondition"
        >
          {{ t('alarms.form.addCondition') }}
        </VBtn>
      </VCardText>
    </VCard>

    <!-- Lo que este formulario no configura se dice aqui y no se descubre despues de guardar. -->
    <VAlert type="info" variant="tonal" density="comfortable">
      {{ isEdit ? t('alarms.form.scopeNoticeEdit') : t('alarms.form.scopeNotice') }}
    </VAlert>

    <VAlert v-if="error" type="error" :text="error" role="alert" />

    <div class="d-flex flex-wrap ga-3 justify-end">
      <VBtn variant="text" :to="backTo" :disabled="saving">{{ t('common.cancel') }}</VBtn>
      <VBtn
        color="primary"
        prepend-icon="mdi-check"
        :loading="saving"
        :disabled="!canSubmit"
        @click="submit"
      >
        {{ isEdit ? t('alarms.form.save') : t('alarms.form.submit') }}
      </VBtn>
    </div>
  </div>
</template>
