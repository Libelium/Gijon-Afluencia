import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'
import './styles/app.scss'
import { initAuth, isAuthenticated } from './auth/keycloak'
import { useSessionStore } from './stores/session'

const PUBLIC_PATHS = ['/login']

async function bootstrap() {
  const app = createApp(App)
  app.use(createPinia())
  app.use(vuetify)

  // La sesion se resuelve ANTES de montar: si se monta antes, la primera peticion sale sin token.
  const isPublic = PUBLIC_PATHS.some((p) => window.location.pathname.startsWith(p))
  try {
    await initAuth(isPublic)
  } catch (e) {
    console.error('No se ha podido inicializar la autenticación', e)
  }

  if (isAuthenticated()) {
    try {
      await useSessionStore().load()
    } catch (e) {
      console.error('No se ha podido cargar el usuario', e)
    }
  }

  app.use(router)
  await router.isReady()
  app.mount('#app')
}

void bootstrap()
