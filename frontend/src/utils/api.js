import { authStore } from '../store/auth'

// 根据环境设置基础 URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

class Api {
  constructor() {
    this.baseUrl = API_BASE_URL
  }

  async get(endpoint, options = {}) {
    const token = localStorage.getItem('token')
    const url = endpoint.startsWith('/api') ? endpoint : `${this.baseUrl}${endpoint}`
    
    const config = {
      method: 'GET',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
      credentials: 'include',
      ...options
    }
    
    // 如果不是请求 blob，添加 Content-Type
    if (!options.responseType || options.responseType !== 'blob') {
      config.headers['Content-Type'] = 'application/json'
    }
    
    const response = await fetch(url, config)
    return response
  }

  async post(endpoint, data) {
    const token = localStorage.getItem('token')
    const url = endpoint.startsWith('/api') ? endpoint : `${this.baseUrl}${endpoint}`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify(data)
    })
    return response
  }

  async put(endpoint, data) {
    const token = localStorage.getItem('token')
    const url = endpoint.startsWith('/api') ? endpoint : `${this.baseUrl}${endpoint}`
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify(data)
    })
    return response
  }

  async delete(endpoint) {
    const token = localStorage.getItem('token')
    const url = endpoint.startsWith('/api') ? endpoint : `${this.baseUrl}${endpoint}`
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      },
      credentials: 'include'
    })
    return response
  }

  async uploadDocument(kbId, file) {
    const token = localStorage.getItem('token')
    const formData = new FormData()
    formData.append('file', file)
    
    const url = `${this.baseUrl}/knowledge-bases/${kbId}/documents`
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
      body: formData,
      credentials: 'include'
    })
    return response
  }
}

export const api = new Api()