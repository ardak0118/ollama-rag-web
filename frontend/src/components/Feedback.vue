<template>
  <div class="feedback-container mobile-adaptive">
    <!-- 反馈按钮 -->
    <button class="feedback-button" @click.stop="openFeedbackModal">
      <span class="icon">💡</span>
      反馈建议
    </button>

    <!-- 反馈模态框 -->
    <div v-if="showFeedbackModal" 
         :class="['modal-overlay', { 'active': showFeedbackModal }]" 
         @click.self="closeFeedbackModal">
      <div class="feedback-modal" :class="{ 'active': showFeedbackModal }">
        <div class="modal-header">
          <h2>反馈建议</h2>
          <button class="close-btn" @click.stop="closeFeedbackModal">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label>反馈类型</label>
            <select v-model="feedback.type">
              <option value="bug">问题反馈</option>
              <option value="feature">功能建议</option>
              <option value="kb">知识库反馈</option>
              <option value="other">其他</option>
            </select>
          </div>
          
          <div class="form-group" v-if="feedback.type === 'kb'">
            <label>选择知识库</label>
            <select v-model="feedback.kb_id">
              <option value="">请选择知识库</option>
              <option v-for="kb in knowledgeBases" 
                      :key="kb.id" 
                      :value="kb.id">
                {{ kb.name }}
              </option>
            </select>

            <!-- 添加文件上传部分 -->
            <div class="file-upload">
              <label>上传相关文档（可选）</label>
              <div class="upload-box" @click="triggerFileInput">
                <input 
                  type="file"
                  ref="fileInput"
                  @change="handleFileSelect"
                  style="display: none"
                  accept=".txt,.pdf,.doc,.docx"
                >
                <div class="upload-area">
                  <i class="fas fa-cloud-upload-alt"></i>
                  <span>点击或拖拽文件上传</span>
                  <small>支持 .txt, .pdf, .doc, .docx 格式</small>
                </div>
              </div>
              <div v-if="selectedFile" class="selected-file">
                <span>{{ selectedFile.name }}</span>
                <button @click.stop="removeFile" class="remove-file">×</button>
              </div>
            </div>
          </div>
          
          <div class="form-group">
            <label>反馈内容</label>
            <textarea 
              v-model="feedback.content"
              :placeholder="getContentPlaceholder"
              rows="5"
            ></textarea>
          </div>

          <div class="form-group">
            <label>联系方式（选填）</label>
            <input 
              type="text"
              v-model="feedback.contact"
              placeholder="邮箱或其他联系方式"
            >
          </div>
        </div>

        <div class="modal-footer">
          <button 
            class="submit-btn" 
            @click.stop="submitFeedback"
            :disabled="!feedback.content || isSubmitting"
          >
            {{ isSubmitting ? '提交中...' : '提交反馈' }}
          </button>
          <button class="cancel-btn" @click.stop="closeFeedbackModal">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../utils/api'

export default {
  name: 'Feedback',
  setup() {
    const showFeedbackModal = ref(false)
    const isSubmitting = ref(false)
    const knowledgeBases = ref([])
    const fileInput = ref(null)
    const selectedFile = ref(null)
    
    const feedback = reactive({
      type: 'bug',
      content: '',
      contact: '',
      kb_id: ''
    })

    const getContentPlaceholder = computed(() => {
      const placeholders = {
        'bug': '请详细描述您遇到的问题...',
        'feature': '请描述您希望添加的功能...',
        'kb': '请描述知识库中的问题（如错误信息、不准确内容等）...',
        'other': '请输入您的反馈内容...'
      }
      return placeholders[feedback.type] || '请输入反馈内容...'
    })

    const triggerFileInput = () => {
      fileInput.value?.click()
    }

    const handleFileSelect = (event) => {
      const file = event.target.files[0]
      if (file) {
        // 检查文件类型
        const allowedTypes = ['.txt', '.pdf', '.doc', '.docx']
        const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
        
        if (!allowedTypes.includes(fileExt)) {
          alert('不支持的文件类型。请上传 txt, pdf, doc 或 docx 格式的文件。')
          return
        }
        
        selectedFile.value = file
      }
    }

    const removeFile = () => {
      selectedFile.value = null
      if (fileInput.value) {
        fileInput.value.value = ''
      }
    }

    const submitFeedback = async () => {
      if (!feedback.content) return
      if (feedback.type === 'kb' && !feedback.kb_id) {
        alert('请选择知识库')
        return
      }
      
      isSubmitting.value = true
      try {
        const formData = new FormData()
        formData.append('type', feedback.type)
        formData.append('content', feedback.content)
        formData.append('contact', feedback.contact || '')
        
        if (feedback.type === 'kb') {
          formData.append('kb_id', feedback.kb_id)
          const selectedKb = knowledgeBases.value.find(kb => kb.id === feedback.kb_id)
          if (selectedKb) {
            formData.append('kb_name', selectedKb.name)
          }
          
          // 添加文件
          if (selectedFile.value) {
            formData.append('file', selectedFile.value)
          }
        }

        const response = await api.post('/api/feedback', formData)
        
        if (response.ok) {
          alert('感谢您的反馈！')
          closeFeedbackModal()
        } else {
          throw new Error('提交失败')
        }
      } catch (error) {
        console.error('Error submitting feedback:', error)
        alert('提交失败，请稍后重试')
      } finally {
        isSubmitting.value = false
      }
    }

    const loadKnowledgeBases = async () => {
      try {
        const response = await api.get('/api/knowledge-base')
        if (response.ok) {
          const data = await response.json()
          knowledgeBases.value = data.knowledge_bases
        }
      } catch (error) {
        console.error('Error loading knowledge bases:', error)
      }
    }

    const openFeedbackModal = () => {
      showFeedbackModal.value = true
    }

    const closeFeedbackModal = () => {
      showFeedbackModal.value = false
      feedback.content = ''
      feedback.contact = ''
      feedback.kb_id = ''
      feedback.type = 'bug'
    }

    onMounted(() => {
      loadKnowledgeBases()
    })

    return {
      showFeedbackModal,
      feedback,
      isSubmitting,
      knowledgeBases,
      fileInput,
      selectedFile,
      getContentPlaceholder,
      triggerFileInput,
      handleFileSelect,
      removeFile,
      submitFeedback,
      openFeedbackModal,
      closeFeedbackModal
    }
  }
}
</script>

