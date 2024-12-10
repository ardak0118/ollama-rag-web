<template>
  <div class="knowledge-page">
    <div class="header">
      <h1>知识库管理</h1>
      <button class="back-btn" @click="goBack">返回聊天</button>
    </div>

    <div class="main-content">
      <!-- 添加知识库 -->
      <div class="section">
        <h2>添加知识库</h2>
        <div class="add-knowledge">
          <input 
            type="text" 
            v-model="newKnowledgeBase.name" 
            placeholder="知识库名称"
          >
          <button @click="addKnowledgeBase" :disabled="!newKnowledgeBase.name.trim()">
            创建知识库
          </button>
        </div>
      </div>

      <!-- 知识库列表 -->
      <div class="section">
        <h2>知识库列表</h2>
        <div class="knowledge-list">
          <div v-if="knowledgeBases.length === 0" class="empty-state">
            暂无知识库，请创建新的知识库
          </div>
          <div v-else v-for="kb in knowledgeBases" 
               :key="kb.id" 
               class="knowledge-item">
            <div class="kb-info">
              <h3>{{ kb.name }}</h3>
              <p>文档数量: {{ kb.documentCount }}</p>
            </div>
            <div class="kb-actions">
              <button class="action-btn upload-btn" @click="uploadDocument(kb)">
                上传文档
              </button>
              <button class="action-btn view-btn" @click="viewDocuments(kb)">
                查看文档
              </button>
              <button class="action-btn edit-btn" @click="editKnowledgeBase(kb)">
                编辑
              </button>
              <button class="action-btn delete-btn" @click="deleteKnowledgeBase(kb)">
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 上传文档对话框 -->
    <div v-if="showUploadDialog" class="dialog-overlay">
      <div class="dialog">
        <h2>上传文档到 {{ currentKnowledgeBase?.name }}</h2>
        <div class="upload-area">
          <div class="upload-box" @click="triggerFileInput">
            <input 
              type="file" 
              ref="fileInput"
              @change="handleFileUpload" 
              accept=".txt,.pdf,.doc,.docx"
              style="display: none"
            >
            <div class="upload-icon">📄</div>
            <div class="upload-text">
              点击或拖拽文件到此处上传<br>
              <span class="upload-hint">支持 .txt, .pdf, .doc, .docx 格式</span>
            </div>
          </div>
          <div v-if="selectedFile" class="selected-file">
            已选择: {{ selectedFile.name }}
          </div>
        </div>
        <div class="dialog-actions">
          <button class="confirm-btn" 
                  @click="submitUpload"
                  :disabled="!selectedFile || isUploading">
            {{ isUploading ? '上传中...' : '上传' }}
          </button>
          <button class="cancel-btn" @click="cancelUpload">取消</button>
        </div>
      </div>
    </div>

    <!-- 文档列表对话框 -->
    <div v-if="showDocumentsDialog" class="dialog-overlay">
      <div class="dialog documents-dialog">
        <div class="dialog-header">
          <h2>{{ currentKnowledgeBase?.name }} - 文档列表</h2>
          <button class="close-btn" @click="showDocumentsDialog = false">×</button>
        </div>
        <div class="documents-list">
          <div v-if="documents.length === 0" class="empty-state">
            暂无文档
          </div>
          <div v-else v-for="doc in documents" 
               :key="doc.id" 
               class="document-item">
            <div class="doc-info">
              <span class="doc-name">{{ doc.name }}</span>
              <span class="doc-date">{{ formatDate(doc.created_at) }}</span>
            </div>
            <div class="doc-actions">
              <button class="doc-btn view-btn" @click="viewDocument(doc)">
                查看
              </button>
              <button class="doc-btn delete-btn" @click="deleteDocument(doc)">
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加文档查看对话框 -->
    <div v-if="showDocumentViewDialog" class="dialog-overlay">
      <div class="dialog document-view-dialog">
        <div class="dialog-header">
          <h2>{{ currentDocument?.name }}</h2>
          <button class="close-btn" @click="closeDocumentView">×</button>
        </div>
        <div class="document-content">
          {{ documentContent }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { api } from '../utils/api'

export default {
  name: 'KnowledgeBasePage',
  data() {
    return {
      knowledgeBases: [],
      newKnowledgeBase: {
        name: ''
      },
      currentKnowledgeBase: null,
      showUploadDialog: false,
      showDocumentsDialog: false,
      selectedFile: null,
      documents: [],
      isUploading: false,
      showDocumentViewDialog: false,  // 添加文档查看对话框的显示状态
      currentDocument: null,          // 当前查看的文档
      documentContent: '',            // 文档内容
    }
  },
  methods: {
    goBack() {
      this.$router.push('/')
    },
    async loadKnowledgeBases() {
      try {
        const response = await api.get('/api/knowledge-base')
        const data = await response.json()
        this.knowledgeBases = data.knowledge_bases
      } catch (error) {
        console.error('Error loading knowledge bases:', error)
      }
    },
    async addKnowledgeBase() {
      if (!this.newKnowledgeBase.name.trim()) return
      
      try {
        const response = await api.post('/api/knowledge-base', this.newKnowledgeBase)
        if (response.ok) {
          await this.loadKnowledgeBases()
          this.newKnowledgeBase.name = ''
        }
      } catch (error) {
        console.error('Error adding knowledge base:', error)
      }
    },
    async editKnowledgeBase(kb) {
      // 实现编辑功能
      console.log('Edit knowledge base:', kb)
    },
    async deleteKnowledgeBase(kb) {
      if (!confirm(`确定要删除知识库 "${kb.name}" 吗？`)) return
      
      try {
        await api.delete(`/api/knowledge-base/${kb.id}`)
        await this.loadKnowledgeBases()
      } catch (error) {
        console.error('Error deleting knowledge base:', error)
      }
    },
    uploadDocument(kb) {
      this.currentKnowledgeBase = kb
      this.showUploadDialog = true
    },
    viewDocuments(kb) {
      this.currentKnowledgeBase = kb
      this.showDocumentsDialog = true
    },
    // 文件上传相关方法
    triggerFileInput() {
      this.$refs.fileInput.click()
    },

    async handleFileUpload(event) {
      const file = event.target.files[0]
      if (file) {
        this.selectedFile = file
      }
    },

    async submitUpload() {
      if (!this.selectedFile || !this.currentKnowledgeBase) return
      
      this.isUploading = true
      const formData = new FormData()
      formData.append('file', this.selectedFile)

      try {
        const response = await api.post(
          `/api/knowledge-base/${this.currentKnowledgeBase.id}/upload`,
          formData
        )

        const data = await response.json()
        console.log('Upload successful:', data)
        
        // 刷新知识库列表
        await this.loadKnowledgeBases()
        // 关闭上传对话框
        this.showUploadDialog = false
        this.selectedFile = null
        
        // 显示成功消息
        alert('文档上传成功')
      } catch (error) {
        console.error('Error uploading document:', error)
        alert('上传失败：' + (error.message || '未知错误'))
      } finally {
        this.isUploading = false
      }
    },

    cancelUpload() {
      this.selectedFile = null
      this.showUploadDialog = false
    },

    // 文档管理相关方法
    async loadDocuments(kb) {
      try {
        const response = await api.get(`/api/knowledge-base/${kb.id}/documents`)
        const data = await response.json()
        this.documents = data.documents
      } catch (error) {
        console.error('Error loading documents:', error)
      }
    },

    async viewDocuments(kb) {
      this.currentKnowledgeBase = kb
      await this.loadDocuments(kb)
      this.showDocumentsDialog = true
    },

    async deleteDocument(doc) {
      if (!confirm(`确定要删除文档 "${doc.name}" 吗？`)) return

      try {
        await api.delete(
          `/api/knowledge-base/${this.currentKnowledgeBase.id}/documents/${doc.id}`
        )
        await this.loadDocuments(this.currentKnowledgeBase)
      } catch (error) {
        console.error('Error deleting document:', error)
      }
    },

    formatDate(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    },

    // 查看文档内容
    async viewDocument(doc) {
      try {
        const response = await api.get(
          `/api/knowledge-base/${this.currentKnowledgeBase.id}/documents/${doc.id}`
        )
        
        if (response.ok) {
          const data = await response.json()
          this.currentDocument = {
            ...doc,
            content: data.content
          }
          this.documentContent = data.content
          this.showDocumentViewDialog = true
        }
      } catch (error) {
        console.error('Error viewing document:', error)
      }
    },

    // 关闭文档查看对话框
    closeDocumentView() {
      this.showDocumentViewDialog = false
      this.currentDocument = null
      this.documentContent = ''
    }
  },
  async created() {
    await this.loadKnowledgeBases()
  }
}
</script>

<style scoped>
.knowledge-page {
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

.back-btn {
  padding: 8px 16px;
  background-color: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
}

.section {
  background-color: white;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.add-knowledge {
  display: flex;
  gap: 12px;
}

.add-knowledge input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.knowledge-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 12px;
}

.kb-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.upload-btn {
  background-color: #3b82f6;
  color: white;
}

.view-btn {
  background-color: #10b981;
  color: white;
}

.edit-btn {
  background-color: #f59e0b;
  color: white;
}

.delete-btn {
  background-color: #ef4444;
  color: white;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: #6b7280;
}

/* 添加对话框样式 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background-color: white;
  border-radius: 8px;
  padding: 24px;
  min-width: 400px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.documents-dialog {
  width: 800px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #6b7280;
  cursor: pointer;
}

.upload-area {
  margin-bottom: 16px;
}

.upload-box {
  border: 2px dashed #e5e7eb;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
}

.upload-box:hover {
  border-color: #3b82f6;
  background-color: #f9fafb;
}

.upload-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.upload-hint {
  color: #6b7280;
  font-size: 12px;
}

.selected-file {
  margin-top: 8px;
  padding: 8px;
  background-color: #f3f4f6;
  border-radius: 4px;
}

.documents-list {
  margin-top: 16px;
}

.document-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 8px;
}

.doc-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-name {
  font-weight: 500;
}

.doc-date {
  font-size: 12px;
  color: #6b7280;
}

.doc-actions {
  display: flex;
  gap: 8px;
}

.doc-btn {
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.view-btn {
  background-color: #3b82f6;
  color: white;
}

.delete-btn {
  background-color: #ef4444;
  color: white;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.confirm-btn, .cancel-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.confirm-btn {
  background-color: #3b82f6;
  color: white;
}

.confirm-btn:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}

.cancel-btn {
  background-color: #e5e7eb;
  color: #374151;
}

/* 添加文档查看对话框样式 */
.document-view-dialog {
  width: 90%;
  max-width: 1000px;
  height: 80vh;
  display: flex;
  flex-direction: column;
}

.document-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  margin-top: 16px;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.dialog-header h2 {
  margin: 0;
  font-size: 18px;
  color: #374151;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #6b7280;
  cursor: pointer;
  padding: 4px;
}

.close-btn:hover {
  color: #374151;
}
</style> 