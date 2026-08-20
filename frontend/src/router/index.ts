import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
    },
    {
      path: '/items/:id',
      name: 'detail',
      component: () => import('@/views/DetailView.vue'),
      props: route => ({ id: Number(route.params.id) }),
    },
  ],
})

export default router
