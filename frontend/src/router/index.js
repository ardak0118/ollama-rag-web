import { createRouter, createWebHistory } from 'vue-router'
import ChatWindow from '../components/ChatWindow.vue'
import KnowledgeBasePage from '../components/KnowledgeBasePage.vue'
import Login from '../components/Login.vue'
import Register from '../components/Register.vue'
import UserManagement from '../components/admin/UserManagement.vue'
import SystemSettings from '../components/admin/SystemSettings.vue'
import AdminLayout from '../layouts/AdminLayout.vue'
import { authStore } from '../store/auth'
import { hasPermission, Permissions } from '../utils/permissions'

const routes = [
  {
    path: '/',
    name: 'Chat',
    component: ChatWindow,
    meta: { requiresAuth: true }
  },
  {
    path: '/knowledge-base',
    name: 'KnowledgeBase',
    component: KnowledgeBasePage,
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/register',
    name: 'Register',
    component: Register
  },
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAdmin: true },
    children: [
      {
        path: 'users',
        component: UserManagement,
        meta: { permission: Permissions.USER_MANAGE }
      },
      {
        path: 'system',
        component: SystemSettings,
        meta: { permission: Permissions.SYSTEM_MANAGE }
      }
    ]
  },
  {
    path: '/admin/test',
    name: 'AdminTest',
    component: () => import('../components/admin/AdminTest.vue'),
    meta: { 
      requiresAuth: true,
      requiresAdmin: true
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 检查是否需要登录
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!authStore.token) {
      next('/login')
      return
    }
  }
  
  // 检查是否需要管理员权限
  if (to.matched.some(record => record.meta.requiresAdmin)) {
    if (!authStore.isAdmin) {
      next('/')
      return
    }
  }
  
  // 检查具体权限
  if (to.meta.permission && !hasPermission(to.meta.permission)) {
    next('/')
    return
  }
  
  next()
})

export default router 