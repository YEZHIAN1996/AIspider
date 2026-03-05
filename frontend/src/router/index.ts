import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
      { path: 'tasks', name: 'Tasks', component: () => import('@/views/Tasks.vue') },
      { path: 'seeds', name: 'Seeds', component: () => import('@/views/Seeds.vue') },
      { path: 'proxies', name: 'Proxies', component: () => import('@/views/Proxies.vue') },
      { path: 'data', name: 'DataQuery', component: () => import('@/views/DataQuery.vue') },
      { path: 'logs', name: 'Logs', component: () => import('@/views/Logs.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth !== false && !auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
})

export default router
