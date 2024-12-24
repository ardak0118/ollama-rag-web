import { reactive } from 'vue'
import { api } from '../utils/api'

export const authStore = reactive({
  user: null,
  token: null,
  isAdmin: false,
  
  async fetchCurrentUser() {
    try {
      const response = await api.get('/api/auth/me')
      if (response.ok) {
        const userData = await response.json()
        this.user = userData
        this.isAdmin = userData.is_admin || false
        return userData
      }
      return null
    } catch (error) {
      console.error('Failed to fetch user:', error)
      return null
    }
  },

  setToken(token) {
    this.token = token
    localStorage.setItem('token', token)
  },

  clearAuth() {
    this.user = null
    this.token = null
    this.isAdmin = false
    localStorage.removeItem('token')
  },

  init() {
    const token = localStorage.getItem('token')
    if (token) {
      this.token = token
      this.fetchCurrentUser()
    }
  }
})

authStore.init()