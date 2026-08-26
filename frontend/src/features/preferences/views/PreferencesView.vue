<script setup lang="ts">
import { computed, onUnmounted, reactive, ref } from 'vue'
import { useDisplay } from 'vuetify'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { ApiError, errorMessage } from '@/api/http'
import { savePreference } from '@/api/user'
import { t } from '@/i18n'
import { useSessionStore } from '@/stores/session'
import { useUiStore, type ThemeName } from '@/stores/ui'
import SettingsCard from '../components/SettingsCard.vue'
import {
  DATETIME_FORMATS,
  DEFAULTS,
  LANGUAGES,
  NUMBER_FORMATS,
  PREFERENCE_NAMES,
  THEME_MODES,
  browserTimeZone,
  labelFor,
  offsetLabel,
  themeModeOr,
  timeZoneChoices,
  translated,
  withStored,
  type PreferenceName,
  type PreferenceValues,
} from '../options'
import {
  previewDate,
  previewDateTime,
  previewNumber,
  previewRelative,
  previewTime,
} from '../preview'

const session = useSessionStore()
const ui = useUiStore()
// En pantalla estrecha los tres temas no caben en fila sin que la etiqueta toque el borde:
// se apilan a lo ancho y el icono pasa a ir junto al texto.
const { xs } = useDisplay()

const themeModes = translated(THEME_MODES)
const detectedZone = browserTimeZone()

const SAMPLE_NUMBER = 1234567.891
const SAMPLE_PAST = new Date(Date.now() - 5 * 3600_000).toISOString()

/** Cada tarjeta del formulario y las preferencias que agrupa, para senalar la que tiene cambios. */
const GROUPS = {
  locale: ['language', 'timeZone'],
  formats: ['datetimeFormat', 'numberFormat'],
  appearance: ['displayskinMode'],
} as const satisfies Record<string, readonly PreferenceName[]>

function readStored(): PreferenceValues {
  const p = session.preferences
  return {
    language: p.language || DEFAULTS.language,
    timeZone: p.timeZone || DEFAULTS.timeZone,
    datetimeFormat: p.datetimeFormat || DEFAULTS.datetimeFormat,
    numberFormat: p.numberFormat || DEFAULTS.numberFormat,
    // Sin preferencia guardada, el tema en vigor es el que ya tiene el navegador.
    displayskinMode: themeModeOr(p.displayskinMode, ui.theme),
  }
}

const stored = ref<PreferenceValues>(readStored())
const form = reactive<PreferenceValues>({ ...stored.value })

// Un valor guardado ajeno al catalogo se anade a la lista para que se vea con etiqueta.
const languages = computed(() => withStored(translated(LANGUAGES), stored.value.language))
const datetimeFormats = computed(() =>
  withStored(translated(DATETIME_FORMATS), stored.value.datetimeFormat),
)
const numberFormats = computed(() =>
  withStored(translated(NUMBER_FORMATS), stored.value.numberFormat),
)
const timeZones = computed(() => timeZoneChoices(stored.value.timeZone))

const fieldErrors = reactive<Partial<Record<PreferenceName, string>>>({})
const saving = ref(false)
const loadError = ref<string | null>(null)

const changed = computed(() => PREFERENCE_NAMES.filter((name) => form[name] !== stored.value[name]))
const dirty = computed(() => changed.value.length > 0)
const noSession = computed(() => !session.loading && !loadError.value && !session.user)

const pending = (group: keyof typeof GROUPS) =>
  GROUPS[group].some((name) => changed.value.includes(name))

const dirtyText = computed(() => {
  if (!dirty.value) return t('preferences.clean')
  return changed.value.length === 1
    ? t('preferences.dirtyOne')
    : t('preferences.dirtyMany', { count: changed.value.length })
})

