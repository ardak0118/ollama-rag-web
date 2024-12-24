<template>
  <div class="system-settings">
    <h2>系统设置</h2>
    
    <!-- 基本设置 -->
    <div class="settings-section">
      <h3>基本设置</h3>
      <div class="settings-form">
        <div class="form-group">
          <label>系统名称</label>
          <input v-model="settings.systemName" type="text" />
        </div>
        <div class="form-group">
          <label>系统描述</label>
          <textarea v-model="settings.description" rows="3"></textarea>
        </div>
      </div>
    </div>
    
    <!-- AI 模型设置 -->
    <div class="settings-section">
      <h3>AI 模型设置</h3>
      <div class="settings-form">
        <div class="form-group">
          <label>默认模型</label>
          <select v-model="settings.defaultModel">
            <option value="qwen2.5:latest">Qwen 2.5</option>
            <option value="qwen:7b">Qwen 7B</option>
            <option value="llama2:7b">LLaMA2 7B</option>
          </select>
        </div>
        <div class="form-group">
          <label>最大上下文长度</label>
          <input v-model.number="settings.maxContextLength" type="number" />
        </div>
        <div class="form-group">
          <label>温度</label>
          <input 
            v-model.number="settings.temperature" 
            type="range" 
            min="0" 
            max="1" 
            step="0.1" 
          />
          <span>{{ settings.temperature }}</span>
        </div>
      </div>
    </div>
    
    <!-- 知识库设置 -->
    <div class="settings-section">
      <h3>知识库设置</h3>
      <div class="settings-form">
        <div class="form-group">
          <label>文档分块大小</label>
          <input v-model.number="settings.chunkSize" type="number" />
        </div>
        <div class="form-group">
          <label>分块重叠大小</label>
          <input v-model.number="settings.chunkOverlap" type="number" />
        </div>
        <div class="form-group">
          <label>向量模型</label>
          <select v-model="settings.embeddingModel">
            <option value="bge-large-zh">BGE-Large-ZH</option>
            <option value="m3e-base">M3E-Base</option>
          </select>
        </div>
      </div>
    </div>
    
    <!-- 系统维护 -->
    <div class="settings-section">
      <h3>系统维护</h3>
      <div class="maintenance-actions">
        <button @click="rebuildVectorStore" class="btn warning">
          重建向量库
        </button>
        <button @click="clearCache" class="btn">
          清理缓存
        </button>
        <button @click="backupSystem" class="btn primary">
          系统备份
        </button>
      </div>
    </div>
    
    <!-- 保存按钮 -->
    <div class="actions">
      <button 
        @click="saveSettings" 
        class="btn primary"
        :disabled="isSaving"
      >
        {{ isSaving ? '保存中...' : '保存设置' }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { api } from '../../utils/api'

export default {
  name: 'SystemSettings',
  
  setup() {
    const settings = ref({
      systemName: '',
      description: '',
      defaultModel: 'qwen2.5:latest',
      maxContextLength: 4096,
      temperature: 0.7,
      chunkSize: 500,
      chunkOverlap: 50,
      embeddingModel: 'bge-large-zh'
    })
    
    const isSaving = ref(false)
    
    // 加载设置
    const loadSettings = async () => {
      try {
        const response = await api.get('/admin/settings')
        if (response.ok) {
          settings.value = await response.json()
        }
      } catch (error) {
        console.error('Failed to load settings:', error)
      }
    }
    
    // 保存设置
    const saveSettings = async () => {
      try {
        isSaving.value = true
        const response = await api.post('/admin/settings', settings.value)
        if (!response.ok) {
          throw new Error('Failed to save settings')
        }
        alert('设置保存成功')
      } catch (error) {
        console.error('Failed to save settings:', error)
        alert('保存设置失败')
      } finally {
        isSaving.value = false
      }
    }
    
    // 重建向量库
    const rebuildVectorStore = async () => {
      if (!confirm('确定要重建向量库吗？这可能需要一些时间。')) return
      
      try {
        const response = await api.post('/admin/rebuild-vectors')
        if (!response.ok) {
          throw new Error('Failed to rebuild vector store')
        }
        alert('向量库重建已开始，请稍后查看进度')
      } catch (error) {
        console.error('Failed to rebuild vector store:', error)
        alert('重建向量库失败')
      }
    }
    
    // 清理缓存
    const clearCache = async () => {
      try {
        const response = await api.post('/admin/clear-cache')
        if (!response.ok) {
          throw new Error('Failed to clear cache')
        }
        alert('缓存清理成功')
      } catch (error) {
        console.error('Failed to clear cache:', error)
        alert('清理缓存失败')
      }
    }
    
    // 系统备份
    const backupSystem = async () => {
      try {
        const response = await api.post('/admin/backup')
        if (!response.ok) {
          throw new Error('Failed to backup system')
        }
        alert('系统备份成功')
      } catch (error) {
        console.error('Failed to backup system:', error)
        alert('系统备份失败')
      }
    }
    
    onMounted(() => {
      loadSettings()
    })
    
    return {
      settings,
      isSaving,
      saveSettings,
      rebuildVectorStore,
      clearCache,
      backupSystem
    }
  }
}
</script>

<style scoped>
.system-settings {
  max-width: 800px;
  margin: 0 auto;
}

.settings-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.settings-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #1e293b;
  font-size: 1.25rem;
}

.settings-form {
  display: grid;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.875rem;
  color: #4b5563;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.form-group textarea {
  resize: vertical;
}

.maintenance-actions {
  display: flex;
  gap: 1rem;
}

.actions {
  margin-top: 2rem;
  display: flex;
  justify-content: flex-end;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn.primary {
  background-color: #2563eb;
  color: white;
}

.btn.primary:hover {
  background-color: #1d4ed8;
}

.btn.warning {
  background-color: #f59e0b;
  color: white;
}

.btn.warning:hover {
  background-color: #d97706;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>