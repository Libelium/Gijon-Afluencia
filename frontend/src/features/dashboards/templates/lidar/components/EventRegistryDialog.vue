<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { ApiError, errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { EVENT_CATALOG } from '../eventSimulation'
import {
  registerEvent,
  toNewEvent,
  touchesLearnedDays,
  type RegistryDraft,
  type RegistryEvent,
  type RegistryTarget,
} from '../predictionEvents'

const props = defineProps<{
  /** El evento que se propone; null, cerrado. */
  draft: RegistryDraft | null
  target: RegistryTarget
  zoneUrn: string
  zoneName?: string
  timeZone: string
}>()
const emit = defineEmits<{ close: []; saved: [event: RegistryEvent, draft: RegistryDraft] }>()

const form = ref<RegistryDraft | null>(null)
const saving = ref(false)
const error = ref<string | null>(null)

watch(
  () => props.draft,
  (draft) => {
    form.value = draft ? { ...draft } : null
    error.value = null
  },
  { immediate: true },
)

const open = computed({
  get: () => props.draft !== null,
  set: (value) => {
    if (!value) emit('close')
  },
})

const kindItems = EVENT_CATALOG.map((spec) => ({ title: t(`dashboards.lidar.scenario.kind.${spec.kind}`), value: spec.kind }))
const hourLabel = (h: number) => `${String(h).padStart(2, '0')}:00`
const startItems = Array.from({ length: 24 }, (_, h) => ({ title: hourLabel(h), value: h }))
const endItems = Array.from({ length: 24 }, (_, i) => ({ title: hourLabel(i + 1), value: i + 1 }))
const zoneItems = computed(() => [
  { title: props.zoneName || t('dashboards.lidar.registry.thisZone'), value: true },
  { title: t('dashboards.lidar.registry.allZones'), value: false },
])

const datesError = computed(() =>
  form.value && form.value.endDate && form.value.endDate < form.value.date
    ? t('dashboards.lidar.registry.endBeforeStart')
    : undefined,
)
const hoursError = computed(() =>
  form.value && form.value.endHour <= form.value.startHour ? t('dashboards.lidar.registry.endHourBeforeStart') : undefined,
)
const learned = computed(() => !!form.value?.date && touchesLearnedDays(form.value.date, props.timeZone))
const canSubmit = computed(() => !!form.value?.date && !datesError.value && !hoursError.value)

async function submit() {
  const draft = form.value
  if (!draft || !canSubmit.value) return
  saving.value = true
  error.value = null
  try {
    const saved = await registerEvent(props.target, toNewEvent(draft, props.zoneUrn))
    emit('saved', saved, draft)
  } catch (e) {
    error.value =
      e instanceof ApiError && e.kind === 'forbidden' ? t('dashboards.lidar.registry.forbidden') : errorMessage(e)
  } finally {
    saving.value = false
  }
}

/** Asocia el dialogo con su titulo para los lectores de pantalla (WCAG 4.1.2). */
const titleId = useId()
</script>

<template>
  <VDialog v-model="open" max-width="560" :persistent="saving" :aria-labelledby="titleId">
    <VCard v-if="form">
      <VCardTitle :id="titleId" class="text-h6 pa-4">{{ t('dashboards.lidar.registry.dialogTitle') }}</VCardTitle>

      <VDivider />

      <VCardText class="pa-4">
        <form class="d-flex flex-column ga-4" @submit.prevent="submit">
          <div class="d-flex flex-wrap ga-3">
            <VTextField
              v-model="form.date"
              type="date"
              :label="t('dashboards.lidar.registry.from')"
              density="comfortable"
              style="flex: 1 1 180px"
              hide-details="auto"
            />
            <VTextField
              v-model="form.endDate"
              type="date"
              :min="form.date"
              :label="t('dashboards.lidar.registry.to')"
              density="comfortable"
              style="flex: 1 1 180px"
              :error-messages="datesError"
              hide-details="auto"
            />
          </div>
          <VSelect
            v-model="form.kind"
            :items="kindItems"
            :label="t('dashboards.lidar.scenario.kind')"
            density="comfortable"
            hide-details
          />
          <div class="d-flex flex-wrap ga-3">
            <VSelect
              v-model="form.startHour"
              :items="startItems"
              :label="t('dashboards.lidar.registry.startHour')"
              density="comfortable"
              style="flex: 1 1 150px"
              hide-details
            />
            <VSelect
              v-model="form.endHour"
              :items="endItems"
              :label="t('dashboards.lidar.registry.endHour')"
              density="comfortable"
              style="flex: 1 1 150px"
              :error-messages="hoursError"
              hide-details="auto"
            />
          </div>
          <VSelect
            v-model="form.onlyThisZone"
            :items="zoneItems"
            :label="t('dashboards.lidar.registry.zones')"
            density="comfortable"
            hide-details
          />
          <VTextarea
            v-model="form.notes"
            :label="t('dashboards.lidar.registry.notes')"
            rows="2"
            auto-grow
            maxlength="500"
            density="comfortable"
            hide-details
          />

          <div class="text-caption text-medium-emphasis">{{ t('dashboards.lidar.registry.dialogHint') }}</div>
          <VAlert v-if="learned" type="warning" variant="tonal" density="compact" :text="t('dashboards.lidar.registry.learned')" />
          <VAlert v-if="error" type="error" role="alert" :text="error" />
        </form>
      </VCardText>

      <VDivider />

      <VCardActions class="pa-4 ga-3 justify-end">
        <VBtn variant="text" :disabled="saving" @click="open = false">{{ t('common.cancel') }}</VBtn>
        <VBtn
          color="primary"
          prepend-icon="mdi-calendar-check"
          :loading="saving"
          :disabled="!canSubmit"
          @click="submit"
        >
          {{ t('dashboards.lidar.registry.register') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
