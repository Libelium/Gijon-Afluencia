<script setup lang="ts">
import { ref, watch } from 'vue'
import { ApiError } from '@/api/http'
import { savePreference } from '@/api/user'
import { t } from '@/i18n'
import { useSessionStore } from '@/stores/session'
import SettingsCard from './SettingsCard.vue'

/**
 * Segundo factor por correo. No entra en el formulario de «Guardar cambios»: es un ajuste de
 * seguridad y se aplica al pulsar, porque el backend lo refleja en Keycloak (rol del realm que
 * activa el paso *Conditional Email OTP* del flujo de acceso) y un cambio a medio guardar no
 * tendria sentido.
 */
const session = useSessionStore()

// Estado propio del interruptor: si el guardado falla se devuelve al valor real. Atado solo a la
// sesion, Vuetify dejaria el interruptor en la posicion pulsada aunque nada hubiera cambiado.
const active = ref(session.preferences.activeMFA === 'true')
watch(
  () => session.preferences.activeMFA,
  (value) => (active.value = value === 'true'),
)
const saving = ref(false)
const forced = ref(false)
const error = ref<string | null>(null)
const done = ref<string | null>(null)

async function toggle(value: boolean | null) {
  const userId = session.user?.id
  if (!userId || saving.value) return

  error.value = null
  done.value = null
  saving.value = true
  try {
    await savePreference(userId, 'activeMFA', value ? 'true' : 'false')
    session.setPreference('activeMFA', value ? 'true' : 'false')
    done.value = t(value ? 'preferences.mfa.enabled' : 'preferences.mfa.disabled')
  } catch (e) {
    // La organizacion lo impone: queda activo y el interruptor se bloquea.
    if (e instanceof ApiError && e.kind === 'forbidden') {
      forced.value = true
      session.setPreference('activeMFA', 'true')
    } else {
      error.value = t('preferences.mfa.failed')
    }
    active.value = session.preferences.activeMFA === 'true'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <SettingsCard
    icon="mdi-shield-lock-outline"
    :title="t('preferences.section.security')"
    :help="t('preferences.section.security.help')"
  >
    <VSwitch
      v-model="active"
      :label="t('preferences.field.activeMFA')"
      :hint="t('preferences.field.activeMFA.hint', { email: session.user?.email ?? '' })"
      :loading="saving"
      :disabled="saving || forced"
      :error-messages="error ?? undefined"
      color="primary"
      inset
      persistent-hint
      @update:model-value="toggle"
    />

    <p v-if="forced" class="text-caption text-medium-emphasis mt-3">
      {{ t('preferences.mfa.forced') }}
    </p>
    <p v-else-if="done" role="status" class="text-caption text-success mt-3">
      {{ done }}
    </p>
  </SettingsCard>
</template>
