<template>
  <div class="app-container mobile-adaptive">
    <nav v-if="isLoggedIn" class="navbar">
      <div class="nav-links">
        <router-link to="/" class="nav-link">
          <i class="fas fa-comments"></i>
          <span>聊天</span>
        </router-link>
        <router-link to="/knowledge-base" class="nav-link">
          <i class="fas fa-book"></i>
          <span>知识库</span>
        </router-link>
        <router-link v-if="authStore.isAdmin" to="/admin/feedback" class="nav-link">
          <i class="fas fa-comment-dots"></i>
          <span>反馈</span>
        </router-link>
      </div>
      <div class="nav-auth">
        <div class="user-info" v-if="authStore.user">
          <img v-if="authStore.user.avatar" :src="authStore.user.avatar" class="avatar">
          <span class="username">{{ authStore.user.username }}</span>
          <span class="role-badge">{{ authStore.user.role }}</span>
        </div>
        <button @click="handleLogout" class="logout-btn">
          <i class="fas fa-sign-out-alt"></i>
          <span>登出</span>
        </button>
      </div>
    </nav>
    <router-view></router-view>
    <Feedback v-if="isLoggedIn" />
  </div>
</template>

<script>
import { authStore } from './store/auth'
import Feedback from './components/Feedback.vue'

export default {
  name: 'App',
  components: {
    Feedback
  },
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
  async beforeRouteEnter(to, from, next) {
    if (authStore.isAuthenticated) {
      await authStore.refreshUserInfo()
    }
    next()
  },
  async mounted() {
    if (this.isLoggedIn) {
      try {
        await this.authStore.refreshUserInfo()
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
  background-color: #ffffff;
  margin: 20px;
  border-radius: 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.nav-links {
  display: flex;
  gap: 1rem;
}

.nav-links a {
  text-decoration: none;
  color: #374151;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  transition: all 0.2s;
  background-color: #f9fafb;
}

.nav-links a:hover {
  background-color: #f3f4f6;
  transform: translateY(-1px);
}

.nav-links a.router-link-active {
  color: #4CAF50;
  background-color: #ecfdf5;
}

.nav-auth {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background-color: #f9fafb;
  border-radius: 20px;
  gap: 0.5rem;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
}

.username {
  color: #374151;
  font-weight: 500;
}

.role-badge {
  background: #e9ecef;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  color: #4b5563;
}

.logout-btn {
  padding: 0.5rem 1.5rem;
  background-color: #ffffff;
  color: #374151;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.logout-btn:hover {
  background-color: #fee2e2;
  color: #dc2626;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* 暗色主题支持 */
@media (prefers-color-scheme: dark) {
  .navbar {
    background-color: #1f2937;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  }

  .nav-links a {
    color: #e5e7eb;
    background-color: #2d3748;
  }

  .nav-links a:hover {
    background-color: #374151;
  }

  .nav-links a.router-link-active {
    color: #4ade80;
    background-color: #064e3b;
  }

  .user-info {
    background-color: #2d3748;
  }

  .username {
    color: #e5e7eb;
  }

  .role-badge {
    background: #374151;
    color: #9ca3af;
  }

  .logout-btn {
    background-color: #1f2937;
    color: #e5e7eb;
    border-color: #374151;
  }

  .logout-btn:hover {
    background-color: #7f1d1d;
    color: #fecaca;
  }
}

/* 优化移动端适配 */
@media (max-width: 768px) {
  .navbar {
    margin: 8px;
    padding: 0.4rem 0.75rem;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
  }

  .nav-links {
    gap: 0.35rem;
  }

  .nav-link {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 0.35rem 0.6rem;
    font-size: 0.8rem;
  }

  .nav-link i {
    font-size: 0.9rem;
  }

  .nav-auth {
    gap: 0.35rem;
  }

  .user-info {
    padding: 0.35rem 0.5rem;
    font-size: 0.8rem;
    gap: 0.35rem;
  }

  .avatar {
    width: 24px;
    height: 24px;
  }

  .username {
    max-width: 70px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .role-badge {
    padding: 0.15rem 0.35rem;
    font-size: 0.7rem;
  }

  .logout-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 0.35rem 0.6rem;
    font-size: 0.8rem;
  }

  .logout-btn i {
    font-size: 0.9rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 380px) {
  .navbar {
    margin: 5px;
    padding: 0.35rem 0.5rem;
  }

  .nav-link span {
    display: none; /* 只显示图标 */
  }

  .nav-link {
    padding: 0.35rem;
  }

  .nav-link i {
    font-size: 1rem;
  }

  .role-badge {
    display: none;
  }

  .username {
    max-width: 50px;
  }

  .logout-btn span {
    display: none;
  }

  .logout-btn {
    padding: 0.35rem;
  }

  .logout-btn i {
    font-size: 1rem;
  }
}

/* 暗色模式适配 */
@media (prefers-color-scheme: dark) {
  @media (max-width: 768px) {
    .navbar {
      background: rgba(31, 41, 55, 0.95);
    }
  }
}
</style> 