<style scoped>
.feedback-button {
  position: fixed;
  right: 20px;
  bottom: 20px;
  display: flex;
  align-items: center;
  padding: 12px 20px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.2s ease;
}

.feedback-button:hover {
  background-color: #2563eb;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.feedback-button .icon {
  margin-right: 8px;
  font-size: 16px;
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

.feedback-modal {
  background: white;
  width: 90%;
  max-width: 500px;
  border-radius: 12px;
  padding: 24px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1e293b;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #9ca3af;
  cursor: pointer;
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

.form-group select,
.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
}

.form-group textarea {
  resize: vertical;
  min-height: 100px;
}

.form-group select:focus,
.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.submit-btn,
.cancel-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-btn {
  background-color: #3b82f6;
  color: white;
}

.submit-btn:hover:not(:disabled) {
  background-color: #2563eb;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cancel-btn {
  background-color: #f3f4f6;
  color: #4b5563;
}

.cancel-btn:hover {
  background-color: #e5e7eb;
}

.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  margin-bottom: 8px;
}

.form-group select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* 添加移动端适配样式 */
@media (max-width: 768px) {
  .feedback-button {
    position: fixed;
    right: 16px;
    bottom: 80px; /* 避免与底部输入框重叠 */
    padding: 8px 16px;
    font-size: 14px;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    z-index: 900;
  }

  .feedback-button .icon {
    font-size: 16px;
    margin-right: 4px;
  }

  .modal-overlay {
    align-items: flex-end;
  }

  .feedback-modal {
    width: 100%;
    max-width: none;
    margin: 0;
    border-radius: 20px 20px 0 0;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    transform: translateY(100%);
    transition: transform 0.3s ease;
  }

  .feedback-modal.active {
    transform: translateY(0);
  }

  .modal-header {
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
  }

  .modal-header h2 {
    font-size: 18px;
    margin: 0;
  }

  .close-btn {
    padding: 8px;
    font-size: 20px;
  }

  .modal-body {
    padding: 16px;
    flex: 1;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }

  .form-group {
    margin-bottom: 16px;
  }

  .form-group label {
    font-size: 14px;
    margin-bottom: 6px;
  }

  .form-group select,
  .form-group input {
    height: 40px;
    font-size: 16px;
    padding: 8px 12px;
  }

  .form-group textarea {
    font-size: 16px;
    padding: 12px;
    min-height: 100px;
  }

  .modal-footer {
    padding: 16px;
    border-top: 1px solid #e5e7eb;
    flex-direction: column;
    gap: 8px;
  }

  .submit-btn,
  .cancel-btn {
    width: 100%;
    height: 44px;
    font-size: 16px;
  }

  /* 暗色模式支持 */
  @media (prefers-color-scheme: dark) {
    .feedback-modal {
      background-color: #1f2937;
    }

    .modal-header,
    .modal-footer {
      border-color: #374151;
    }

    .form-group label {
      color: #e5e7eb;
    }

    .form-group select,
    .form-group input,
    .form-group textarea {
      background-color: #374151;
      border-color: #4b5563;
      color: #e5e7eb;
    }

    .close-btn {
      color: #e5e7eb;
    }
  }

  /* 添加动画效果 */
  .feedback-modal {
    animation: none;
  }

  /* 简化动画效果 */
  .modal-overlay {
    transition: background-color 0.3s ease;
  }

  .feedback-modal {
    transition: transform 0.3s ease;
  }
}

/* 添加文件上传相关样式 */
.file-upload {
  margin-top: 1rem;
}

.upload-box {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-box:hover {
  border-color: #4CAF50;
  background-color: #f8f9fa;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.upload-area i {
  font-size: 2rem;
  color: #6c757d;
}

.upload-area small {
  color: #6c757d;
}

.selected-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1rem;
  padding: 0.5rem;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.remove-file {
  background: none;
  border: none;
  color: #dc3545;
  cursor: pointer;
  font-size: 1.2rem;
  padding: 0 0.5rem;
}

.remove-file:hover {
  color: #c82333;
}
</style> 