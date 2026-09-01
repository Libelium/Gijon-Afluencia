<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue'
import { useTheme } from 'vuetify'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { ApiError, errorMessage } from '@/api/http'
import { t } from '@/i18n'
import { useSessionStore } from '@/stores/session'
import { useCustomizationStore } from '@/stores/customization'
import {
  CUSTOMIZATION_PREFERENCES,
  DEFAULT_BRAND,
  fileToDataUri,
  isAllowedImageType,
  isHexColor,
  MAX_IMAGE_BYTES,
  type CustomizationPreference,
} from '@/customization/preferences'
import DOMPurify from 'dompurify'
import SettingsCard from '@/features/preferences/components/SettingsCard.vue'
import ColorField from '../components/ColorField.vue'
import ImageField from '../components/ImageField.vue'

const session = useSessionStore()
const customization = useCustomizationStore()
const theme = useTheme()

const organizationId = computed(() => session.user?.organization?.id ?? null)

/** Los campos que edita esta pantalla, agrupados como se presentan. */
const COLOR_FIELDS = [
  { name: 'themePrimaryColor', fallback: DEFAULT_BRAND.primary, nonText: false },
  { name: 'themeSecondaryColor', fallback: DEFAULT_BRAND.secondary, nonText: false },
  { name: 'themeLightPrimaryColor', fallback: DEFAULT_BRAND.accent, nonText: true },
] as const

const IMAGE_FIELDS = [
  { name: 'themeLightIcon', preview: 'light' },
  { name: 'themeDarkIcon', preview: 'dark' },
  { name: 'themeLoginIcon', preview: 'light' },
] as const

type Form = Record<CustomizationPreference, string>

function readStored(): Form {
  const v = customization.values
  const out = {} as Form
  for (const name of CUSTOMIZATION_PREFERENCES) out[name] = v[name] ?? ''
  for (const f of COLOR_FIELDS) if (!out[f.name]) out[f.name] = f.fallback
  return out
}

const stored = ref<Form>(readStored())
const form = reactive<Form>({ ...stored.value })

const error = ref('')
const saved = ref(false)

/** Lista de campos cambiados: gobierna el aviso, el boton y la marca de cada tarjeta. */
const changed = computed(() =>
  CUSTOMIZATION_PREFERENCES.filter((name) => form[name] !== stored.value[name]),
)

const groupPending = (names: readonly CustomizationPreference[]) =>
  names.some((n) => changed.value.includes(n))

const colorsValid = computed(() =>
  COLOR_FIELDS.every((f) => form[f.name] === '' || isHexColor(form[f.name])),
)

const canSave = computed(() => changed.value.length > 0 && colorsValid.value && !customization.saving)

/** Vista previa en vivo: se pinta con los colores del formulario, no con los ya guardados. */
const previewColors = computed(() => ({
  primary: isHexColor(form.themePrimaryColor) ? form.themePrimaryColor : DEFAULT_BRAND.primary,
  secondary: isHexColor(form.themeSecondaryColor)
    ? form.themeSecondaryColor
    : DEFAULT_BRAND.secondary,
}))

async function save() {
  error.value = ''
  saved.value = false
  try {
    // Una peticion por preferencia, que es lo que acepta el backend. Se envian solo las que
    // cambian para no reescribir valores intactos ni disparar validaciones innecesarias.
    for (const name of changed.value) {
      const value = form[name]
      if (value === '') await customization.clear(name)
      else await customization.save(name, value)
    }
    stored.value = { ...form }
    customization.applyTheme(theme)
    saved.value = true
  } catch (e) {
    error.value = e instanceof ApiError ? errorMessage(e) : String(e)
  }
}

function discard() {
  Object.assign(form, stored.value)
  error.value = ''
  saved.value = false
}

function resetColors() {
  form.themePrimaryColor = DEFAULT_BRAND.primary
  form.themeSecondaryColor = DEFAULT_BRAND.secondary
  form.themeLightPrimaryColor = DEFAULT_BRAND.accent
}

/**
 * Inserta una imagen en el HTML del pie, incrustada en base64.
 *
 * Es el camino que el saneador del backend admite a proposito (el validador de data URI de
 * HTMLPurifier acepta imagenes rasterizadas), y evita tener que alojar el fichero en otro sitio
 * para una tira de logotipos que no cambia nunca.
 */
const footerInput = ref<HTMLInputElement | null>(null)
const footerError = ref('')

