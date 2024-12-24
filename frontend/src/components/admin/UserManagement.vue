<template>
  <div class="admin-container">
    <div class="header">
      <h1>用户管理</h1>
      <div class="actions">
        <button class="btn primary" @click="showCreateModal = true">
          创建用户
        </button>
        <button class="btn" @click="showImportModal = true">
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
            <th>角色</th>
            <th>状态</th>
            <th>最后活动</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.username }}</td>
            <td>{{ user.email }}</td>
            <td>
              <select 
                v-model="user.is_admin"
                @change="updateUserRole(user)"
                :disabled="user.is_admin && currentUser.id !== user.id"
              >
                <option :value="false">普通用户</option>
                <option :value="true">管理员</option>
              </select>
            </td>
            <td>
              <span :class="['status-badge', user.is_active ? 'active' : 'inactive']">
                {{ user.is_active ? '活跃' : '禁用' }}
              </span>
            </td>
            <td>{{ formatDate(user.last_login) }}</td>
            <td>
              <button 
                class="btn danger"
                @click="deleteUser(user)"
                :disabled="user.is_admin && currentUser.id !== user.id"
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
        const response = await api.get('/admin/users')
        if (!response.ok) {
          throw new Error('Failed to fetch users')
        }
        users.value = await response.json()
      } catch (error) {
        console.error('Failed to fetch users:', error)
      }
    }

    // 创建用户
    const createUser = async () => {
      try {
        isLoading.value = true
        error.value = null

        const response = await api.post('/admin/users', {
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
        const response = await api.put(`/admin/users/${user.id}`, {
          is_admin: user.is_admin
        })
        if (!response.ok) {
          throw new Error('Failed to update user role')
        }
        await fetchUsers()
      } catch (error) {
        console.error('Failed to update user role:', error)
      }
    }

    // 删除用户
    const deleteUser = async (user) => {
      if (!confirm(`确定要删除用户 ${user.username} 吗？`)) return
      
      try {
        const response = await api.delete(`/admin/users/${user.id}`)
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
      selectedFile.value = event.target.files[0]
    }

    // 批量导入用户
    const importUsers = async () => {
      if (!selectedFile.value) return
      
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      
      try {
        await api.post('/api/admin/users/import', formData)
        await fetchUsers()
        showImportModal.value = false
      } catch (error) {
        console.error('Failed to import users:', error)
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
        isDownloading.value = true
        const response = await api.get('/admin/users/template', {
          responseType: 'blob'  // 指定响应类型为 blob
        })
        
        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(errorText || '下载模板失败')
        }
        
        // 获取文件内容
        const blob = await response.blob()
        
        // 创建下载链接
        const url = window.URL.createObjectURL(
          new Blob([blob], { type: 'text/csv;charset=utf-8' })
        )
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', 'users_template.csv')
        
        // 触发下载
        document.body.appendChild(link)
        link.click()
        
        // 清理
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        
      } catch (error) {
        console.error('下载模板失败:', error)
      } finally {
        isDownloading.value = false
      }
    }

    onMounted(() => {
      fetchUsers()
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
      downloadTemplate
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
}

.actions {
  display: flex;
  gap: 12px;
}

.users-table {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

th {
  background-color: #f9fafb;
  font-weight: 500;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.status-badge.active {
  background-color: #dcfce7;
  color: #166534;
}

.status-badge.inactive {
  background-color: #fee2e2;
  color: #991b1b;
}

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn.primary {
  background-color: #3b82f6;
  color: white;
}

.btn.danger {
  background-color: #ef4444;
  color: white;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}

.import-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.template-download {
  margin: 10px 0;
}

.btn.secondary {
  background-color: #e5e7eb;
  color: #374151;
}

.btn.secondary:hover {
  background-color: #d1d5db;
}

.btn.secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style> 