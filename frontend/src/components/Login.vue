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
import { authStore } from '../store/auth'

export default {
  name: 'Login',
  data() {
    return {
      username: '',
      password: '',
      error: null,
      isLoading: false
    }
  },
  methods: {
    async handleLogin() {
      this.error = null;
      this.isLoading = true;
      
      try {
        const formData = new URLSearchParams();
        formData.append('username', this.username);
        formData.append('password', this.password);
        formData.append('grant_type', 'password');

        console.log('Sending login request:', {
          username: this.username,
          grant_type: 'password'
        });

        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: formData
        });

        const data = await response.json();
        console.log('Login response status:', response.status);
        
        if (response.ok) {
          console.log('Login successful, token:', data.access_token);
          authStore.setToken(data.access_token);
          try {
            await authStore.fetchCurrentUser();
            const redirect = this.$route.query.redirect || '/';
            this.$router.push(redirect);
          } catch (err) {
            console.error('Failed to fetch user data:', err);
            this.error = '获取用户信息失败';
          }
        } else {
          console.error('Login failed:', data);
          this.error = data.detail || '登录失败';
        }
      } catch (err) {
        console.error('Login request failed:', err);
        this.error = '登录请求失败，请稍后重试';
      } finally {
        this.isLoading = false;
      }
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