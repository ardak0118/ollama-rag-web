<template>
  <div class="login-container">
    <div class="login-box">
      <h2>登录</h2>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名:</label>
          <input 
            type="text" 
            v-model="username" 
            required
            :disabled="isLoading"
            placeholder="请输入用户名"
          >
        </div>
        <div class="form-group">
          <label>密码:</label>
          <input 
            type="password" 
            v-model="password" 
            required
            :disabled="isLoading"
            placeholder="请输入密码"
          >
        </div>
        <button 
          type="submit" 
          class="login-btn"
          :disabled="isLoading"
        >
          {{ isLoading ? '登录中...' : '登录' }}
        </button>
        <div class="register-link">
          没有账号？<router-link to="/register">去注册</router-link>
        </div>
      </form>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { api } from '../utils/api'
import { authStore } from '../store/auth'
import { useRouter } from 'vue-router'

export default {
  name: 'Login',
  setup() {
    const username = ref('')
    const password = ref('')
    const error = ref('')
    const isLoading = ref(false)
    const router = useRouter()

    const handleLogin = async () => {
      if (!username.value || !password.value) {
        error.value = '请输入用户名和密码'
        return
      }

      isLoading.value = true
      error.value = ''

      try {
        const response = await api.post('/api/auth/login', {
          username: username.value,
          password: password.value
        })

        const data = await response.json()
        
        if (response.ok) {
          // 保存 token 和用户信息
          authStore.setAuth(data.access_token, data.user)
          router.push('/')
        } else {
          error.value = data.detail?.message || '登录失败，请检查用户名和密码'
        }
      } catch (err) {
        console.error('Login request failed:', err)
        error.value = err.message || '登录失败，请稍后重试'
      } finally {
        isLoading.value = false
      }
    }

    return {
      username,
      password,
      error,
      isLoading,
      handleLogin
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f5f5;
}

.login-box {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
}

.form-group input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.login-btn {
  width: 100%;
  padding: 0.75rem;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.login-btn:hover {
  background-color: #45a049;
}

.error {
  color: red;
  margin-top: 1rem;
  text-align: center;
}

.register-link {
  text-align: center;
  margin-top: 1rem;
}

.register-link a {
  color: #4CAF50;
  text-decoration: none;
}

.register-link a:hover {
  text-decoration: underline;
}
</style> 