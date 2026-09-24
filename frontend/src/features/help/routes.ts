import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/ayuda',
    name: 'help',
    component: () => import('./views/HelpView.vue'),
    meta: { title: 'Ayuda' },
  },
]

export default routes
