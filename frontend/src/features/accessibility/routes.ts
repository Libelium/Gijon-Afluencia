import type { RouteRecordRaw } from 'vue-router'

/**
 * La declaracion de accesibilidad es publica a proposito: el Real Decreto 1112/2018 exige que
 * se pueda consultar desde el sitio, y exigir sesion para leerla la haria inaccesible a quien
 * necesita justamente reclamar por no poder entrar.
 */
const routes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'accessibility',
    component: () => import('./views/AccessibilityView.vue'),
    meta: { public: true, title: 'Declaración de accesibilidad' },
  },
]

export default routes