// El reloj de la vista previa avanza cada segundo: es lo que hace evidente que es en vivo.
const now = ref(new Date().toISOString())
const ticker = window.setInterval(() => (now.value = new Date().toISOString()), 1000)
onUnmounted(() => window.clearInterval(ticker))

const resolvedTheme = computed(() => resolveTheme(form.displayskinMode))

const systemHint = computed(() =>
  t('preferences.theme.systemHint', {
    mode: t(`preferences.theme.${resolvedTheme.value === 'dark' ? 'darkWord' : 'lightWord'}`),
  }),
)

const zoneLabel = computed(
  () => `${form.timeZone.replace(/_/g, ' ')} · ${offsetLabel(form.timeZone)}`,
)

const previewDateTimeText = computed(() =>
  previewDateTime(now.value, form.timeZone, form.datetimeFormat),
)

const previewRows = computed(() => [
  {
    label: t('preferences.preview.date'),
    value: previewDate(now.value, form.timeZone, form.datetimeFormat),
  },
  {
    label: t('preferences.preview.time'),
    value: previewTime(now.value, form.timeZone, form.datetimeFormat),
  },
  {
    label: t('preferences.preview.number'),
    value: previewNumber(SAMPLE_NUMBER, form.numberFormat),
  },
  {
    label: t('preferences.preview.relative'),
    value: previewRelative(SAMPLE_PAST, form.timeZone),
  },
])

const snack = reactive({
  open: false,
  color: 'success',
  title: '',
  lines: [] as string[],
  timeout: 4000,
})