async function insertFooterImage(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  footerError.value = ''
  if (!isAllowedImageType(file.type)) footerError.value = t('customization.image.badType')
  else if (file.size > MAX_IMAGE_BYTES) {
    footerError.value = t('customization.image.tooLarge', {
      size: `${Math.round(file.size / 1024)} KB`,
    })
  }
  if (footerError.value) {
    if (footerInput.value) footerInput.value.value = ''
    return
  }
  const uri = await fileToDataUri(file)
  const alt = file.name.replace(/\.[^.]+$/, '')
  form.themeCustomFooter =
    `${form.themeCustomFooter}\n<p><img src="${uri}" alt="${alt}" style="height:48px" /></p>`.trim()
  if (footerInput.value) footerInput.value.value = ''
}

/**
 * Una imagen incrustada son ~14 KB de base64 en una sola linea: leerla no aporta nada y tapa el
 * texto que si se edita a mano. Se cuentan aparte, se ofrece quitarlas de golpe, y lo que se ve
 * es el pie RENDERIZADO — que es lo que de verdad importa revisar.
 */
const DATA_URI = /<img\b[^>]*src="data:image\/[a-z]+;base64,[^"]*"[^>]*>/gi

const embeddedImages = computed(() => (form.themeCustomFooter.match(DATA_URI) ?? []).length)

const footerBytes = computed(() => new TextEncoder().encode(form.themeCustomFooter).length)

function stripFooterImages() {
  form.themeCustomFooter = form.themeCustomFooter.replace(DATA_URI, '').replace(/<(p|div)>\s*<\/\1>/gi, '').trim()
}

/** Mismo saneado que aplica AppFooter al pintar, para que la previsualizacion no engane. */
const footerPreview = computed(() =>
  form.themeCustomFooter
    ? DOMPurify.sanitize(form.themeCustomFooter, {
        ALLOWED_TAGS: ['p', 'br', 'b', 'strong', 'i', 'em', 'u', 's', 'sub', 'sup', 'ul', 'ol', 'li',
          'span', 'div', 'a', 'img', 'figure', 'table', 'thead', 'tbody', 'tr', 'td', 'th'],
        ALLOWED_ATTR: ['href', 'title', 'target', 'rel', 'src', 'alt', 'width', 'height', 'style', 'class'],
        ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|data:image\/(?:png|jpeg|gif|webp);base64,)/i,
      })
    : '',
)

onMounted(async () => {
  const id = organizationId.value
  if (id === null) return
  try {
    await customization.load(id)
    stored.value = readStored()
    Object.assign(form, stored.value)
  } catch (e) {
    error.value = e instanceof ApiError ? errorMessage(e) : String(e)
  }
})
</script>

