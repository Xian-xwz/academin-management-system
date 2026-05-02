import { createRouter, createWebHistory } from 'vue-router';
import { getToken, getUserInfo } from '@/utils/auth';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: () => import('@/views/Login/index.vue')
    },
    {
      path: '/register',
      component: () => import('@/views/Register/index.vue')
    },
    {
      path: '/',
      component: () => import('@/components/Layout/index.vue'),
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', component: () => import('@/views/Dashboard/index.vue') },
        { path: 'student-query', component: () => import('@/views/StudentQuery/index.vue') },
        { path: 'ai-chat', component: () => import('@/views/AIChat/index.vue') },
        { path: 'forum', component: () => import('@/views/Forum/TopicList/index.vue') },
        { path: 'forum/topics/create', component: () => import('@/views/Forum/CreateTopic/index.vue') },
        { path: 'forum/topics/:id/edit', component: () => import('@/views/Forum/CreateTopic/index.vue') },
        { path: 'forum/topics/:id', component: () => import('@/views/Forum/TopicDetail/index.vue') },
        { path: 'knowledge-cards', component: () => import('@/views/KnowledgeCards/index.vue') },
        { path: 'schedule', component: () => import('@/views/Schedule/index.vue') },
        { path: 'time-plan', component: () => import('@/views/TimePlan/index.vue') },
        { path: 'profile', component: () => import('@/views/Profile/index.vue') },
      ]
    },
    {
      path: '/admin',
      component: () => import('@/components/AdminLayout/index.vue'),
      redirect: '/admin/dashboard',
      meta: { requiresAdmin: true },
      children: [
        { path: 'dashboard', component: () => import('@/views/Admin/Dashboard/index.vue'), meta: { requiresAdmin: true } },
        { path: 'users', component: () => import('@/views/Admin/Users/index.vue'), meta: { requiresAdmin: true } },
        { path: 'users/:studentId/progress', component: () => import('@/views/Admin/UserProgress/index.vue'), meta: { requiresAdmin: true } },
        { path: 'forum', component: () => import('@/views/Admin/Forum/index.vue'), meta: { requiresAdmin: true } },
      ]
    }
  ]
});

router.beforeEach((to, from, next) => {
  const hasToken = getToken();
  const userInfo = getUserInfo();
  if (to.path === '/login' || to.path === '/register') {
    if (hasToken) {
      next({ path: userInfo?.role === 'admin' ? '/admin' : '/' });
    } else {
      next();
    }
  } else {
    if (hasToken) {
      if (to.matched.some(record => record.meta.requiresAdmin) && userInfo?.role !== 'admin') {
        next({ path: '/dashboard' });
      } else {
        next();
      }
    } else {
      next(`/login?redirect=${to.path}`);
    }
  }
});

export default router;
