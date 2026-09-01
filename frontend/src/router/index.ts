import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import AppShell from '@/layouts/AppShell.vue'
import BlankLayout from '@/layouts/BlankLayout.vue'
import { isAuthenticated, login } from '@/auth/keycloak'
import { pageTitle } from '@/brand'

import entityRoutes from '@/features/entities/routes'
import mapRoutes from '@/features/map/routes'
import dashboardRoutes from '@/features/dashboards/routes'
import alarmRoutes from '@/features/alarms/routes'
import preferenceRoutes from '@/features/preferences/routes'
import customizationRoutes from '@/features/customization/routes'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    component: BlankLayout,
    children: [
      {
        path: '',
        name: 'login',
        component: () => import('@/views/LoginView.vue'),
        meta: { public: true, title: 'Iniciar sesión' },
      },
    ],
  },
  {
    path: '/',
    component: AppShell,
    children: [
      { path: '', redirect: '/entidades' },
      ...entityRoutes,
      ...mapRoutes,
      ...dashboardRoutes,
      ...alarmRoutes,
      ...preferenceRoutes,
      ...customizationRoutes,
      {
        path: '/sin-acceso',
        name: 'forbidden',
        component: () => import('@/views/ForbiddenView.vue'),
        meta: { title: 'Sin acceso' },
      },
      {
        path: '/:pathMatch(.*)*',
        name: 'not-found',
        component: () => import('@/views/NotFoundView.vue'),
        meta: { title: 'Página no encontrada' },
      },
    ],
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, saved) => saved ?? { top: 0 },
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  if (!isAuthenticated()) {
    void login(to.fullPath)
    return false
  }
  return true
})

router.afterEach((to) => {
  document.title = pageTitle(to.meta.title as string | undefined)
})

export default router