function resolveTheme(mode: string): ThemeName {
  if (mode === 'dark' || mode === 'light') return mode
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function clearErrors() {
  for (const name of PREFERENCE_NAMES) delete fieldErrors[name]
}

function discard() {
  Object.assign(form, stored.value)
  clearErrors()
  snack.open = false
}

async function reload() {
  loadError.value = null
  try {
    await session.load()
    stored.value = readStored()
    discard()
  } catch (e) {
    loadError.value = errorMessage(e)
  }
}

async function save() {
  const userId = session.user?.id
  if (!userId) {
    loadError.value = t('preferences.noSession')
    return
  }

  const names = [...changed.value]
  if (!names.length) return

  clearErrors()
  saving.value = true
  const results = await Promise.allSettled(
    names.map((name) => savePreference(userId, name, form[name])),
  )
  saving.value = false

  const failures: string[] = []
  const applied: PreferenceValues = { ...stored.value }

  results.forEach((result, i) => {
    const name = names[i]
    if (result.status === 'fulfilled') {
      applied[name] = form[name]
      session.setPreference(name, form[name])
      if (name === 'displayskinMode') ui.theme = resolveTheme(form[name])
      return
    }
    const forced = result.reason instanceof ApiError && result.reason.kind === 'forbidden'
    const reason = forced ? t('preferences.forced') : errorMessage(result.reason)
    fieldErrors[name] = reason
    // Un ajuste impuesto por la organizacion no se aceptara nunca: se devuelve a su valor real
    // para que el formulario no muestre algo que el servidor no tiene.
    if (forced) form[name] = stored.value[name]
    failures.push(t('preferences.failedItem', { label: labelFor(name), reason }))
  })

  stored.value = applied
  report(names.length, failures)
}

function report(total: number, failures: string[]) {
  const ok = total - failures.length
  snack.lines = failures
  if (!failures.length) {
    snack.color = 'success'
    snack.title = t('preferences.saved')
  } else if (!ok) {
    snack.color = 'error'
    snack.title = t('preferences.noneSaved')
  } else {
    snack.color = 'warning'
    snack.title = t('preferences.partialSaved', { ok, total })
  }
  // Un fallo no debe desaparecer solo: el usuario tiene que poder leer cual ha sido.
  snack.timeout = failures.length ? -1 : 4000
  snack.open = true
}
</script>

<template>
  <div>
    <PageHeader :title="t('preferences.title')" :subtitle="t('preferences.subtitle')" />

    <StateBlock
      :loading="session.loading"
      :error="loadError"
      :empty="noSession"
      :empty-text="t('preferences.noSession')"
      empty-icon="mdi-account-off-outline"
      skeleton="card"
      @retry="reload"
    >
      <template #empty-action>
        <VBtn color="primary" variant="tonal" prepend-icon="mdi-refresh" @click="reload">
          {{ t('preferences.reload') }}
        </VBtn>
      </template>

      <VRow>
        <VCol cols="12" md="7">
          <div class="d-flex flex-column ga-6">
            <SettingsCard
              icon="mdi-translate"
              :title="t('preferences.section.locale')"
              :help="t('preferences.section.locale.help')"
              :pending="pending('locale')"
            >
              <div class="d-flex flex-column ga-6">
                <VSelect
                  v-model="form.language"
                  :items="languages"
                  item-title="title"
                  item-value="value"
                  :label="t('preferences.field.language')"
                  :hint="t('preferences.field.language.hint')"
                  :error-messages="fieldErrors.language"
                  persistent-hint
                  prepend-inner-icon="mdi-translate"
                />

                <VAutocomplete
                  v-model="form.timeZone"
                  :items="timeZones"
                  item-title="title"
                  item-value="value"
                  :label="t('preferences.field.timeZone')"
                  :hint="t('preferences.field.timeZone.hint', { zone: detectedZone })"
                  :error-messages="fieldErrors.timeZone"
                  persistent-hint
                  auto-select-first
                  prepend-inner-icon="mdi-earth"
                >
                  <template #item="{ props: itemProps, item }">
                    <VListItem v-bind="itemProps" :subtitle="offsetLabel(item.raw.value)" />
                  </template>
                </VAutocomplete>
              </div>
            </SettingsCard>

            <SettingsCard
              icon="mdi-format-list-numbered"
              :title="t('preferences.section.formats')"
              :help="t('preferences.section.formats.help')"
              :pending="pending('formats')"
            >
              <div class="d-flex flex-column ga-4">
                <VSelect
                  v-model="form.datetimeFormat"
                  :items="datetimeFormats"
                  item-title="title"
                  item-value="value"
                  :label="t('preferences.field.datetimeFormat')"
                  :error-messages="fieldErrors.datetimeFormat"
                  prepend-inner-icon="mdi-calendar-outline"
                />

                <VSelect
                  v-model="form.numberFormat"
                  :items="numberFormats"
                  item-title="title"
                  item-value="value"
                  :label="t('preferences.field.numberFormat')"
                  :error-messages="fieldErrors.numberFormat"
                  prepend-inner-icon="mdi-numeric"
                />
              </div>
            </SettingsCard>

            <SettingsCard
              icon="mdi-palette-outline"
              :title="t('preferences.section.appearance')"
              :help="t('preferences.section.appearance.help')"
              :pending="pending('appearance')"
            >
              <div class="text-caption text-medium-emphasis mb-2">
                {{ t('preferences.field.displayskinMode') }}
              </div>

              <VBtnToggle
                v-model="form.displayskinMode"
                :aria-label="t('preferences.field.displayskinMode')"
                mandatory
                variant="outlined"
                color="primary"
                class="w-100 h-auto ga-3 flex-column flex-sm-row"
              >
                <VBtn
                  v-for="mode in themeModes"
                  :key="mode.value"
                  :value="mode.value"
                  :prepend-icon="mode.icon"
                  :stacked="!xs"
                  rounded="lg"
                  class="flex-1-1-0 py-3 py-sm-4"
                >
                  {{ mode.title }}
                </VBtn>
              </VBtnToggle>

              <p
                v-if="form.displayskinMode === 'system'"
                class="text-caption text-medium-emphasis mt-3"
              >
                {{ systemHint }}
              </p>
              <p v-if="fieldErrors.displayskinMode" class="text-caption text-error mt-3">
                {{ fieldErrors.displayskinMode }}
              </p>
            </SettingsCard>
          </div>
        </VCol>

        <VCol cols="12" md="5" class="order-first order-md-last">
          <VCard class="bg-surface-variant">
            <VCardText class="pa-4 pa-sm-6">
              <div class="d-flex align-center ga-3">
                <VIcon icon="mdi-eye-outline" size="20" class="text-primary" />
                <h2 class="text-subtitle-2 flex-grow-1 min-w-0">
                  {{ t('preferences.preview.title') }}
                </h2>
              </div>

              <p class="text-body-2 text-medium-emphasis mt-2 mb-5">
                {{ t('preferences.preview.help') }}
              </p>

              <div class="bg-surface border rounded-lg d-flex flex-column ga-1 pa-4 mb-5">
                <span class="text-caption text-medium-emphasis">
                  {{ t('preferences.preview.datetime') }}
                </span>
                <span class="text-h6 text-primary">{{ previewDateTimeText }}</span>
                <span class="d-flex align-center ga-1 text-caption text-medium-emphasis min-w-0">
                  <VIcon icon="mdi-earth" size="14" />
                  <span class="text-truncate" :title="zoneLabel">{{ zoneLabel }}</span>
                </span>
              </div>

              <div class="d-flex flex-column ga-3">
                <div
                  v-for="row in previewRows"
                  :key="row.label"
                  class="d-flex flex-wrap align-baseline justify-space-between ga-3"
                >
                  <span class="text-caption text-medium-emphasis">{{ row.label }}</span>
                  <span class="text-body-2 font-weight-medium text-right min-w-0">
                    {{ row.value }}
                  </span>
                </div>
              </div>

              <VDivider class="my-4" />

              <p class="text-caption text-medium-emphasis">
                {{ t('preferences.preview.note') }}
              </p>
            </VCardText>
          </VCard>
        </VCol>
      </VRow>

      <!-- La barra queda al alcance sin recorrer todo el formulario; la banda opaca evita que
           el contenido se vea asomar por debajo de la tarjeta al desplazarse. -->
      <div class="position-sticky bottom-0 bg-background pt-3 pb-4 mt-3">
        <VCard>
          <VCardText class="d-flex flex-wrap align-center justify-space-between ga-4 pa-4">
            <div class="d-flex align-center ga-2 min-w-0">
              <VIcon
                :icon="dirty ? 'mdi-alert-circle-outline' : 'mdi-check-circle-outline'"
                :color="dirty ? 'warning' : 'success'"
                size="20"
              />
              <span class="text-body-2 text-medium-emphasis">{{ dirtyText }}</span>
            </div>

            <div
              class="d-flex flex-column flex-sm-row align-stretch align-sm-center ga-3 w-100 w-sm-auto"
            >
              <VBtn
                variant="text"
                :disabled="!dirty || saving"
                prepend-icon="mdi-undo-variant"
                @click="discard"
              >
                {{ t('preferences.discard') }}
              </VBtn>
              <VBtn
                color="primary"
                :disabled="!dirty"
                :loading="saving"
                prepend-icon="mdi-content-save-outline"
                @click="save"
              >
                {{ t('preferences.save') }}
              </VBtn>
            </div>
          </VCardText>
        </VCard>
      </div>
    </StateBlock>

    <VSnackbar
      v-model="snack.open"
      :color="snack.color"
      :timeout="snack.timeout"
      location="bottom"
      multi-line
    >
      <div class="d-flex flex-column ga-1">
        <span class="font-weight-medium">{{ snack.title }}</span>
        <span v-for="line in snack.lines" :key="line" class="text-body-2">{{ line }}</span>
      </div>
      <template #actions>
        <VBtn variant="text" @click="snack.open = false">{{ t('common.close') }}</VBtn>
      </template>
    </VSnackbar>
  </div>
</template>
