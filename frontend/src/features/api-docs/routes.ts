import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/api',
    name: 'api-docs',
    component: () => import('./views/ApiDocsView.vue'),
    meta: { title: 'API' },
  },
]

export default routes
