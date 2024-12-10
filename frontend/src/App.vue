<template>
  <div id="app">
    <nav v-if="isLoggedIn" class="navbar">
      <div class="nav-links">
        <router-link to="/">聊天</router-link>
        <router-link to="/knowledge-base">知识库管理</router-link>
      </div>
      <div class="nav-auth">
        <div class="user-info" v-if="authStore.user">
          <img v-if="authStore.user.avatar" :src="authStore.user.avatar" class="avatar">
          <span class="username">{{ authStore.user.username }}</span>
          <span class="role-badge">{{ authStore.user.role }}</span>
        </div>
        <button @click="handleLogout" class="logout-btn">登出</button>
      </div>
    </nav>
    <router-view></router-view>
  </div>
</template>

<script>
import { authStore } from './store/auth'

export default {
  name: 'App',
  data() {
    return {
      authStore
    }
  },
  computed: {
    isLoggedIn() {
      return !!this.authStore.token
    }
  },
  methods: {
    handleLogout() {
      this.authStore.clearAuth()
      this.$router.push('/login')
    }
  },
  async mounted() {
    if (this.isLoggedIn) {
      try {
        await this.authStore.fetchCurrentUser()
      } catch (err) {
        console.error('Failed to fetch user data:', err)
        this.$router.push('/login')
      }
    }
  }
}
</script>

<style>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #ddd;
}

.nav-links a {
  margin-right: 1rem;
  text-decoration: none;
  color: #333;
}

.nav-links a.router-link-active {
  color: #4CAF50;
}

.nav-auth {
  display: flex;
  align-items: center;
}

.username {
  margin-right: 1rem;
}

.logout-btn {
  padding: 0.5rem 1rem;
  background-color: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.logout-btn:hover {
  background-color: #c82333;
}

.user-info {
  display: flex;
  align-items: center;
  margin-right: 1rem;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  margin-right: 0.5rem;
}

.role-badge {
  background: #e9ecef;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  margin-left: 0.5rem;
}
</style> 