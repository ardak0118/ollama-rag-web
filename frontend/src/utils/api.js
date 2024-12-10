import { authStore } from '../store/auth'

// 创建基础 API URL 配置
const BASE_URL = 'http://localhost:8000'

export const api = {
  async request(endpoint, options = {}) {
    const token = localStorage.getItem('token')
    
    // 如果是 FormData，不要设置 Content-Type，让浏览器自动设置
    const headers = options.body instanceof FormData 
      ? { 
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          ...options.headers 
        }
      : {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          ...options.headers
        }

    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers
    })

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
      const errorText = await response.text()
      throw new Error(`Request failed: ${errorText}`)
    }

    return response
  },

  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' })
  },

  async post(endpoint, data, options = {}) {
    // 如果是 FormData，直接使用，否则转换为 JSON
    const body = data instanceof FormData ? data : JSON.stringify(data)
    
    return this.request(endpoint, {
      method: 'POST',
      body,
      ...options
    })
  },

  async put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    })
  },

  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' })
  }
} 