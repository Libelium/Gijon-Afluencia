<script setup lang="ts">
import { watch, onMounted } from 'vue'
import { useTheme } from 'vuetify'
import { useUiStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'

const ui = useUiStore()
const session = useSessionStore()
const theme = useTheme()

function apply(name: string) {
  theme.global.name.value = name
}

onMounted(() => {
  // La preferencia del usuario gana sobre lo guardado en el navegador, pero solo la primera vez.
  const pref = session.preferences.displayskinMode
  if (pref === 'dark' || pref === 'light') ui.theme = pref
  else if (pref === 'system')
    ui.theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  apply(ui.theme)
})

watch(() => ui.theme, apply)
</script>

<template>
  <RouterView />
</template>
