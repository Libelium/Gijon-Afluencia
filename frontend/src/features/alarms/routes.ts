import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/alarmas',
    name: 'alarms-list',
    component: () => import('./views/AlarmsListView.vue'),
    meta: { title: 'Alarmas' },
  },
  {
    path: '/alarmas/nueva',
    name: 'alarm-create',
    component: () => import('./views/AlarmFormView.vue'),
    meta: { title: 'Nueva alarma' },
  },
  {
    path: '/alarmas/:id',
    name: 'alarm-detail',
    component: () => import('./views/AlarmDetailView.vue'),
    props: true,
    meta: { title: 'Alarma' },
  },
]

export default routes
