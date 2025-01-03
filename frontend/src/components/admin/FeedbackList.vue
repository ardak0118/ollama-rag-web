<template>
  <div class="feedback-list mobile-adaptive">
    <div class="header">
      <h1>反馈列表</h1>
      <div class="filters">
        <select v-model="currentFilter" @change="loadFeedbacks">
          <option value="all">全部</option>
          <option value="bug">问题反馈</option>
          <option value="feature">功能建议</option>
          <option value="kb">知识库反馈</option>
          <option value="other">其他</option>
        </select>
      </div>
    </div>

    <!-- 反馈列表 -->
    <div class="feedback-grid">
      <div v-if="feedbacks.length === 0" class="empty-state">
        暂无反馈信息
      </div>
      <div v-else v-for="feedback in feedbacks" 
           :key="feedback.id" 
           class="feedback-card"
           @click="viewFeedbackDetail(feedback)">
        <div class="feedback-header">
          <div class="feedback-meta">
            <span class="feedback-type" :class="feedback.type">
              {{ getFeedbackTypeName(feedback.type) }}
            </span>
            <span class="feedback-date">{{ formatDate(feedback.created_at) }}</span>
          </div>
          <span class="feedback-user">{{ feedback.username }}</span>
        </div>
        <div class="feedback-preview">
          {{ feedback.content.slice(0, 100) }}{{ feedback.content.length > 100 ? '...' : '' }}
        </div>
        <div class="feedback-footer">
          <div v-if="feedback.type === 'kb'" class="kb-tag">
            <span class="kb-icon">📚</span>
            {{ feedback.kb_name }}
          </div>
          <div v-if="feedback.has_file" class="file-tag">
            <span class="file-icon">📎</span>
            {{ feedback.file_name }}
          </div>
          <div v-if="feedback.contact" class="contact-tag">
            <span class="contact-icon">📧</span>
            有联系方式
          </div>
        </div>
      </div>
    </div>

    <!-- 分页控件 -->
    <div class="pagination">
      <button 
        :disabled="currentPage === 1"
        @click="changePage(currentPage - 1)"
      >
        上一页
      </button>
      <span>{{ currentPage }} / {{ totalPages }}</span>
      <button 
        :disabled="currentPage === totalPages"
        @click="changePage(currentPage + 1)"
      >
        下一页
      </button>
    </div>

    <!-- 反馈详情对话框 -->
    <div v-if="showDetailDialog" class="modal-overlay" @click="closeDetailDialog">
      <div class="detail-dialog" @click.stop>
        <div class="dialog-header">
          <h2>反馈详情</h2>
          <button class="close-btn" @click="closeDetailDialog">×</button>
        </div>
        <div class="dialog-body" v-if="currentFeedback">
          <div class="detail-meta">
            <div class="meta-item">
              <span class="meta-label">反馈类型:</span>
              <span class="feedback-type" :class="currentFeedback.type">
                {{ getFeedbackTypeName(currentFeedback.type) }}
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">提交时间:</span>
              <span>{{ formatDate(currentFeedback.created_at) }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">提交用户:</span>
              <span>{{ currentFeedback.username }}</span>
            </div>
            <div v-if="currentFeedback.contact" class="meta-item">
              <span class="meta-label">联系方式:</span>
              <span>{{ currentFeedback.contact }}</span>
            </div>
          </div>
          
          <div v-if="currentFeedback.type === 'kb'" class="kb-section">
            <h3>相关知识库</h3>
            <div class="kb-info">
              <div v-if="currentFeedback.kb_name">
                <span class="kb-name" @click="viewKnowledgeBase(currentFeedback.kb_id)">
                  {{ currentFeedback.kb_name }}
                  <span class="view-kb">查看知识库 →</span>
                </span>
                <div class="kb-note" v-if="currentFeedback.kb_id">
                  (ID: {{ currentFeedback.kb_id }})
                </div>
              </div>
              <div v-else class="kb-deleted">
                此知识库已被删除 (ID: {{ currentFeedback.kb_id }})
              </div>
            </div>
          </div>

          <div class="feedback-content">
            <h3>反馈内容</h3>
            <div class="content-box">
              {{ currentFeedback.content }}
            </div>
          </div>

          <div class="detail-actions">
            <button class="delete-btn" @click="deleteFeedback(currentFeedback)">
              删除反馈
            </button>
          </div>

          <div v-if="currentFeedback.file_name" class="file-section">
            <h3>附件</h3>
            <div class="file-info">
              <span class="file-name">
                <i class="fas fa-file"></i>
                {{ currentFeedback.file_name }}
              </span>
              <button class="download-btn" @click="downloadFile(currentFeedback.id)">
                <i class="fas fa-download"></i>
                下载
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加知识库查看对话框 -->
    <div v-if="showKbDialog" class="modal-overlay" @click="closeKbDialog">
      <div class="kb-dialog" @click.stop>
        <div class="dialog-header">
          <h2>知识库详情</h2>
          <button class="close-btn" @click="closeKbDialog">×</button>
        </div>
        <div class="dialog-body" v-if="currentKb">
          <h3>{{ currentKb.name }}</h3>
          <div class="document-list">
            <div v-for="doc in currentKb.documents" 
                 :key="doc.id" 
                 class="document-item"
                 @click="viewDocument(doc)">
              <span class="doc-name">{{ doc.name }}</span>
              <span class="doc-date">{{ formatDate(doc.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加文档内容查看对话框 -->
    <div v-if="showDocDialog" class="modal-overlay" @click="closeDocDialog">
      <div class="doc-dialog" @click.stop>
        <div class="dialog-header">
          <h2>{{ currentDoc?.name }}</h2>
          <button class="close-btn" @click="closeDocDialog">×</button>
        </div>
        <div class="dialog-body">
          <pre class="doc-content">{{ currentDoc?.content }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { api } from '../../utils/api'
import { useRouter } from 'vue-router'

export default {
  name: 'FeedbackList',
  setup() {
    const router = useRouter()
    const feedbacks = ref([])
    const currentFilter = ref('all')
    const currentPage = ref(1)
    const totalPages = ref(1)
    const pageSize = 10
    const showKbDialog = ref(false)
    const showDocDialog = ref(false)
    const currentKb = ref(null)
    const currentDoc = ref(null)
    const showDetailDialog = ref(false)
    const currentFeedback = ref(null)

    const getFeedbackTypeName = (type) => {
      const types = {
        'bug': '问题反馈',
        'feature': '功能建议',
        'kb': '知识库反馈',
        'other': '其他'
      }
      return types[type] || type
    }

    const formatDate = (dateStr) => {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      return date.toLocaleString('zh-CN')
    }

    const loadFeedbacks = async () => {
      try {
        const response = await api.get('/api/feedback', {
          params: {
            type: currentFilter.value === 'all' ? undefined : currentFilter.value,
            page: currentPage.value,
            size: pageSize
          }
        })
        
        if (response.ok) {
          const data = await response.json()
          feedbacks.value = data.items
          totalPages.value = Math.ceil(data.total / pageSize)
        }
      } catch (error) {
        console.error('Error loading feedbacks:', error)
      }
    }

    const deleteFeedback = async (feedback) => {
      if (!confirm('确定要删除这条反馈吗？')) return
      
      try {
        const response = await api.delete(`/api/feedback/${feedback.id}`)
        if (response.ok) {
          await loadFeedbacks()
        }
      } catch (error) {
        console.error('Error deleting feedback:', error)
      }
    }

    const changePage = (page) => {
      currentPage.value = page
      loadFeedbacks()
    }

    const viewKnowledgeBase = async (kbId) => {
      try {
        const response = await api.get(`/api/knowledge-base/${kbId}`)
        if (response.ok) {
          const data = await response.json()
          currentKb.value = data
          showKbDialog.value = true
        } else {
          // 处理错误响应
          if (response.status === 404) {
            alert('该知识库已不存在或已被删除')
          } else {
            const errorData = await response.json().catch(() => ({}))
            alert(errorData.detail || '加载知识库失败')
          }
        }
      } catch (error) {
        console.error('Error loading knowledge base:', error)
        if (error.message.includes('body stream already read')) {
          // 忽略这个特定错误，因为它只是一个技术细节
          return
        }
        alert('加载知识库失败，请稍后重试')
      }
    }

    const viewDocument = (doc) => {
      currentDoc.value = doc
      showDocDialog.value = true
    }

    const closeKbDialog = () => {
      showKbDialog.value = false
      currentKb.value = null
    }

    const closeDocDialog = () => {
      showDocDialog.value = false
      currentDoc.value = null
    }

    const viewFeedbackDetail = (feedback) => {
      currentFeedback.value = feedback
      showDetailDialog.value = true
    }

    const closeDetailDialog = () => {
      showDetailDialog.value = false
      currentFeedback.value = null
    }

    const downloadFile = async (feedbackId) => {
      try {
        const response = await api.get(`/api/feedback/download/${feedbackId}`, {
          responseType: 'blob'
        })
        
        if (response.ok) {
          const blob = await response.blob()
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          
          // 从 Content-Disposition 头获取文件名
          const contentDisposition = response.headers.get('content-disposition')
          let filename = 'download'
          
          if (contentDisposition) {
            const matches = /filename\*=UTF-8''(.+)/.exec(contentDisposition)
            if (matches && matches[1]) {
              filename = decodeURIComponent(matches[1])
            }
          }
          
          a.download = filename
          document.body.appendChild(a)
          a.click()
          window.URL.revokeObjectURL(url)
          a.remove()
        } else {
          throw new Error('下载失败')
        }
      } catch (error) {
        console.error('Error downloading file:', error)
        alert('下载失败：' + error.message)
      }
    }

    onMounted(() => {
      loadFeedbacks()
    })

    return {
      feedbacks,
      currentFilter,
      currentPage,
      totalPages,
      getFeedbackTypeName,
      formatDate,
      loadFeedbacks,
      deleteFeedback,
      changePage,
      showKbDialog,
      showDocDialog,
      currentKb,
      currentDoc,
      viewKnowledgeBase,
      viewDocument,
      closeKbDialog,
      closeDocDialog,
      showDetailDialog,
      currentFeedback,
      viewFeedbackDetail,
      closeDetailDialog,
      downloadFile
    }
  }
}
</script>

<style scoped>
.feedback-list {
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

.filters select {
  padding: 8px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
}

.feedback-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 24px;
}

.feedback-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s;
}

.feedback-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.feedback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.feedback-type {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.feedback-type.bug {
  background-color: #fee2e2;
  color: #dc2626;
}

.feedback-type.feature {
  background-color: #e0f2fe;
  color: #0284c7;
}

.feedback-type.other {
  background-color: #f3f4f6;
  color: #4b5563;
}

.feedback-date {
  font-size: 12px;
  color: #6b7280;
}

.feedback-content {
  margin-bottom: 16px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.feedback-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.username {
  font-weight: 500;
  color: #374151;
}

.contact {
  font-size: 12px;
  color: #6b7280;
}

.delete-btn {
  padding: 6px 12px;
  background-color: #fee2e2;
  color: #dc2626;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.delete-btn:hover {
  background-color: #fecaca;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background-color: white;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: #6b7280;
  background: white;
  border-radius: 8px;
}

.kb-info {
  margin-bottom: 8px;
  padding: 8px;
  background-color: #f3f4f6;
  border-radius: 4px;
}

.kb-label {
  font-weight: 500;
  color: #4b5563;
  margin-right: 8px;
}

.kb-name {
  color: #2563eb;
  cursor: pointer;
  text-decoration: underline;
}

.kb-name:hover {
  color: #1d4ed8;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.kb-dialog,
.doc-dialog {
  background: white;
  border-radius: 8px;
  padding: 24px;
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  overflow-y: auto;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.dialog-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1e293b;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #64748b;
  cursor: pointer;
}

.document-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.document-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: #f8fafc;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.document-item:hover {
  background-color: #f1f5f9;
}

.doc-name {
  font-weight: 500;
  color: #0f172a;
}

.doc-date {
  font-size: 12px;
  color: #64748b;
}

.doc-content {
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 14px;
  line-height: 1.6;
  padding: 16px;
  background-color: #f8fafc;
  border-radius: 6px;
  max-height: 60vh;
  overflow-y: auto;
}

.feedback-preview {
  color: #4b5563;
  margin: 12px 0;
  line-height: 1.5;
}

.feedback-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.feedback-user {
  font-weight: 500;
  color: #1f2937;
}

.kb-tag, .contact-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.kb-tag {
  background-color: #dbeafe;
  color: #2563eb;
}

.contact-tag {
  background-color: #f3f4f6;
  color: #4b5563;
}

.detail-dialog {
  width: 90%;
  max-width: 800px;
  background: white;
  border-radius: 12px;
  padding: 24px;
}

.detail-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  color: #64748b;
}

.kb-section {
  margin: 24px 0;
}

.content-box {
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  white-space: pre-wrap;
  line-height: 1.6;
}

.detail-actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

.view-kb {
  color: #2563eb;
  font-size: 14px;
}

.kb-note {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}

.kb-deleted {
  color: #ef4444;
  font-style: italic;
  padding: 8px;
  background-color: #fee2e2;
  border-radius: 4px;
}

/* 添加移动端适配样式 */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }

  .header h1 {
    font-size: 20px;
  }

  .filters {
    width: 100%;
  }

  .filters select {
    width: 100%;
  }

  .feedback-grid {
    padding: 16px;
    gap: 16px;
  }

  .feedback-card {
    padding: 16px;
  }

  .feedback-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .feedback-meta {
    width: 100%;
    justify-content: space-between;
  }

  .feedback-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .detail-dialog,
  .kb-dialog,
  .doc-dialog {
    width: 100%;
    height: 100%;
    max-width: none;
    max-height: none;
    border-radius: 0;
    padding: 16px;
    margin: 0;
  }

  .detail-meta {
    grid-template-columns: 1fr;
    padding: 12px;
  }

  .document-list {
    margin-top: 16px;
  }

  .document-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .doc-date {
    width: 100%;
    text-align: left;
  }

  .pagination {
    flex-wrap: wrap;
    padding: 16px;
  }

  .modal-overlay {
    align-items: flex-end;
  }

  .kb-info {
    padding: 12px;
  }

  .content-box {
    padding: 12px;
  }

  .detail-actions {
    margin-top: 16px;
  }

  .delete-btn {
    width: 100%;
    padding: 12px;
    font-size: 14px;
  }
}

/* 添加文件下载相关样式 */
.file-section {
  margin-top: 1.5rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.file-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.5rem;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #495057;
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.download-btn:hover {
  background-color: #0056b3;
}

.file-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background-color: #e9ecef;
  border-radius: 4px;
  font-size: 12px;
  color: #495057;
}

.file-icon {
  font-size: 14px;
}
</style> 