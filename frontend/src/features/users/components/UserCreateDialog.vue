<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ApiError } from '@/api/http'
import { t } from '@/i18n'
import { createUser, type AccessLevel, type OrganizationUser } from '../api/users'
import { ACCESS_LEVELS } from '../lib/access'

/**
 * Alta de un usuario en la organizacion. La cuenta nace en Keycloak con una contrasena aleatoria
 * que nadie conoce y el servidor envia el correo para que la persona fije la suya.
 */
const props = defineProps<{ organizationId: number }>()
const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{ created: [user: OrganizationUser, invitationSent: boolean] }>()

const form = reactive<{ name: string; email: string; accessLevel: AccessLevel }>({
  name: '',
  email: '',
  accessLevel: 'read',
})
const saving = ref(false)
const error = ref<string | null>(null)

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const nameRules = [(v: string) => !!v.trim() || t('users.create.nameRequired')]
const emailRules = [
  (v: string) => !!v.trim() || t('users.create.emailRequired'),
  (v: string) => EMAIL.test(v.trim()) || t('users.create.emailInvalid'),
]
const valid = computed(() => !!form.name.trim() && EMAIL.test(form.email.trim()))

watch(open, (isOpen) => {
  if (!isOpen) return
  form.name = ''
  form.email = ''
  form.accessLevel = 'read'
  error.value = null
})

async function submit() {
  if (!valid.value || saving.value) return
  saving.value = true
  error.value = null
  try {
    const result = await createUser(props.organizationId, {
      name: form.name.trim(),
      email: form.email.trim(),
      accessLevel: form.accessLevel,
    })
    emit('created', result.user, result.invitationSent)
    open.value = false
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 409
        ? t('users.create.duplicate')
        : t('users.create.failed')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <VDialog v-model="open" max-width="520" :persistent="saving">
    <VCard :title="t('users.create.title')">
      <VForm @submit.prevent="submit">
        <VCardText class="d-flex flex-column ga-4">
          <p class="text-body-2 text-medium-emphasis">{{ t('users.create.help') }}</p>

          <VTextField
            v-model="form.name"
            :label="t('users.create.name')"
            :rules="nameRules"
            autocomplete="off"
            prepend-inner-icon="mdi-account-outline"
            autofocus
          />
          <VTextField
            v-model="form.email"
            :label="t('users.create.email')"
            :rules="emailRules"
            type="email"
            autocomplete="off"
            prepend-inner-icon="mdi-email-outline"
          />

          <VRadioGroup
            v-model="form.accessLevel"
            :label="t('users.access.label')"
            hide-details
            class="mt-1"
          >
            <VRadio v-for="level in ACCESS_LEVELS" :key="level" :value="level">
              <template #label>
                <div>
                  <div class="text-body-2 font-weight-medium">{{ t(`users.access.${level}`) }}</div>
                  <div class="text-caption text-medium-emphasis">{{ t(`users.access.${level}.help`) }}</div>
                </div>
              </template>
            </VRadio>
          </VRadioGroup>

          <VAlert v-if="error" type="error" variant="tonal" role="alert">{{ error }}</VAlert>
        </VCardText>

        <VCardActions class="px-6 pb-4">
          <VSpacer />
          <VBtn variant="text" :disabled="saving" @click="open = false">
            {{ t('common.cancel') }}
          </VBtn>
          <VBtn type="submit" color="primary" variant="flat" :loading="saving" :disabled="!valid">
            {{ t('users.create.submit') }}
          </VBtn>
        </VCardActions>
      </VForm>
    </VCard>
  </VDialog>
</template>
