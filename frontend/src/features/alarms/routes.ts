import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/alarmas',
    name: 'alarms-list',
    component: () => import('./views/AlarmsListView.vue'),
    meta: { title: 'Alarmas' },
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
