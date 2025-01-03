import { reactive } from 'vue'
import { api } from '../utils/api'

export const authStore = reactive({
  user: null,
  token: null,
  isAuthenticated: false,
  isAdmin: false,
  canManageKB: false,

  // 添加 setAuth 方法
  setAuth(token, userData) {
    this.setToken(token)
    this.setUser(userData)
  },

  setUser(userData) {
    this.user = userData
    this.isAuthenticated = !!userData
    this.isAdmin = userData?.is_admin || false
    this.canManageKB = userData?.can_manage_kb || false
  },

  setToken(token) {
    this.token = token
    if (token) {
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('token')
    }
  },

  clearUser() {
    this.user = null
    this.token = null
    this.isAuthenticated = false
    this.isAdmin = false
    this.canManageKB = false
    localStorage.removeItem('token')
  },

  // 添加 clearAuth 作为 clearUser 的别名
  clearAuth() {
    this.clearUser()
  },

  // 初始化方法，从 localStorage 恢复 token
  init() {
    const token = localStorage.getItem('token')
    if (token) {
      this.token = token
      // 可以在这里添加自动获取用户信息的逻辑
      this.fetchUserInfo()
    }
  },

  // 获取用户信息
  async fetchUserInfo() {
    try {
      const response = await api.get('/api/auth/users/me')
      if (response.ok) {
        const userData = await response.json()
        this.setUser(userData)
      } else {
        // 添加更详细的错误处理
        let errorMessage = '获取用户信息失败'
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorMessage
        } catch (e) {
          console.error('Error parsing error response:', e)
        }
        console.error('Failed to fetch user info:', errorMessage)
        this.clearUser()
        throw new Error(errorMessage)
      }
    } catch (error) {
      console.error('Failed to fetch user info:', error)
      this.clearUser()
      throw error
    }
  },

  // 添加刷新用户信息的方法
  async refreshUserInfo() {
    try {
      const response = await api.get('/api/auth/users/me')
      if (response.ok) {
        const userData = await response.json()
        this.setUser(userData)
      }
    } catch (error) {
      console.error('Failed to refresh user info:', error)
    }
  }
})

// 在应用启动时初始化
authStore.init()