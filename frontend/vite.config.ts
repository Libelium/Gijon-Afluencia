import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

export default defineConfig({
  plugins: [vue(), vuetify({ autoImport: true })],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    // El backend no admite comodines en CORS y el cliente OIDC valida el redirect URI:
    // el origen de desarrollo debe estar dado de alta en ambos.
    port: 20600,
    host: true,
  },
})
