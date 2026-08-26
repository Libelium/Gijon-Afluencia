import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/entidades',
    name: 'entities-list',
    component: () => import('./views/EntitiesListView.vue'),
    meta: { title: 'Entidades' },
  },
  {
    path: '/entidades/:id',
    name: 'entity-detail',
    component: () => import('./views/EntityDetailView.vue'),
    meta: { title: 'Entidad' },
  },
]

export default routes
