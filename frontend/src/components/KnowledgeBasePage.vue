<template>
  <div class="knowledge-page mobile-adaptive">
    <div class="header">
      <h1>知识库管理</h1>
      <button class="back-btn" @click="goBack">返回聊天</button>
    </div>

    <div class="main-content">
      <!-- 管理功能只对有权限的用户显示 -->
      <div v-if="authStore.canManageKB" class="section">
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

      <!-- 知识库列表对所有用户可见 -->
      <div class="section">
        <h2>知识库列表</h2>
        <div class="knowledge-list">
          <div v-if="knowledgeBases.length === 0" class="empty-state">
            暂无知识库
          </div>
          <div v-else v-for="kb in knowledgeBases" 
               :key="kb.id" 
               class="knowledge-item">
            <div class="kb-info">
              <h3>{{ kb.name }}</h3>
              <p>文档数量: {{ kb.documentCount }}</p>
            </div>
            <div class="kb-actions">
              <!-- 管理功能只对有权限的用户显示 -->
              <template v-if="authStore.canManageKB">
                <button class="action-btn upload-btn" @click="uploadDocument(kb)">
                  上传文档
                </button>
                <button class="action-btn edit-btn" @click="editKnowledgeBase(kb)">
                  编辑
                </button>
                <button class="action-btn delete-btn" @click="deleteKnowledgeBase(kb)">
                  删除
                </button>
              </template>
              <!-- 查看功能对所有用户可用 -->
              <button class="action-btn view-btn" @click="viewDocuments(kb)">
                查看文档
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 上传文档对话框（仅管理员可见） -->
    <div v-if="showUploadDialog && authStore.canManageKB" class="dialog-overlay">
      <div class="dialog">
        <h2>上传文档到 {{ currentKnowledgeBase?.name }}</h2>
        <div class="upload-area">
          <div class="upload-box" @click="triggerFileInput">
            <input 
              type="file" 
              ref="fileInput"
              :ref="el => fileInput = el"
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

    <!-- 文档列表对话框（所有用户可见） -->
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
              <!-- 删除按钮只对管理员显示 -->
              <button v-if="authStore.canManageKB" 
                      class="doc-btn delete-btn" 
                      @click="deleteDocument(doc)">
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 文档查看对话框（所有用户可见） -->
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
import { ref, onMounted } from 'vue'
import { api } from '../utils/api'
import { authStore } from '../store/auth'
import { useRouter } from 'vue-router'

