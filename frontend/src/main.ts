import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'
import './styles/app.scss'
import { initAuth, isAuthenticated } from './auth/keycloak'
import { useSessionStore } from './stores/session'
import { useCustomizationStore } from './stores/customization'

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

  const customization = useCustomizationStore()

  if (isAuthenticated()) {
    try {
      const user = await useSessionStore().load()
      // La personalizacion se aplica ANTES de montar: aplicada despues, la primera pintura
      // saldria con la paleta por defecto y cambiaria de color a la vista del usuario.
      if (user.organization?.id) await customization.load(user.organization.id)
    } catch (e) {
      console.error('No se ha podido cargar el usuario', e)
    }
  }

  // Aunque la carga haya fallado se aplica lo que haya en cache; si no hay nada, los colores
  // por defecto, que es exactamente lo que ya estaba en el tema.
  customization.applyTheme(vuetify.theme)

  app.use(router)
  await router.isReady()
  app.mount('#app')
}

void bootstrap()
