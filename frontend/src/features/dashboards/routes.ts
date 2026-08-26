import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/paneles',
    name: 'dashboards-list',
    component: () => import('./views/DashboardsListView.vue'),
    meta: { title: 'Paneles' },
  },
  {
    path: '/paneles/:id',
    name: 'dashboard-detail',
    component: () => import('./views/DashboardDetailView.vue'),
    props: true,
    meta: { title: 'Panel' },
  },
]

export default routes
