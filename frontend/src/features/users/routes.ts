import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/usuarios',
    name: 'users',
    component: () => import('./views/UsersView.vue'),
    meta: { title: 'Usuarios' },
  },
]

export default routes
