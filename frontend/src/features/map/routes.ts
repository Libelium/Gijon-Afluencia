import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/mapa',
    name: 'map',
    component: () => import('./views/MapView.vue'),
    meta: { title: 'Mapa' },
  },
]

export default routes
