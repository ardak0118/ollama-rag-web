<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h2>管理控制台</h2>
      </div>
      <nav class="sidebar-nav">
        <router-link 
          to="/admin/users" 
          class="nav-item"
          v-permission="Permissions.USER_MANAGE"
        >
          用户管理
        </router-link>
        <router-link 
          to="/admin/system" 
          class="nav-item"
          v-permission="Permissions.SYSTEM_MANAGE"
        >
          系统设置
        </router-link>
        <router-link 
          to="/admin/test" 
          class="nav-item"
        >
          权限测试
        </router-link>
      </nav>
    </div>
    
    <!-- 主内容区 -->
    <div class="main-content">
      <div class="header">
        <div class="breadcrumb">
          管理控制台 / {{ currentRoute }}
        </div>
        <div class="user-info">
          <span>{{ authStore.user?.username }}</span>
          <button @click="logout" class="logout-btn">退出</button>
        </div>
      </div>
      <div class="content">
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authStore } from '../store/auth'
import { Permissions } from '../utils/permissions'

export default {
  name: 'AdminLayout',
  
  setup() {
    const router = useRouter()
    const route = useRoute()
    
    const currentRoute = computed(() => {
      switch(route.path) {
        case '/admin/users':
          return '用户管理'
        case '/admin/system':
          return '系统设置'
        case '/admin/test':
          return '权限测试'
        default:
          return '控制台'
      }
    })
    
    const logout = () => {
      authStore.clearAuth()
      router.push('/login')
    }
    
    return {
      currentRoute,
      authStore,
      Permissions,
      logout
    }
  }
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 250px;
  background-color: #1e293b;
  color: white;
  padding: 1rem;
}

.sidebar-header {
  padding: 1rem;
  border-bottom: 1px solid #334155;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: #f8fafc;
}

.sidebar-nav {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.nav-item {
  display: block;
  padding: 0.75rem 1rem;
  color: #cbd5e1;
  text-decoration: none;
  border-radius: 0.375rem;
  transition: all 0.2s;
}

.nav-item:hover {
  background-color: #334155;
  color: white;
}

.nav-item.router-link-active {
  background-color: #2563eb;
  color: white;
}

.main-content {
  flex: 1;
  background-color: #f1f5f9;
  display: flex;
  flex-direction: column;
}

.header {
  background-color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
}

.breadcrumb {
  color: #64748b;
  font-size: 0.875rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logout-btn {
  padding: 0.5rem 1rem;
  background-color: #ef4444;
  color: white;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.logout-btn:hover {
  background-color: #dc2626;
}

.content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}
</style> 