import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { http } from '@/api/http'
import type { CurrentUser, UserPreferences } from '@/types'

export const useSessionStore = defineStore('session', () => {
  const user = ref<CurrentUser | null>(null)
  const loading = ref(false)

  const preferences = computed<UserPreferences>(() => user.value?.preferences ?? {})
  const timeZone = computed(() => preferences.value.timeZone || 'Europe/Madrid')
  const displayName = computed(() => user.value?.name || user.value?.email || '')

  /** GET /user ya devuelve las preferencias resueltas: no hace falta una segunda llamada. */
  async function load() {
    loading.value = true
    try {
      const { data } = await http.get<CurrentUser>('/user')
      user.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  function setPreference(name: string, value: string) {
    if (user.value) user.value.preferences = { ...user.value.preferences, [name]: value }
  }

  return { user, loading, preferences, timeZone, displayName, load, setPreference }
})
