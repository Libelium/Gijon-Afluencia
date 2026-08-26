import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/preferencias',
    name: 'preferences',
    component: () => import('./views/PreferencesView.vue'),
    meta: { title: 'Preferencias' },
  },
]

export default routes
