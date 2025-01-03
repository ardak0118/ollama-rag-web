<template>
  <div class="user-management mobile-adaptive">
    <div class="admin-container">
      <div class="header">
        <h1>用户管理</h1>
        <div class="action-buttons">
          <button class="action-btn create" @click="showCreateModal = true">
            <span class="icon">+</span>
            创建用户
          </button>
          <button class="action-btn import" @click="showImportModal = true">
            <span class="icon">📥</span>
            批量导入
          </button>
        </div>
      </div>

      <!-- 用户列表 -->
      <div class="users-table">
        <table>
          <thead>
            <tr>
              <th>用户名</th>
              <th>邮箱</th>
              <th class="status-column">状态</th>
              <th class="status-column">管理员</th>
              <th class="status-column">知识库权限</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.username }}</td>
              <td>{{ user.email }}</td>
              <td class="status-column">
                <div class="status-toggle">
                  <input 
                    type="checkbox" 
                    :id="`active-${user.id}`"
                    :checked="user.is_active"
                    @change="updateUserStatus(user)"
                    :disabled="user.id === currentUser?.id"
                    class="toggle-input"
                  >
                  <label :for="`active-${user.id}`" class="toggle-label">
                    <span class="toggle-button"></span>
                    <span class="status-text" :class="user.is_active ? 'active' : 'inactive'">
                      {{ user.is_active ? '活跃' : '禁用' }}
                    </span>
                  </label>
                </div>
              </td>
              <td class="status-column">
                <div class="status-toggle">
                  <input 
                    type="checkbox" 
                    :id="`admin-${user.id}`"
                    :checked="user.is_admin"
                    @change="updateUserRole(user)"
                    :disabled="user.id === currentUser?.id"
                    class="toggle-input"
                  >
                  <label :for="`admin-${user.id}`" class="toggle-label">
                    <span class="toggle-button"></span>
                    <span class="status-text" :class="user.is_admin ? 'admin' : ''">
                      {{ user.is_admin ? '是' : '否' }}
                    </span>
                  </label>
                </div>
              </td>
              <td class="status-column">
                <div class="status-toggle">
                  <input 
                    type="checkbox" 
                    :id="`kb-${user.id}`"
                    :checked="user.can_manage_kb"
                    @change="updateKbPermission(user)"
                    :disabled="user.is_admin || user.id === currentUser?.id"
                    class="toggle-input"
                  >
                  <label :for="`kb-${user.id}`" class="toggle-label">
                    <span class="toggle-button"></span>
                    <span class="status-text" :class="user.can_manage_kb ? 'kb-enabled' : ''">
                      {{ user.can_manage_kb ? '允许' : '禁止' }}
                    </span>
                  </label>
                </div>
              </td>
              <td>
                <button 
                  @click="deleteUser(user)"
                  :disabled="user.id === currentUser?.id"
                  class="delete-btn"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 创建用户弹窗 -->
      <Modal v-if="showCreateModal" @close="showCreateModal = false">
        <template #title>创建用户</template>
        <template #content>
          <form @submit.prevent="createUser">
            <div class="form-group">
              <label>用户名</label>
              <input v-model="newUser.username" required />
            </div>
            <div class="form-group">
              <label>邮箱</label>
              <input type="email" v-model="newUser.email" required />
            </div>
            <div class="form-group">
              <label>密码</label>
              <input type="password" v-model="newUser.password" required />
            </div>
            <div class="form-group">
              <label>角色</label>
              <select v-model="newUser.is_admin">
                <option :value="false">普通用户</option>
                <option :value="true">管理员</option>
              </select>
            </div>
            <div class="error" v-if="error">{{ error }}</div>
            <div class="form-actions">
              <button type="submit" class="btn primary" :disabled="isLoading">
                {{ isLoading ? '创建中...' : '创建' }}
              </button>
              <button type="button" class="btn" @click="showCreateModal = false">
                取消
              </button>
            </div>
          </form>
        </template>
      </Modal>

      <!-- 批量导入弹窗 -->
      <Modal v-if="showImportModal" @close="showImportModal = false">
        <template #title>批量导入用户</template>
        <template #content>
          <div class="import-container">
            <div class="import-tips">
              <p>请注意：</p>
              <ul>
                <li>请使用 UTF-8 编码的 CSV 文件</li>
                <li>文件必须包含以下列：username, email, password, role(可选)</li>
                <li>可以先下载模板，按照模板格式填写</li>
              </ul>
            </div>
            <input 
              type="file" 
              ref="fileInput"
              accept=".csv"
              @change="handleFileUpload"
            />
            <div class="template-download">
              <button 
                class="btn secondary" 
                @click="downloadTemplate"
                :disabled="isDownloading"
              >
                {{ isDownloading ? '下载中...' : '下载模板' }}
              </button>
            </div>
            <button 
              class="btn primary" 
              @click="importUsers"
              :disabled="!selectedFile"
            >
              开始导入
            </button>
          </div>
        </template>
      </Modal>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { api } from '../../utils/api'