export default {
  name: 'KnowledgeBasePage',
  setup() {
    const router = useRouter()
    const fileInput = ref(null)

    // 修改 onMounted，移除权限检查
    onMounted(async () => {
      await loadKnowledgeBases()
    })

    const knowledgeBases = ref([])
    const newKnowledgeBase = ref({
      name: ''
    })
    const currentKnowledgeBase = ref(null)
    const showUploadDialog = ref(false)
    const showDocumentsDialog = ref(false)
    const selectedFile = ref(null)
    const documents = ref([])
    const isUploading = ref(false)
    const showDocumentViewDialog = ref(false)  // 添加文档查看对话框的显示状态
    const currentDocument = ref(null)          // 当前查看的文档
    const documentContent = ref('')            // 文档内容

    const loadKnowledgeBases = async () => {
      try {
        const response = await api.get('/api/knowledge-base')
        const data = await response.json()
        knowledgeBases.value = data.knowledge_bases
      } catch (error) {
        console.error('Error loading knowledge bases:', error)
      }
    }

    const addKnowledgeBase = async () => {
      if (!newKnowledgeBase.value.name.trim()) return
      
      try {
        const response = await api.post('/api/knowledge-base', newKnowledgeBase.value)
        if (response.ok) {
          await loadKnowledgeBases()
          newKnowledgeBase.value.name = ''
        }
      } catch (error) {
        console.error('Error adding knowledge base:', error)
      }
    }

    const editKnowledgeBase = async (kb) => {
      // 实现编辑功能
      console.log('Edit knowledge base:', kb)
    }

    const deleteKnowledgeBase = async (kb) => {
      if (!confirm(`确定要删除知识库 "${kb.name}" 吗？`)) return
      
      try {
        await api.delete(`/api/knowledge-base/${kb.id}`)
        await loadKnowledgeBases()
      } catch (error) {
        console.error('Error deleting knowledge base:', error)
      }
    }

    const uploadDocument = (kb) => {
      currentKnowledgeBase.value = kb
      showUploadDialog.value = true
    }

    // 文件上传相关方法
    const triggerFileInput = () => {
      if (fileInput.value) {
        fileInput.value.click()
      }
    }

    const handleFileUpload = async (event) => {
      const file = event.target.files[0]
      if (file) {
        selectedFile.value = file
      }
    }

    const submitUpload = async () => {
      if (!selectedFile.value) {
        showError('请选择文件');
        return;
      }

      if (!currentKnowledgeBase.value) {
        showError('请选择知识库');
        return;
      }

      // 检查文件类型
      const allowedTypes = ['.txt', '.pdf', '.md', '.doc', '.docx'];
      const fileExt = selectedFile.value.name.substring(selectedFile.value.name.lastIndexOf('.')).toLowerCase();
      if (!allowedTypes.includes(fileExt)) {
        showError(`不支持的文件类型。支持的类型：${allowedTypes.join(', ')}`);
        return;
      }

      isUploading.value = true;
      const formData = new FormData();
      formData.append('file', selectedFile.value);

      try {
        console.log('Uploading file:', selectedFile.value.name);
        console.log('To knowledge base:', currentKnowledgeBase.value.id);

        const response = await api.post(
          `/api/knowledge-base/${currentKnowledgeBase.value.id}/upload`,
          formData
        );

        // 打印完整的响应信息
        console.log('Upload response:', {
          status: response.status,
          statusText: response.statusText,
          headers: Object.fromEntries(response.headers.entries())
        });

        if (response.ok) {
          const data = await response.json();
          console.log('Upload success:', data);
          showSuccess('文件上传成功');
          selectedFile.value = null;
          showUploadDialog.value = false;
          await loadKnowledgeBases();
        } else {
          const error = await response.json();
          console.error('Upload error:', error);
          showError(`上传失败: ${error.detail || JSON.stringify(error)}`);
        }
      } catch (error) {
        console.error('Error uploading document:', error);
        showError('上传失败：' + (error.message || '未知错误'));
      } finally {
        isUploading.value = false;
      }
    }

    const cancelUpload = () => {
      selectedFile.value = null
      showUploadDialog.value = false
    }

    // 文档管理相关方法
    const loadDocuments = async (kb) => {
      try {
        const response = await api.get(`/api/knowledge-base/${kb.id}/documents`)
        const data = await response.json()
        documents.value = data.documents
      } catch (error) {
        console.error('Error loading documents:', error)
      }
    }

    const viewDocuments = async (kb) => {
      currentKnowledgeBase.value = kb
      await loadDocuments(kb)
      showDocumentsDialog.value = true
    }

    const deleteDocument = async (doc) => {
      if (!confirm(`确定要删除文档 "${doc.name}" 吗？`)) return

      try {
        await api.delete(
          `/api/knowledge-base/${currentKnowledgeBase.value.id}/documents/${doc.id}`
        )
        await loadDocuments(currentKnowledgeBase.value)
      } catch (error) {
        console.error('Error deleting document:', error)
      }
    }

    const formatDate = (dateStr) => {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    }

    // 查看文档内容
    const viewDocument = async (doc) => {
      try {
        const response = await api.get(
          `/api/knowledge-base/${currentKnowledgeBase.value.id}/documents/${doc.id}`
        )
        
        if (response.ok) {
          const data = await response.json()
          currentDocument.value = {
            ...doc,
            content: data.content
          }
          documentContent.value = data.content
          showDocumentViewDialog.value = true
        }
      } catch (error) {
      console.error('Error viewing document:', error)
      }
    }

    // 关闭文档查看对话框
    const closeDocumentView = () => {
      showDocumentViewDialog.value = false
      currentDocument.value = null
      documentContent.value = ''
    }

    const goBack = () => {
      router.push('/')
    }

    // 添加错误和成功提示方法
    const showError = (message) => {
      alert(message); // 可以替换为更好的提示UI
    }

    const showSuccess = (message) => {
      alert(message); // 可以替换为更好的提示UI
    }

    return {
      fileInput,
      authStore,
      knowledgeBases,
      newKnowledgeBase,
      currentKnowledgeBase,
      showUploadDialog,
      showDocumentsDialog,
      selectedFile,
      documents,
      isUploading,
      showDocumentViewDialog,
      currentDocument,
      documentContent,
      loadKnowledgeBases,
      addKnowledgeBase,
      editKnowledgeBase,
      deleteKnowledgeBase,
      uploadDocument,
      viewDocuments,
      triggerFileInput,
      handleFileUpload,
      submitUpload,
      cancelUpload,
      loadDocuments,
      deleteDocument,
      formatDate,
      viewDocument,
      closeDocumentView,
      goBack,
      showError,
      showSuccess
    }
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
  width: 30%;
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

/* 添加无权限提示的样式 */
.no-permission {
  text-align: center;
  padding: 40px;
  margin: 20px;
  background-color: #f9fafb;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.no-permission h2 {
  color: #374151;
  margin-bottom: 16px;
}

.no-permission p {
  color: #6b7280;
}

/* 添加移动端适配样式 */
@media (max-width: 730px) {
  .knowledge-page {
    padding: 1rem;
  }

  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .header h1 {
    font-size: 1.5rem;
    margin: 0;
  }

  .back-btn {
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
  }

  .section {
    margin-bottom: 1.5rem;
  }

  .section h2 {
    font-size: 1.2rem;
    margin-bottom: 1rem;
  }

  .add-knowledge {
    flex-direction: column;
    gap: 0.8rem;
  }

  .add-knowledge input {
    width: 100%;
    padding: 0.8rem;
    font-size: 1rem;
  }

  .add-knowledge button {
    width: 100%;
    padding: 0.8rem;
    font-size: 1rem;
  }

  .knowledge-list {
    gap: 1rem;
  }

  .knowledge-item {
    padding: 1rem;
    flex-direction: column;
    gap: 1rem;
  }

  .kb-info {
    width: 100%;
  }

  .kb-info h3 {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
  }

  .kb-info p {
    font-size: 0.9rem;
  }

  .kb-actions {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
  }

  .action-btn {
    width: 100%;
    padding: 0.6rem;
    font-size: 0.9rem;
  }

  /* 对话框适配 */
  .dialog {
    width: 90%;
    margin: 1rem;
    padding: 1rem;
  }

  .dialog h2 {
    font-size: 1.2rem;
  }

  .upload-area {
    padding: 1.5rem;
  }

  .upload-icon {
    font-size: 2rem;
  }

  .upload-text {
    font-size: 0.9rem;
  }

  .upload-hint {
    font-size: 0.8rem;
  }

  .dialog-actions {
    flex-direction: column;
    gap: 0.8rem;
  }

  .dialog-actions button {
    width: 100%;
    padding: 0.8rem;
    font-size: 1rem;
  }

  /* 文档列表对话框适配 */
  .documents-dialog {
    width: 50%;
    max-height: 90vh;
  }

  .documents-list {
    max-height: calc(90vh - 120px);
  }

  .document-item {
    padding: 0.8rem;
    flex-direction: column;
    gap: 0.8rem;
  }

  .doc-info {
    width: 100%;
  }

  .doc-actions {
    width: 100%;
    justify-content: flex-start;
    gap: 0.5rem;
  }

  .doc-btn {
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
  }

  .document-view-dialog {
    width: 30%;
    height: 100vh;
    max-width: 100%;
    margin: 0;
    border-radius: 0;
    position: fixed;
    top: 0;
    left: 0;
  }

  .document-content {
    padding: 16px;
    margin-top: 12px;
    font-size: 16px;
    line-height: 1.5;
    -webkit-overflow-scrolling: touch;
  }

  .dialog-header {
    padding: 16px;
    position: sticky;
    top: 0;
    background: #ffffff;
    z-index: 10;
  }

  .dialog-header h2 {
    font-size: 16px;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .close-btn {
    padding: 8px;
    margin: -8px;
  }
}

/* 超小屏幕优化 */
@media (max-width: 340px) {
  .kb-actions {
    grid-template-columns: 1fr;
  }

  .action-btn {
    padding: 0.8rem;
    font-size: 1rem;
  }

  .doc-actions {
    flex-direction: column;
  }

  .doc-btn {
    width: 100%;
  }

  .dialog {
    padding: 0.8rem;
  }

  .document-content {
    padding: 12px;
    font-size: 15px;
  }

  .dialog-header {
    padding: 12px;
  }

  .dialog-header h2 {
    font-size: 15px;
  }
}

/* 暗色模式支持 */
@media (prefers-color-scheme: dark) {
  .knowledge-page {
    background: #1f2937;
  }

  .header {
    background: #1f2937;
  }

  .knowledge-item {
    background: #374151;
    border-color: #4b5563;
  }

  .action-btn {
    background: #4b5563;
    color: #e5e7eb;
  }

  .dialog {
    background: #1f2937;
  }

  input {
    background: #374151;
    border-color: #4b5563;
    color: #e5e7eb;
  }

  .document-item {
    background: #374151;
    border-color: #4b5563;
  }

  .document-view-dialog {
    background: #1f2937;
  }

  .document-content {
    background: #374151;
    border-color: #4b5563;
    color: #e5e7eb;
  }

  .dialog-header {
    background: #1f2937;
    border-bottom-color: #4b5563;
  }

  .dialog-header h2 {
    color: #e5e7eb;
  }

  .close-btn {
    color: #9ca3af;
  }

  .close-btn:hover {
    color: #e5e7eb;
  }
}

/* 修改文档查看对话框的移动端适配样式 */
@media (max-width: 730px) {
  .document-view-dialog {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
    margin: 0;
    padding: 0;
    border-radius: 0;
    position: fixed;
    top: 0;
    left: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .dialog-header {
    padding: 8px 12px;
    background: #ffffff;
    border-bottom: 1px solid #e5e7eb;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .dialog-header h2 {
    font-size: 14px;
    margin: 0;
    padding-right: 32px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .close-btn {
    position: absolute;
    right: 8px;
    top: 8px;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    padding: 0;
    margin: 0;
    background: none;
    border: none;
    color: #666;
  }

  .document-content {
    flex: 1;
    height: calc(100% - 40px);
    padding: 12px;
    margin: 0;
    font-size: 14px;
    line-height: 1.4;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    background: #fff;
  }
}

/* 超小屏幕优化 (340px) */
@media (max-width: 340px) {
  .document-view-dialog {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    height: 100%;
  }

  .dialog-header {
    height: 36px;
    padding: 6px 10px;
  }

  .dialog-header h2 {
    font-size: 13px;
    padding-right: 28px;
  }

  .close-btn {
    right: 6px;
    top: 6px;
    width: 22px;
    height: 22px;
    font-size: 16px;
  }

  .document-content {
    height: calc(100% - 36px);
    padding: 10px;
    font-size: 13px;
  }
}

/* 确保对话框遮罩层正确显示 */
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
  z-index: 999;
}

/* 专门针对 340*730 移动端的适配 */
@media screen and (max-width: 340px) and (max-height: 730px) {
  /* 文档查看对话框适配 */
  .document-view-dialog {
    width: 340px;
    height: 730px;
    position: fixed;
    top: 0;
    left: 0;
    margin: 0;
    padding: 0;
    border-radius: 0;
    display: flex;
    flex-direction: column;
  }

  /* 对话框头部 */
  .dialog-header {
    height: 40px;
    min-height: 40px;
    padding: 8px;
    border-bottom: 1px solid #e5e7eb;
    position: relative;
    display: flex;
    align-items: center;
  }

  .dialog-header h2 {
    font-size: 14px;
    margin: 0;
    padding-right: 30px;
    width: calc(100% - 40px);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* 关闭按钮 */
  .close-btn {
    position: fixed;
    right: 4px;
    top: 30px;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
    z-index: 2;
    /* 添加圆形边框和背景 */
    border-radius: 50%;
    background-color: rgba(255, 255, 255, 0.9);
    border: 2px solid #17200f;
    /* 优化点击效果 */
    transition: all 0.2s ease;
  }

  /* 添加悬停效果 */
  .close-btn:hover {
    background-color: rgba(255, 255, 255, 1);
    transform: scale(1.05);
  }


  /* 文档内容区域 */
  .document-content {
    flex: 1;
    height: calc(700px - 40px);
    padding: 14px;
    margin: 0;
    overflow-y: auto;
    font-size: 9px;
    line-height: 1.4;
    -webkit-overflow-scrolling: touch;
  }
}
</style> 