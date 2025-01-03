<template>
  <div class="url-register">
    <div class="register-card">
      <div class="logo">
        <img src="../assets/logo.png" alt="Logo">
        <h1>小巴Chat</h1>
      </div>
      
      <div v-if="loading" class="status-message loading">
        <div class="spinner"></div>
        <span>正在处理...</span>
      </div>
      
      <div v-else-if="error" class="status-message error">
        <i class="fas fa-exclamation-circle"></i>
        <span>{{ error }}</span>
        <div class="action-buttons">
          <button class="btn primary" @click="goToLogin">
            <i class="fas fa-sign-in-alt"></i> 去登录
          </button>
          <button class="btn secondary" @click="tryAgain">
            <i class="fas fa-redo"></i> 重试
          </button>
        </div>
      </div>
      
      <div v-else-if="success" class="status-message success">
        <i class="fas fa-check-circle"></i>
        <span>{{ successMessage }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { registerFromParams } from '../utils/api'
import { authStore } from '../store/auth'

export default {
  name: 'UrlRegister',
  setup() {
    const router = useRouter()
    const loading = ref(true)
    const error = ref(null)
    const success = ref(false)
    const successMessage = ref('')
    const currentParams = ref(null)

    const processUrlParams = async () => {
      try {
        const urlParams = new URLSearchParams(window.location.search)
        const name = urlParams.get('name')
        const mobile = urlParams.get('mobile')

        if (!name || !mobile) {
          throw new Error('缺少必要的参数')
        }

        currentParams.value = { name, mobile }

        // 注册或登录
        const result = await registerFromParams(name, mobile)
        
        // 保存认证信息
        authStore.setAuth(result.access_token, result.user)
        
        success.value = true
        successMessage.value = result.message === 'Login successful' 
          ? '登录成功！正在跳转...'
          : '注册成功！正在跳转...'
        
        // 延迟跳转
        setTimeout(() => {
          router.push('/')
        }, 1500)
      } catch (e) {
        error.value = e.message
      } finally {
        loading.value = false
      }
    }

    const tryAgain = () => {
      if (currentParams.value) {
        loading.value = true
        error.value = null
        processUrlParams()
      }
    }

    const goToLogin = () => {
      router.push('/login')
    }

    onMounted(() => {
      processUrlParams()
    })

    return {
      loading,
      error,
      success,
      successMessage,
      tryAgain,
      goToLogin
    }
  }
}
</script>

<style scoped>
.url-register {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.register-card {
  background: white;
  padding: 2rem;
  border-radius: 16px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.05);
  width: 90%;
  max-width: 400px;
  text-align: center;
}

.logo {
  margin-bottom: 2rem;
}

.logo img {
  width: 80px;
  height: 80px;
  margin-bottom: 1rem;
}

.logo h1 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin: 0;
}

.status-message {
  padding: 1.5rem;
  border-radius: 12px;
  margin: 1rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.loading {
  background: #f8f9fa;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.error {
  background: #fff5f5;
  color: #e53e3e;
}

.success {
  background: #f0fff4;
  color: #38a169;
}

.status-message i {
  font-size: 2rem;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s;
}

.btn.primary {
  background: #3498db;
  color: white;
}

.btn.secondary {
  background: #e2e8f0;
  color: #4a5568;
}

.btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .register-card {
    padding: 1.5rem;
  }
  
  .logo img {
    width: 60px;
    height: 60px;
  }
  
  .btn {
    padding: 0.5rem 1rem;
  }
}
</style>