<template>
  <div class="chat-container">
    <div class="model-selector">
      <div class="model-label">选择模型:</div>
      <select v-model="selectedModel" :disabled="isLoading || isLoadingModels">
        <option v-if="isLoadingModels" value="">加载模型列表中...</option>
        <option v-else-if="models.length === 0" value="">无可用模型</option>
        <option v-for="model in models" 
                :key="model.name" 
                :value="model.name">
          {{ formatModelName(model.name) }} ({{ formatSize(model.size) }})
        </option>
      </select>
    </div>
    <div class="messages" ref="messagesContainer">
      <div v-for="(message, index) in messages" 
           :key="index" 
           :class="['message-wrapper', message.role]">
        <div class="message-container">
          <div class="message-header">
            <span class="role-badge">{{ message.role === 'user' ? '我' : 'AI' }}</span>
            <span class="message-time">{{ formatTime(message.timestamp) }}</span>
          </div>
          <div class="message-content">
            {{ message.content }}
            <div v-if="message.sources && message.sources.length > 0" class="sources">
              <div class="sources-title">
                <i class="fas fa-book"></i> 参考来源：
              </div>
              <div v-for="(source, idx) in message.sources" 
                   :key="idx" 
                   class="source-item">
                <div class="source-header" @click="toggleSource(idx)">
                  <i :class="['fas', sourceExpanded[idx] ? 'fa-chevron-down' : 'fa-chevron-right']"></i>
                  <span class="source-filename">{{ source.filename }}</span>
                  <span class="file-type-badge">{{ source.file_type }}</span>
                </div>
                <div v-if="sourceExpanded[idx]" class="source-content">
                  {{ source.content }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="isLoading" class="message-wrapper assistant">
        <div class="message-container">
          <div class="message-header">
            <span class="role-badge">AI</span>
          </div>
          <div class="message-content loading">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="input-area">
      <div class="input-wrapper">
        <textarea 
          v-model="newMessage" 
          @keydown.enter.exact.prevent="sendMessage"
          @keydown.shift.enter.prevent="newMessage += '\n'"
          :disabled="isLoading"
          placeholder="请输入你的问题..."
          rows="1"
          ref="messageInput"
          @input="adjustTextareaHeight"
        ></textarea>
        <div class="button-group">
          <button 
            class="send-button"
            @click="sendMessage" 
            :disabled="isLoading || !newMessage.trim()"
            :title="isLoading ? '发送中...' : '发送'"
          >
            <i class="fas fa-paper-plane"></i>
            <span class="send-text">发送</span>
          </button>
        </div>
      </div>
      <div class="input-tips">
        <span class="shortcut-tip">Enter 发送 | Shift + Enter 换行</span>
        <span class="char-count" :class="{ 'near-limit': newMessage.length > 800 }">
          {{ newMessage.length }}/1000
        </span>
      </div>
    </div>
    <button @click="goToKnowledgeBase">管理知识库</button>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { api } from '../utils/api'

export default {
  name: 'RAGChat',
  props: {
    knowledgeBaseId: {
      type: Number,
      required: true
    },
    currentChatId: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      messages: [],
      newMessage: '',
      isLoading: false,
      chatId: null,
      error: null,
      selectedModel: 'qwen2.5:latest',
      models: [],
      isLoadingModels: false,
      sourceExpanded: reactive({})  // 使用 reactive 创建响应式对象
    }
  },
  methods: {
    formatModelName(name) {
      // 格式化模型名称显示
      const parts = name.split(':')
      const modelName = parts[0]
      const version = parts[1] || 'latest'
      
      // 首字母大写
      return modelName.charAt(0).toUpperCase() + modelName.slice(1) + ' ' + version
    },
    formatSize(size) {
      // 格式化模型大小
      if (!size) return ''
      const gb = size / (1024 * 1024 * 1024)
      return gb.toFixed(1) + 'GB'
    },
    async loadModels() {
      try {
        // 使用后端代理接口
        const response = await fetch('http://localhost:8000/api/proxy/models');
        if (response.ok) {
          const data = await response.json();
          if (data.models) {
            this.models = data.models;
            if (!this.models.includes(this.selectedModel)) {
              this.selectedModel = this.models[0];
            }
          }
        }
      } catch (error) {
        console.error('Error loading models:', error);
        // 设置默认模型
        this.models = ['qwen2.5:latest'];
        this.selectedModel = 'qwen2.5:latest';
      }
    },
    async sendMessage() {
      if (!this.newMessage.trim() || this.isLoading) return;
      
      if (!this.knowledgeBaseId) {
        this.error = '请先选择知识库';
        this.messages.push({
          content: this.error,
          role: 'error'
        });
        return;
      }

      const userMessage = this.newMessage.trim();
      this.messages.push({
        content: userMessage,
        role: 'user'
      });
      this.newMessage = '';
      this.isLoading = true;
      this.error = null;

      try {
        const response = await api.post('/api/rag/chat', {
          message: userMessage,
          kb_id: this.knowledgeBaseId,
          model: this.selectedModel,
          conversation_id: this.chatId
        });

        if (!response.ok) {
          throw new Error('HTTP error! status: ' + response.status);
        }

        const data = await response.json();
        
        if (!this.chatId && data.conversation_id) {
          this.chatId = data.conversation_id;
          this.$emit('chat-created', this.chatId);
        }

        this.messages.push({
          content: data.response,
          role: 'assistant',
          sources: data.sources || []
        });

        this.$nextTick(() => {
          this.scrollToBottom();
        });
      } catch (error) {
        console.error('Error:', error);
        this.error = '发送消息失败，请重试';
        this.messages.push({
          content: this.error,
          role: 'error'
        });
      } finally {
        this.isLoading = false;
      }
    },
    async loadChatHistory(chatId) {
      if (!chatId) {
        console.warn('No chat ID provided');
        return;
      }

      try {
        const response = await api.get(`/api/rag/chat/messages/${chatId}`);
        if (response.ok) {
          const data = await response.json();
          this.messages = data.messages || [];
          this.$nextTick(() => {
            this.scrollToBottom();
          });
        }
      } catch (error) {
        console.error('Error loading chat history:', error);
      }
    },
    scrollToBottom() {
      const container = this.$refs.messagesContainer
      container.scrollTop = container.scrollHeight
    },
    formatTime(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit'
      });
    },
    adjustTextareaHeight() {
      const textarea = this.$refs.messageInput;
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    },
    toggleSource(idx) {
      // 直接修改响应式对象
      this.sourceExpanded[idx] = !this.sourceExpanded[idx]
    },
    goToKnowledgeBase() {
      this.$router.push({
        path: '/',
        query: { from: 'chat' }
      })
    }
  },
  async created() {
    // 组件创建时加载模型列表
    await this.loadModels()
  },
  watch: {
    knowledgeBaseId: {
      immediate: true,
      handler(newId) {
        console.log('Knowledge base ID changed:', newId);
      }
    },
    currentChatId: {
      immediate: true,
      handler(newId) {
        if (newId) {
          this.chatId = newId;
          this.loadChatHistory(newId);
        } else {
          this.chatId = null;
          this.messages = [];
        }
      }
    },
    selectedModel(newModel) {
      // 当选择新模型时，可以在这里添加一些处理逻辑
      console.log('Selected model changed to:', newModel)
    }
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #f8f9fa;
}

