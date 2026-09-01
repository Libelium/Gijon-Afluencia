import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/personalizacion',
    name: 'customization',
    component: () => import('./views/CustomizationView.vue'),
    meta: { title: 'Personalización' },
  },
]

export default routes
