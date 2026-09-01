<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '@/api/http'
import { t } from '@/i18n'
import PageHeader from '@/components/PageHeader.vue'
import AlarmConditionCard from '../components/AlarmConditionCard.vue'
import { createAlarm } from '../api/alarms'
import {
  conditionComplete,
  newConditionDraft,
  toInactivityCondition,
  toThresholdCondition,
} from '../lib/draft'
import type { AlarmFunction, AlarmType, NewAlarm } from '../types'

const router = useRouter()

const name = ref('')
const nameTouched = ref(false)
const type = ref<AlarmType>('basic')
const enabled = ref(true)
const combination = ref<AlarmFunction>('AND')
const conditions = ref([newConditionDraft()])
const saving = ref(false)
const error = ref<string | null>(null)

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

async function submit() {
  if (!canSubmit.value) return
  saving.value = true
  error.value = null
  try {
    const payload: NewAlarm = {
      name: name.value.trim(),
      type: type.value,
      // El servidor exige la combinacion siempre, tambien cuando no combina nada.
      function: showCombination.value ? combination.value : 'AND',
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
</script>

<template>
  <PageHeader
    :title="t('alarms.form.title')"
    :subtitle="t('alarms.form.subtitle')"
    icon="mdi-bell-plus-outline"
    back-to="/alarmas"
  />

  <div class="d-flex flex-column ga-4" style="max-width: 900px">
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
      {{ t('alarms.form.scopeNotice') }}
    </VAlert>

    <VAlert v-if="error" type="error" :text="error" role="alert" />

    <div class="d-flex flex-wrap ga-3 justify-end">
      <VBtn variant="text" to="/alarmas" :disabled="saving">{{ t('common.cancel') }}</VBtn>
      <VBtn
        color="primary"
        prepend-icon="mdi-check"
        :loading="saving"
        :disabled="!canSubmit"
        @click="submit"
      >
        {{ t('alarms.form.submit') }}
      </VBtn>
    </div>
  </div>
</template>
