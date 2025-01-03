<template>
  <div class="admin-test mobile-adaptive">
    <h2>管理员权限测试</h2>
    
    <!-- 测试结果 -->
    <div class="test-results">
      <div class="test-item">
        <span>管理员状态:</span>
        <span :class="['status', authStore.isAdmin ? 'success' : 'error']">
          {{ authStore.isAdmin ? '是' : '否' }}
        </span>
      </div>
      
      <!-- 统计信息 -->
      <div v-if="stats" class="stats-section">
        <h3>系统统计</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">总用户数</div>
            <div class="stat-value">{{ stats.user_stats.total }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">管理员数</div>
            <div class="stat-value">{{ stats.user_stats.admin }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">活跃用户数</div>
            <div class="stat-value">{{ stats.user_stats.active }}</div>
          </div>
        </div>

        <!-- 最近注册用户 -->
        <div v-if="stats.recent_users.length" class="recent-section">
          <h3>最近注册用户</h3>
          <ul class="recent-list">
            <li v-for="user in stats.recent_users" :key="user.id">
              {{ user.username }} ({{ user.email }})
              <span class="time">{{ formatDate(user.created_at) }}</span>
            </li>
          </ul>
        </div>

        <!-- 最近登录用户 -->
        <div v-if="stats.recent_logins.length" class="recent-section">
          <h3>最近登录用户</h3>
          <ul class="recent-list">
            <li v-for="user in stats.recent_logins" :key="user.id">
              {{ user.username }}
              <span class="time">{{ formatDate(user.last_login) }}</span>
            </li>
          </ul>
        </div>
      </div>
      
      <!-- 测试按钮 -->
      <div class="test-actions">
        <button @click="testAdminAPI" class="btn">测试管理员 API</button>
        <button @click="refreshStats" class="btn">刷新统计</button>
      </div>
      
      <!-- API 测试结果 -->
      <div v-if="testResults.length" class="api-results">
        <h3>API 测试结果:</h3>
        <div v-for="(result, index) in testResults" 
             :key="index"
             :class="['result-item', result.success ? 'success' : 'error']">
          {{ result.message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { api } from '../../utils/api'
import { authStore } from '../../store/auth'

export default {
  name: 'AdminTest',
  setup() {
    const testResults = ref([])
    const stats = ref(null)
    
    const formatDate = (dateString) => {
      if (!dateString) return '未知'
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
    
    const testAdminAPI = async () => {
      try {
        const response = await api.get('/api/admin/test')
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || 'Admin API test failed')
        }
        const data = await response.json()
        testResults.value.push({
          success: true,
          message: `管理员 API 测试成功: ${data.message}`
        })
      } catch (error) {
        console.error('Failed to test admin API:', error)
        testResults.value.push({
          success: false,
          message: `管理员 API 测试失败: ${error.message}`
        })
      }
    }
    
    const refreshStats = async () => {
      try {
        const response = await api.get('/api/admin/stats')
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(JSON.stringify(errorData))
        }
        stats.value = await response.json()
      } catch (error) {
        console.error('Failed to fetch stats:', error)
        throw error
      }
    }
    
    onMounted(async () => {
      await refreshStats()
    })
    
    return {
      authStore,
      testResults,
      stats,
      testAdminAPI,
      refreshStats,
      formatDate
    }
  }
}
</script>

<style scoped>
.admin-test {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.test-results {
  margin: 20px 0;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.test-item {
  margin: 10px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 14px;
}

.status.success {
  background-color: #dcfce7;
  color: #166534;
}

.status.error {
  background-color: #fee2e2;
  color: #991b1b;
}

.stats-section {
  margin: 20px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.stat-item {
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #0f172a;
}

.test-actions {
  display: flex;
  gap: 12px;
  margin: 20px 0;
}

.btn {
  padding: 8px 16px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn:hover {
  background-color: #2563eb;
}

.api-results {
  margin-top: 20px;
}

.result-item {
  padding: 12px;
  margin: 8px 0;
  border-radius: 6px;
}

.result-item.success {
  background-color: #dcfce7;
  color: #166534;
}

.result-item.error {
  background-color: #fee2e2;
  color: #991b1b;
}

.recent-section {
  margin-top: 24px;
}

.recent-list {
  list-style: none;
  padding: 0;
  margin: 12px 0;
}

.recent-list li {
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 4px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.time {
  font-size: 12px;
  color: #64748b;
}

/* 添加移动端适配 */
@media (max-width: 768px) {
  .admin-test {
    padding: 16px;
  }

  .test-section {
    padding: 16px;
    margin-bottom: 16px;
  }

  .test-button {
    width: 100%;
    padding: 12px;
    font-size: 14px;
    margin-bottom: 8px;
  }

  .result-box {
    padding: 12px;
    font-size: 14px;
    margin-top: 12px;
  }
}
</style> 