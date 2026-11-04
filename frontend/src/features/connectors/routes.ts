import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/conectores',
    name: 'connectors-list',
    component: () => import('./views/ConnectorsListView.vue'),
    meta: { title: 'Conectores' },
  },
  {
    path: '/conectores/nuevo',
    name: 'connector-create',
    component: () => import('./views/ConnectorFormView.vue'),
    meta: { title: 'Nuevo conector' },
  },
  {
    path: '/conectores/:id',
    name: 'connector-detail',
    component: () => import('./views/ConnectorDetailView.vue'),
    props: true,
    meta: { title: 'Conector' },
  },
  {
    path: '/conectores/:id/editar',
    name: 'connector-edit',
    component: () => import('./views/ConnectorFormView.vue'),
    props: true,
    meta: { title: 'Editar conector' },
  },
]

export default routes
