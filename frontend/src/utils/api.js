class Api {
  constructor() {
    this.baseUrl = ''
  }

  async get(endpoint) {
    try {
      const token = localStorage.getItem('token')
      const headers = {
        'Content-Type': 'application/json'
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      console.log('Making GET request to:', endpoint)
      console.log('Request headers:', headers)

      const response = await fetch(endpoint, {
        method: 'GET',
        headers: headers,
        credentials: 'include'
      })

      return response
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  async post(endpoint, data = null) {
    try {
      const token = localStorage.getItem('token')
      const headers = {}
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      // 如果不是 FormData，添加 Content-Type
      if (data && !(data instanceof FormData)) {
        headers['Content-Type'] = 'application/json'
      }

      console.log('Making POST request to:', endpoint)
      console.log('Request headers:', headers)
      
      const requestOptions = {
        method: 'POST',
        headers: headers,
        credentials: 'include'
      };

      // 只有当 data 不为 null 时才添加 body
      if (data) {
        requestOptions.body = data instanceof FormData ? data : JSON.stringify(data);
      }

      const response = await fetch(endpoint, requestOptions);

      // 添加响应调试信息
      console.log('Response status:', response.status);
      if (!response.ok) {
        const errorData = await response.json();
        console.error('Response error:', errorData);
        throw new Error(errorData.detail?.message || '请求失败');
      }

      return response;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  async put(endpoint, data) {
    const token = localStorage.getItem('token')
    const url = `${this.baseUrl}${endpoint}`
    
    try {
      console.log('Making PUT request to:', url)
      const response = await fetch(url, {
        method: 'PUT',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(data)
      })
      
      // 添加响应调试信息
      console.log('Response status:', response.status)
      console.log('Response headers:', Object.fromEntries(response.headers.entries()))
      
      return response
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  async delete(endpoint) {
    const token = localStorage.getItem('token')
    const url = `${this.baseUrl}${endpoint}`
    
    try {
      console.log('Making DELETE request to:', url)
      const response = await fetch(url, {
        method: 'DELETE',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      })
      
      // 添加响应调试信息
      console.log('Response status:', response.status)
      console.log('Response headers:', Object.fromEntries(response.headers.entries()))
      
      return response
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  async uploadDocument(kbId, file) {
    const token = localStorage.getItem('token')
    const formData = new FormData()
    formData.append('file', file)
    
    const url = `${this.baseUrl}/knowledge-base/${kbId}/documents`
    
    console.log('Uploading document to:', url)
    console.log('File to upload:', file)
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: formData,
        credentials: 'include'
      })
      
      console.log('Upload response:', {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries())
      })
      
      if (!response.ok) {
        const error = await response.clone().json()
        console.error('Upload error details:', error)
      }
      
      return response
    } catch (error) {
      console.error('Network error:', error)
      throw error
    }
  }
}

export const api = new Api()

export const registerFromParams = async (name, mobile) => {
  try {
    // 构建查询字符串
    const queryString = new URLSearchParams({
      name,
      mobile
    }).toString();

    const response = await api.post(`/api/auth/register-from-params?${queryString}`);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || '操作失败');
    }

    return await response.json();
  } catch (error) {
    console.error('Registration/Login error:', error);
    throw error;
  }
};