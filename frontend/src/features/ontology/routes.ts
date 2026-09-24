import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/ontologia',
    name: 'ontology',
    component: () => import('./views/OntologyView.vue'),
    meta: { title: 'Ontología' },
  },
]

export default routes