import Modal from '../common/Modal.vue'
import { authStore } from '../../store/auth'

export default {
  name: 'UserManagement',
  components: { Modal },
  
  setup() {
    const users = ref([])
    const showCreateModal = ref(false)
    const showImportModal = ref(false)
    const selectedFile = ref(null)
    const error = ref(null)
    const isLoading = ref(false)
    const isDownloading = ref(false)
    
    const newUser = ref({
      username: '',
      email: '',
      password: '',
      is_admin: false
    })

    const currentUser = ref(authStore.user)

    // 获取用户列表
    const fetchUsers = async () => {
      try {
        const response = await api.get('/api/admin/users')
        console.log('Fetching users from:', response.url)
        
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('用户管理API未找到，请确保后端服务正常运行')
          }
          const errorData = await response.json()
          throw new Error(errorData.detail || 'Failed to fetch users')
        }
        
        const data = await response.json()
        console.log('Fetched users:', data)
        users.value = data
      } catch (error) {
        console.error('Failed to fetch users:', error)
        alert(error.message)
      }
    }

    // 创建用户
    const createUser = async () => {
      try {
        isLoading.value = true
        error.value = null

        const response = await api.post('/api/admin/users', {
          username: newUser.value.username,
          email: newUser.value.email,
          password: newUser.value.password,
          is_admin: newUser.value.is_admin
        })

        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.detail || '创建用户失败')
        }

        const data = await response.json()
        users.value.push(data)
        showCreateModal.value = false
        newUser.value = {
          username: '',
          email: '',
          password: '',
          is_admin: false
        }
      } catch (err) {
        error.value = err.message
        console.error('Error creating user:', err)
      } finally {
        isLoading.value = false
      }
    }

    // 更新用户角色
    const updateUserRole = async (user) => {
      try {
        console.log('Updating user role:', {
          userId: user.id,
          isAdmin: user.is_admin
        })

        const response = await api.put(`/api/admin/users/${user.id}`, {
          is_admin: user.is_admin
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || 'Failed to update user role')
        }

        // 更新本地状态
        const updatedUser = await response.json()
        Object.assign(user, updatedUser)

        // 如果更新成功，刷新用户列表
        await fetchUsers()
      } catch (error) {
        console.error('Failed to update user role:', error)
        // 恢复原始状态
        user.is_admin = !user.is_admin
        alert(error.message || '更新用户角色失败')
      }
    }

    // 删除用户
    const deleteUser = async (user) => {
      if (!confirm(`确定要删除用户 ${user.username} 吗？`)) return
      
      try {
        const response = await api.delete(`/api/admin/users/${user.id}`)
        if (!response.ok) {
          throw new Error('Failed to delete user')
        }
        await fetchUsers()
      } catch (error) {
        console.error('Failed to delete user:', error)
      }
    }

    // 处理文件上传
    const handleFileUpload = (event) => {
      const file = event.target.files[0]
      if (file) {
        // 检查文件大小
        if (file.size > 1024 * 1024) { // 1MB
          alert('文件大小不能超过1MB')
          event.target.value = ''
          return
        }
        
        // 检查文件类型
        if (!file.name.endsWith('.csv')) {
          alert('只支持 CSV 文件')
          event.target.value = ''
          return
        }
        
        // 使用 FileReader API 安全地读取文件
        const reader = new FileReader()
        reader.onload = (e) => {
          try {
            const content = e.target.result
            // 简单检查是否包含必要的列
            const headers = content.split('\n')[0].toLowerCase()
            if (!headers.includes('username') || !headers.includes('email') || !headers.includes('password')) {
              alert('CSV文件必须包含以下列：username, email, password')
              event.target.value = ''
              return
            }
            selectedFile.value = file
          } catch (error) {
            console.error('文件读取错误:', error)
            alert('文件读取错误，请确保文件格式正确')
            event.target.value = ''
          }
        }
        
        // 使用 UTF-8 编码读取文本文件
        reader.readAsText(file, 'UTF-8')
      }
    }

    // 批量导入用户
    const importUsers = async () => {
      if (!selectedFile.value) return
      
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      
      try {
        console.log('Starting file upload...')
        console.log('File details:', {
          name: selectedFile.value.name,
          size: selectedFile.value.size,
          type: selectedFile.value.type
        })
        
        const response = await api.post('/api/admin/users/import', formData)
        
        console.log('Upload response received:', {
          status: response.status,
          statusText: response.statusText
        })
        
        if (!response.ok) {
          const errorData = await response.json()
          console.error('Error response:', errorData)
          throw new Error(errorData.detail || '导入失败')
        }
        
        const result = await response.json()
        console.log('Import result:', result)
        
        if (result.errors && result.errors.length > 0) {
          alert(`导入失败，但存在以下问题：\n${result.errors.join('\n')}\n\n成功导入 ${result.imported_count} 个用户`)
        } else {
          alert(`成功导入 ${result.imported_count} 个用户`)
        }
        
        await fetchUsers()
        showImportModal.value = false
      } catch (error) {
        console.error('Import failed:', error)
        alert(error.message || '导��用户失败，请检查文件格式是否正确')
      }
    }

    // 格式化日期
    const formatDate = (date) => {
      if (!date) return '从未登录'
      return new Date(date).toLocaleString()
    }

    // 下载模板
    const downloadTemplate = async () => {
      try {
        // 开发环境可以忽略 HTTPS 警告
        // @ts-ignore
        console.warn = () => {}  // 仅开发环境使用
        isDownloading.value = true
        const response = await api.get('/api/admin/users/template', {
          responseType: 'blob'
        })
        
        if (!response.ok) {
          const blob = await response.blob()
          const text = await blob.text()
          throw new Error(text || '下载模板失败')
        }
        
        // 获取文件内容并设置正确的 MIME 类型
        const blob = await response.blob()
        const secureBlob = new Blob([blob], { 
          type: 'text/csv; charset=utf-8'
        })
        
        // 使用 window.navigator.msSaveBlob 处理 IE
        if (window.navigator && window.navigator.msSaveOrOpenBlob) {
          window.navigator.msSaveBlob(secureBlob, 'users_template.csv')
          return
        }
        
        // 对于现代浏览器，使用 data URL
        const url = window.URL.createObjectURL(secureBlob)
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', 'users_template.csv')
        
        // 使用更安全的方式触发下载
        document.body.appendChild(link)
        link.click()
        
        // 延迟清理以确保下载开始
        setTimeout(() => {
          document.body.removeChild(link)
          window.URL.revokeObjectURL(url)
        }, 100)
        
      } catch (error) {
        console.error('下载模板失败:', error)
        alert(error.message || '下载模板失败')
      } finally {
        isDownloading.value = false
      }
    }

    // 修改加载用户列表的方法
    const loadUsers = async () => {
      try {
        const response = await api.get('/api/admin/users')
        if (response.ok) {
          const data = await response.json()
          // 检查返回的数据结构
          const userList = Array.isArray(data) ? data : data.users || []
          users.value = userList.map(user => ({
            ...user,
            is_active: !!user.is_active,
            is_admin: !!user.is_admin,
            can_manage_kb: !!user.can_manage_kb
          }))
        }
      } catch (error) {
        console.error('Error loading users:', error)
      }
    }

    // 修改更新知识库权限的方法
    const updateKbPermission = async (user) => {
      try {
        const response = await api.put(`/api/admin/users/${user.id}/kb-permission`, {
          can_manage_kb: !user.can_manage_kb
        })

        if (!response.ok) {
          throw new Error('Failed to update user KB permission')
        }

        // 更新本地状态
        user.can_manage_kb = !user.can_manage_kb
        
        // 重新加载用户列表以确保数据同步
        await loadUsers()
        
        alert(`已${user.can_manage_kb ? '授予' : '移除'}知识库管理权限`)
      } catch (error) {
        console.error('Failed to update user KB permission:', error)
        user.can_manage_kb = !user.can_manage_kb
        alert('更新知识库权限失败')
      }
    }

    // 添加更新用户状态的方法
    const updateUserStatus = async (user) => {
      try {
        const response = await api.put(`/api/admin/users/${user.id}`, {
          is_active: !user.is_active
        })

        if (!response.ok) {
          throw new Error('Failed to update user status')
        }

        // 更新本地状态
        user.is_active = !user.is_active
        
        // 重新加载用户列表以确保数据同步
        await loadUsers()
        
        alert(`已${user.is_active ? '启用' : '禁用'}用户`)
      } catch (error) {
        console.error('Failed to update user status:', error)
        // 恢复原始状态
        user.is_active = !user.is_active
        alert('更新用户状态失败')
      }
    }

    onMounted(() => {
      loadUsers()
    })

    return {
      users,
      showCreateModal,
      showImportModal,
      selectedFile,
      newUser,
      currentUser,
      error,
      isLoading,
      createUser,
      updateUserRole,
      deleteUser,
      handleFileUpload,
      importUsers,
      formatDate,
      isDownloading,
      downloadTemplate,
      updateKbPermission,
      updateUserStatus
    }
  }
}
</script>

