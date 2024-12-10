<template>
  <div class="register-container">
    <div class="register-box">
      <h2>注册</h2>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label>用户名:</label>
          <input 
            type="text" 
            v-model="username" 
            required
            :disabled="isLoading"
            placeholder="请输入用户名(3-20个字符)"
          >
        </div>
        <div class="form-group">
          <label>邮箱:</label>
          <input 
            type="email" 
            v-model="email" 
            required
            :disabled="isLoading"
            placeholder="请输入邮箱"
          >
        </div>
        <div class="form-group">
          <label>密码:</label>
          <input 
            type="password" 
            v-model="password" 
            required
            :disabled="isLoading"
            placeholder="请输入密码(至少6个字符)"
          >
        </div>
        <button 
          type="submit" 
          class="register-btn"
          :disabled="isLoading"
        >
          {{ isLoading ? '注册中...' : '注册' }}
        </button>
        <div class="login-link">
          已有账号？<router-link to="/login">去登录</router-link>
        </div>
      </form>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script>
import { authStore } from '../store/auth'

export default {
  name: 'Register',
  data() {
    return {
      username: '',
      email: '',
      password: '',
      error: null,
      isLoading: false
    }
  },
  methods: {
    async handleRegister() {
      this.error = null
      this.isLoading = true
      
      try {
        // 前端验证
        if (this.username.length < 3) {
          this.error = '用户名至少需要3个字符'
          return
        }
        if (this.password.length < 6) {
          this.error = '密码至少需要6个字符'
          return
        }
        
        const response = await fetch('/api/auth/register', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            username: this.username,
            email: this.email,
            password: this.password
          })
        });

        const data = await response.json();
        
        if (response.ok) {
          // 注册成功后直接登录
          authStore.setToken(data.access_token)
          await authStore.fetchCurrentUser()
          this.$router.push('/')
        } else {
          this.error = data.detail || '注册失败'
          console.error('Registration error:', data)
        }
      } catch (err) {
        console.error('Registration error:', err)
        this.error = '注册请求失败，请稍后重试'
      } finally {
        this.isLoading = false
      }
    }
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f5f5;
}

.register-box {
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

.register-btn {
  width: 100%;
  padding: 0.75rem;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 1rem;
}

.register-btn:hover {
  background-color: #45a049;
}

.error {
  color: red;
  margin-top: 1rem;
  text-align: center;
}

.login-link {
  text-align: center;
}

.login-link a {
  color: #4CAF50;
  text-decoration: none;
}

.login-link a:hover {
  text-decoration: underline;
}
</style> 