<template>
  <div>
    <PageHeader
      icon="mdi-palette-outline"
      :title="t('customization.title')"
      :subtitle="t('customization.subtitle')"
    />

    <StateBlock
      v-if="organizationId === null"
      icon="mdi-domain-off"
      :title="t('customization.noOrganization')"
    />

    <template v-else>
      <VAlert v-if="error" type="error" class="mb-4" role="alert">{{ error }}</VAlert>
      <VAlert v-if="saved && changed.length === 0" type="success" class="mb-4" role="status">
        {{ t('customization.saved') }}
      </VAlert>

      <div class="d-flex flex-column ga-4">
        <SettingsCard
          icon="mdi-palette-swatch-outline"
          :title="t('customization.section.colors')"
          :help="t('customization.section.colors.help')"
          :pending="groupPending(COLOR_FIELDS.map((f) => f.name))"
        >
          <div class="d-flex flex-column ga-6">
            <ColorField
              v-for="f in COLOR_FIELDS"
              :key="f.name"
              v-model="form[f.name]"
              :label="t(`customization.field.${f.name}`)"
              :hint="t(`customization.field.${f.name}.hint`)"
              :non-text="f.nonText"
            />
          </div>
          <VBtn variant="text" size="small" class="mt-4" @click="resetColors">
            {{ t('customization.reset') }}
          </VBtn>
        </SettingsCard>

        <SettingsCard
          icon="mdi-eye-outline"
          :title="t('customization.preview.title')"
          :help="t('customization.preview.help')"
        >
          <div class="d-flex flex-wrap align-center ga-3">
            <VBtn :style="{ background: previewColors.primary, color: '#fff' }">
              {{ t('customization.preview.button') }}
            </VBtn>
            <VBtn variant="outlined" :style="{ color: previewColors.secondary, borderColor: previewColors.secondary }">
              {{ t('customization.preview.secondary') }}
            </VBtn>
            <VChip :style="{ background: previewColors.primary, color: '#fff' }">
              {{ t('customization.preview.chip') }}
            </VChip>
            <a href="#" :style="{ color: previewColors.primary }" @click.prevent>
              {{ t('customization.preview.link') }}
            </a>
          </div>
        </SettingsCard>

        <SettingsCard
          icon="mdi-image-outline"
          :title="t('customization.section.logos')"
          :help="t('customization.section.logos.help')"
          :pending="groupPending(IMAGE_FIELDS.map((f) => f.name))"
        >
          <div class="d-flex flex-column ga-6">
            <ImageField
              v-for="f in IMAGE_FIELDS"
              :key="f.name"
              v-model="form[f.name]"
              :label="t(`customization.field.${f.name}`)"
              :hint="t(`customization.field.${f.name}.hint`)"
              :preview="f.preview"
            />
          </div>
        </SettingsCard>

        <SettingsCard
          icon="mdi-page-layout-footer"
          :title="t('customization.section.footer')"
          :help="t('customization.section.footer.help')"
          :pending="groupPending(['themeCustomFooter'])"
        >
          <VTextarea
            v-model="form.themeCustomFooter"
            :label="t('customization.field.themeCustomFooter')"
            :placeholder="t('customization.footer.placeholder')"
            :hint="t('customization.footer.imageHint')"
            persistent-hint
            rows="6"
            no-resize
            spellcheck="false"
            class="footer-source"
          />

          <div class="d-flex flex-wrap align-center ga-2 mt-3">
            <VBtn
              variant="tonal"
              size="small"
              prepend-icon="mdi-image-plus"
              @click="footerInput?.click()"
            >
              {{ t('customization.footer.insertImage') }}
            </VBtn>
            <VBtn
              v-if="embeddedImages > 0"
              variant="text"
              size="small"
              color="error"
              prepend-icon="mdi-image-off-outline"
              @click="stripFooterImages"
            >
              {{ t('customization.footer.stripImages') }}
            </VBtn>
            <VSpacer />
            <span v-if="embeddedImages > 0" class="text-caption text-medium-emphasis">
              {{ t('customization.footer.embedded', { count: embeddedImages, size: Math.round(footerBytes / 1024) }) }}
            </span>
          </div>

          <VDivider class="my-4" />

          <div class="text-body-2 font-weight-medium mb-2">{{ t('customization.footer.preview') }}</div>
          <div class="footer-preview text-caption text-medium-emphasis">
            <!-- eslint-disable-next-line vue/no-v-html -- saneado con DOMPurify arriba -->
            <div v-if="footerPreview" v-html="footerPreview" />
            <span v-else>{{ t('customization.footer.previewEmpty') }}</span>
          </div>
          <input
            ref="footerInput"
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            class="d-none"
            @change="insertFooterImage"
          />
          <VAlert v-if="footerError" type="error" density="compact" class="mt-3" role="alert">
            {{ footerError }}
          </VAlert>
        </SettingsCard>
      </div>

      <VCard class="mt-4" color="surface-variant">
        <VCardText class="d-flex flex-wrap align-center ga-3 pa-4">
          <span class="text-body-2 flex-grow-1">
            <template v-if="changed.length === 0">{{ t('customization.clean') }}</template>
            <template v-else-if="changed.length === 1">{{ t('customization.dirtyOne') }}</template>
            <template v-else>{{ t('customization.dirtyMany', { count: changed.length }) }}</template>
          </span>
          <VBtn variant="text" :disabled="changed.length === 0" @click="discard">
            {{ t('customization.discard') }}
          </VBtn>
          <VBtn color="primary" :loading="customization.saving" :disabled="!canSave" @click="save">
            {{ t('customization.save') }}
          </VBtn>
        </VCardText>
      </VCard>
    </template>
  </div>
</template>

<style scoped>
/* El HTML del pie puede llevar un data URI de 14 KB en una linea: se deja desplazar en horizontal
   dentro del campo en vez de romper la maquetacion o crecer sin fin. */
.footer-source :deep(textarea) {
  white-space: pre;
  overflow-x: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
}

/* Mismo alto fijo y mismos limites que el pie de verdad (`components/AppFooter.vue`): si la
   previsualizacion creciera con el contenido, ensenaria un pie que no existe y nadie veria que
   su HTML no cabe. */
.footer-preview {
  --app-footer-height: 72px;

  display: flex;
  align-items: center;
  block-size: var(--app-footer-height);
  padding-inline: 12px;
  border: 1px dashed rgb(var(--v-theme-outline-strong));
  border-radius: 12px;
  overflow: auto;
}

.footer-preview :deep(img) {
  max-inline-size: 100%;
  max-block-size: calc(var(--app-footer-height) - 16px);
  block-size: auto;
  inline-size: auto;
  object-fit: contain;
  vertical-align: middle;
}

.footer-preview :deep(p) {
  margin-bottom: 0;
}
</style>
