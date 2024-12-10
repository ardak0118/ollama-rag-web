import { reactive } from '@vue/runtime-core'
import { api } from '../utils/api'

const user = reactive({
  data: null
})

const token = reactive({
  value: localStorage.getItem('token')
})

export const authStore = reactive({
  get user() {
    return user.data
  },
  
  get token() {
    return token.value
  },
  
  setUser(userData) {
    user.data = userData
  },
  
  setToken(tokenValue) {
    token.value = tokenValue
    localStorage.setItem('token', tokenValue)
  },
  
  clearAuth() {
    user.data = null
    token.value = null
    localStorage.removeItem('token')
  },
  
  async fetchCurrentUser() {
    try {
      if (!token.value) {
        this.clearAuth()
        return
      }

      const response = await api.get('/api/auth/me')
      if (response.ok) {
        const userData = await response.json()
        this.setUser(userData)
      } else {
        this.clearAuth()
        throw new Error(response.statusText)
      }
    } catch (err) {
      console.error('Failed to fetch user:', err)
      this.clearAuth()
      throw err
    }
  }
}) 