.model-selector {
  display: flex;
  align-items: center;
  padding: 1rem;
  background-color: white;
  border-bottom: 1px solid #e9ecef;
}

.model-label {
  font-weight: 500;
  margin-right: 1rem;
  color: #495057;
}

.model-selector select {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background-color: white;
  font-size: 0.9rem;
  color: #495057;
  cursor: pointer;
  transition: border-color 0.15s ease-in-out;
}

.model-selector select:hover {
  border-color: #adb5bd;
}

.model-selector select:focus {
  border-color: #80bdff;
  outline: 0;
  box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message-wrapper {
  display: flex;
  margin-bottom: 1rem;
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-container {
  max-width: 80%;
  display: flex;
  flex-direction: column;
}

.message-header {
  display: flex;
  align-items: center;
  margin-bottom: 0.25rem;
  gap: 0.5rem;
}

.role-badge {
  font-size: 0.8rem;
  font-weight: 500;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  background-color: #e9ecef;
  color: #495057;
}

.user .role-badge {
  background-color: #007bff;
  color: white;
}

.assistant .role-badge {
  background-color: #28a745;
  color: white;
}

.message-time {
  font-size: 0.8rem;
  color: #6c757d;
}

.message-content {
  padding: 1rem;
  border-radius: 12px;
  background-color: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  line-height: 1.5;
}

.user .message-content {
  background-color: #007bff;
  color: white;
}

.assistant .message-content {
  background-color: white;
  color: #212529;
}

.sources {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e9ecef;
}

.sources-title {
  font-weight: 500;
  color: #6c757d;
  margin-bottom: 0.5rem;
}

.source-item {
  margin: 0.5rem 0;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  overflow: hidden;
}

.source-header {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  background-color: #f8f9fa;
  cursor: pointer;
  transition: background-color 0.2s;
}

.source-header:hover {
  background-color: #e9ecef;
}

.source-header i {
  margin-right: 0.5rem;
  font-size: 0.8rem;
  color: #6c757d;
  transition: transform 0.2s;
}

.source-filename {
  flex: 1;
  font-weight: 500;
  color: #495057;
}

.file-type-badge {
  padding: 0.2rem 0.5rem;
  background-color: #e9ecef;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #6c757d;
}

.source-content {
  padding: 1rem;
  background-color: white;
  border-top: 1px solid #e9ecef;
  font-size: 0.9rem;
  line-height: 1.5;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.input-area {
  padding: 0.75rem;
  background-color: white;
  border-top: 1px solid #e9ecef;
}

.input-wrapper {
  display: flex;
  gap: 0.5rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 0.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  position: relative;
}

textarea {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  resize: none;
  min-height: 20px;
  max-height: 120px;
  line-height: 1.5;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  background-color: white;
}

textarea:focus {
  outline: none;
  border-color: #80bdff;
  box-shadow: 0 0 0 0.2rem rgba(0,123,255,0.15);
}

textarea:disabled {
  background-color: #e9ecef;
  cursor: not-allowed;
}

.button-group {
  display: flex;
  align-items: flex-end;
}

.send-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  height: 36px;
  padding: 0 1rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9rem;
}

.send-button i {
  font-size: 0.9rem;
}

.send-text {
  display: inline-block;
  font-size: 0.9rem;
  margin-left: 0.25rem;
}

.send-button:hover:not(:disabled) {
  background-color: #0056b3;
  transform: translateY(-1px);
}

.send-button:active:not(:disabled) {
  transform: translateY(1px);
}

.send-button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
  opacity: 0.7;
}

.input-tips {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: #6c757d;
}

.shortcut-tip {
  color: #6c757d;
}

.char-count {
  color: #6c757d;
  transition: color 0.3s ease;
}

.char-count.near-limit {
  color: #dc3545;
  font-weight: 500;
}

/* 添加暗色主题支持 */
@media (prefers-color-scheme: dark) {
  .input-wrapper {
    background-color: #2d3238;
  }
  
  textarea {
    background-color: #1e2124;
    border-color: #40464e;
    color: #e9ecef;
  }
  
  textarea:focus {
    border-color: #0d6efd;
    box-shadow: 0 0 0 0.2rem rgba(13,110,253,0.25);
  }
  
  .input-tips {
    color: #adb5bd;
  }
  
  .send-button {
    background-color: #0d6efd;
  }
  
  .send-button:hover:not(:disabled) {
    background-color: #0b5ed7;
  }
}
</style> 