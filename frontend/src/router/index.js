import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', component: () => import('@/views/SearchView.vue') },
  { path: '/journal', component: () => import('@/views/JournalView.vue') },
  { path: '/admin', component: () => import('@/views/AdminView.vue') },
  { path: '/login', component: () => import('@/views/LoginView.vue') },
  { path: '/account', component: () => import('@/views/AccountView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router