<style scoped>
.admin-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px 0;
}

.header h1 {
  font-size: 24px;
  color: #1e293b;
  margin: 0;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.action-btn .icon {
  margin-right: 10px;
  font-size: 16px;
}

.action-btn.create {
  background-color: #3b82f6;
  color: white;
}

.action-btn.create:hover {
  background-color: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.action-btn.import {
  background-color: #f3f4f6;
  color: #4b5563;
  border: 1px solid #e5e7eb;
}

.action-btn.import:hover {
  background-color: #e5e7eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

/* 创建用户和导入模态框的样式 */
.modal {
  background: white;
  padding: 24px;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1e293b;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
}

.modal-close:hover {
  color: #6b7280;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #4b5563;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.modal-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.modal-btn.confirm {
  background-color: #3b82f6;
  color: white;
}

.modal-btn.confirm:hover {
  background-color: #2563eb;
}

.modal-btn.cancel {
  background-color: #f3f4f6;
  color: #4b5563;
}

.modal-btn.cancel:hover {
  background-color: #e5e7eb;
}

/* 导入提示样式 */
.import-tips {
  background-color: #f8fafc;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.import-tips h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #475569;
}

.import-tips ul {
  margin: 0;
  padding-left: 20px;
}

.import-tips li {
  color: #64748b;
  margin-bottom: 6px;
  font-size: 14px;
}

.template-download {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  color: #3b82f6;
  font-size: 14px;
  text-decoration: none;
  margin: 12px 0;
  transition: all 0.2s;
}

.template-download:hover {
  background-color: #f1f5f9;
  border-color: #cbd5e1;
}

.template-download .icon {
  margin-right: 8px;
}

.users-table {
  margin-top: 24px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  background: #f8fafc;
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
}

td {
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  color: #1e293b;
}

tr:last-child td {
  border-bottom: none;
}

tr:hover {
  background: #f8fafc;
}

.delete-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  background: #fee2e2;
  color: #ef4444;
  cursor: pointer;
  transition: all 0.2s;
}

.delete-btn:hover:not(:disabled) {
  background: #fecaca;
}

.delete-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status-column {
  width: 120px;
  text-align: center;
}

.status-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.toggle-input {
  display: none;
}

.toggle-label {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 16px;
  background: #f3f4f6;
  transition: all 0.3s ease;
}

.toggle-input:checked + .toggle-label {
  background: #e5e7eb;
}

.toggle-button {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #9ca3af;
  margin-right: 6px;
  transition: all 0.3s ease;
}

.toggle-input:checked + .toggle-label .toggle-button {
  background: #10b981;
}

.toggle-input:disabled + .toggle-label {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-text {
  font-size: 14px;
  color: #6b7280;
}

.status-text.active {
  color: #10b981;
}

.status-text.inactive {
  color: #ef4444;
}

.status-text.admin {
  color: #3b82f6;
}

.status-text.kb-enabled {
  color: #8b5cf6;
}

/* 添加移动端适配 */
@media (max-width: 768px) {
  .user-management {
    padding: 16px;
  }

  .header {
    flex-direction: column;
    gap: 16px;
  }

  .header h1 {
    font-size: 20px;
  }

  .user-list {
    margin-top: 16px;
  }

  .user-item {
    padding: 12px;
    flex-direction: column;
    gap: 8px;
  }

  .user-info {
    width: 100%;
  }

  .user-actions {
    width: 100%;
    justify-content: flex-start;
    gap: 8px;
  }

  .action-button {
    padding: 8px 12px;
    font-size: 13px;
  }

  .modal-content {
    width: 100%;
    padding: 16px;
    margin: 0;
  }
}
</style> 