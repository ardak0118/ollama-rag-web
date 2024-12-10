<template>
  <div class="app-layout">
    <!-- 左侧对话历史 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <button class="new-chat-btn" @click="startNewConversation">
          <span>+ 新对话</span>
        </button>
      </div>
      
      <div class="sidebar-content">
        <div class="chat-history">
          <div v-for="conv in allConversations" 
               :key="conv.id"
               :class="['chat-item', { active: currentConversationId === conv.id }]"
               @click="loadConversation(conv)">
            <div class="chat-info">
              <div class="chat-title" :title="conv.title">
                {{ conv.title || '新对话' }}
              </div>
              <div class="chat-type-badge" :class="conv.type">
                {{ conv.type === 'rag' ? '知识库对话' : '普通对话' }}
              </div>
            </div>
            <button class="delete-btn" @click.stop="deleteConversation(conv)">×</button>
          </div>
        </div>
      </div>
    </div>

    <div class="main-content">
      <!-- 顶部 -->
      <div class="top-bar">
        <div class="chat-settings">
          <div class="settings-row">
            <div class="model-selector">
              <label>对话模型：</label>
              <select v-model="selectedModel" :disabled="isLoading">
                <option v-for="model in availableModels" 
                        :key="model" 
                        :value="model">
                  {{ formatModelName(model) }}
                </option>
              </select>
            </div>
            
            <div class="kb-selector">
              <label>知识库：</label>
              <select v-model="selectedKnowledgeBase" :disabled="isLoading">
                <option value="">不使用知识库</option>
                <option v-for="kb in knowledgeBases" 
                        :key="kb.id" 
                        :value="kb.id">
                  {{ kb.name }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- 聊天消息区域 -->
      <div class="chat-messages" ref="messagesContainer">
        <div v-for="(message, index) in messages" 
             :key="index" 
             :class="['message', message.role]">
          <div class="message-header">
            <div class="avatar" :class="message.role">
              {{ message.role === 'user' ? '我' : 'AI' }}
            </div>
            <div class="role-name">{{ message.role === 'user' ? '' : selectedModel }}</div>
            <div v-if="message.timestamp" class="message-time">
              {{ formatTime(message.timestamp) }}
            </div>
          </div>
          <div class="message-content" v-html="formatMessage(message.content)"></div>
          <div v-if="message.confidence" class="message-confidence" :class="message.confidence">
            置信度：{{ message.confidence }}
          </div>
          <div v-if="message.sources && message.sources.length > 0" class="message-sources">
            <div class="sources-title">参考来源：</div>
            <div v-for="(source, idx) in message.sources" 
                 :key="idx" 
                 class="source-item"
                 @click="toggleSource(idx)">
              <div class="source-header">
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

      <!-- 部输入区域 -->
      <div class="input-area">
        <div class="input-container">
          <textarea 
            v-model="userInput" 
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.shift.enter.prevent="userInput += '\n'"
            :disabled="isLoading"
            placeholder="请输入你的问题...."
            rows="1"
            ref="messageInput"
            @input="adjustTextareaHeight"
          ></textarea>
          <button 
            class="send-button"
            :class="{ 'can-send': userInput.trim() }"
            @click="sendMessage"
            :disabled="isLoading || !userInput.trim()"
          >
            <i class="fas fa-paper-plane"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { api } from '../utils/api'
import { ref, reactive } from 'vue'

export default {
  name: 'ChatWindow',
  data() {
    return {
      messages: [],
      userInput: '',
      isLoading: false,
      availableModels: ['qwen2.5:latest'],
      selectedModel: 'qwen2.5:latest',
      currentConversationId: null,
      knowledgeBases: [],
      selectedKnowledgeBase: '',
      allConversations: [],
      sourceExpanded: reactive({}),
      error: null,
      lastMessageTime: null
    }
  },
  computed: {
    // 当前对话类型
    currentChatType() {
      return this.selectedKnowledgeBase ? 'rag' : 'normal'
    },

    // 是否可以发送消息
    canSendMessage() {
      return !this.isLoading && this.userInput.trim().length > 0
    },

    // 当前选中的知识库名称
    selectedKnowledgeBaseName() {
      const kb = this.knowledgeBases.find(kb => kb.id === this.selectedKnowledgeBase)
      return kb ? kb.name : ''
    }
  },
  methods: {
    async loadAllConversations() {
      try {
        const response = await api.get('/api/conversations')
        const data = await response.json()
        this.allConversations = data.conversations.map(conv => ({
          id: conv.id,
          title: conv.title,
          type: conv.type,
          kb_id: conv.kb_id,
          timestamp: conv.timestamp
        }))
      } catch (error) {
        console.error('Error loading conversations:', error)
      }
    },

    async loadConversation(conv) {
      try {
        const response = await api.get(`/api/conversations/${conv.id}`)
        const data = await response.json()
        this.messages = data.messages
        this.currentConversationId = conv.id
        this.selectedKnowledgeBase = conv.kb_id || ''
        this.scrollToBottom()
      } catch (error) {
        console.error('Error loading conversation:', error)
      }
    },

    async deleteConversation(conv) {
      if (!confirm('确定要删除这个对话吗？')) return
      
      try {
        await api.delete(`/api/conversations/${conv.id}`)
        await this.loadAllConversations()
        if (this.currentConversationId === conv.id) {
          this.startNewConversation()
        }
      } catch (error) {
        console.error('Error deleting conversation:', error)
      }
    },

    async sendMessage() {
      if (!this.userInput.trim() || this.isLoading) return

      try {
        this.isLoading = true
        
        // 添加用户消息到界面
        const userMessage = {
          content: this.userInput.trim(),
          role: 'user',
          timestamp: new Date().toISOString()
        }
        this.messages.push(userMessage)
        this.userInput = ''
        this.adjustTextareaHeight()

        // 发送请求
        const response = await api.post('/api/chat', {
          message: userMessage.content,
          model: this.selectedModel,
          conversation_id: this.currentConversationId,
          kb_id: this.selectedKnowledgeBase || null
        })

        const data = await response.json()

        // 检查响应状态
        if (!response.ok) {
          throw new Error(data.message || '请求失败')
        }

        // 检查响应数据
        if (!data || (!data.answer && !data.response)) {
          throw new Error('未获取到有效回答')
        }

        // 添加 AI 响应到界面
        const aiMessage = {
          content: data.answer || data.response, // 兼容两种返回格式
          role: 'assistant',
          sources: data.sources || [],
          timestamp: new Date().toISOString(),
          confidence: data.confidence || '中' // 添加置信度
        }

        // 如果有参考来源，添加到消息中
        if (data.sources && data.sources.length > 0) {
          aiMessage.sources = data.sources.map(source => ({
            content: source.content,
            filename: source.metadata?.source || '未知来源',
            file_type: source.metadata?.file_type || '文档',
            score: source.score || 0
          }))
        }

        this.messages.push(aiMessage)

        // 更新对话 ID
        if (!this.currentConversationId && data.conversation_id) {
          this.currentConversationId = data.conversation_id
          await this.loadAllConversations()
        }

      } catch (error) {
        console.error('Error sending message:', error)
        
        // 添加更具体的错误消息
        let errorMessage = '发送消息失败：'
        if (error.message.includes('未获取到有效回答')) {
          errorMessage = '抱歉，知识库中未找到相关信息。请尝试换个方式提问，或确认知识库中是否包含相关内容。'
        } else if (error.message.includes('请求失败')) {
          errorMessage = '抱歉，服务器响应错误，请稍后重试。'
        } else {
          errorMessage = `抱歉，${error.message || '发生未知错误'}，请稍后重试。`
        }
        
        // 添加错误消息到界面
        this.messages.push({
          content: errorMessage,
          role: 'error',
          timestamp: new Date().toISOString()
        })
      } finally {
        this.isLoading = false
        this.scrollToBottom()
      }
    },

    async loadModels() {
      try {
        const response = await api.get('/api/proxy/models')
        const data = await response.json()
        
        if (data.models && Array.isArray(data.models)) {
          this.availableModels = data.models
            .filter(model => model && typeof model === 'string')
            .map(String)
          
          if (!this.availableModels.includes(this.selectedModel)) {
            this.selectedModel = this.availableModels[0] || 'qwen2.5:latest'
          }
        } else {
          this.availableModels = ['qwen2.5:latest']
          this.selectedModel = 'qwen2.5:latest'
        }
        
        // 检查 Ollama 服务健康状态
        const healthResponse = await api.get('/api/proxy/health')
        const healthData = await healthResponse.json()
        if (healthData.status !== 'healthy') {
          console.warn('Ollama service health check failed:', healthData.message)
        }
        
      } catch (error) {
        console.error('Error loading models:', error)
        // 错时使用默认值
        this.availableModels = ['qwen2.5:latest']
        this.selectedModel = 'qwen2.5:latest'
      }
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

    scrollToBottom() {
      this.$nextTick(() => {
        if (this.$refs.messagesContainer) {
          this.$refs.messagesContainer.scrollTop = this.$refs.messagesContainer.scrollHeight
        }
      })
    },
    navigateToKnowledgeBase() {
      this.$router.push('/knowledge-base')
    },
    triggerFileUpload() {
      this.$refs.fileInput.click()
    },
    
    async handleFileUpload(event) {
      const file = event.target.files[0]
      if (!file) return
      
      try {
        this.isLoading = true
        const formData = new FormData()
        formData.append('file', file)
        
        const response = await fetch('http://localhost:8000/api/chat/upload', {
          method: 'POST',
          body: formData
        })
        
        if (!response.ok) {
          throw new Error('文件上传失败')
        }
        
        const data = await response.json()
        
        // 构建引用格式的消息
        const fileReference = `[${file.name}]`
        this.userInput = `请分析这个文件的内容：${fileReference}`
        await this.sendMessage()
        
        // 添加文件内容到消息中，但不显示
        this.messages[this.messages.length - 1].fileContent = data.content
        this.messages[this.messages.length - 1].fileName = file.name
        
      } catch (error) {
        console.error('Error handling file:', error)
        this.messages.push({
          content: `文件处理失败: ${error.message}`,
          role: 'error'
        })
      } finally {
        this.isLoading = false
        event.target.value = ''
      }
    },
    goToKnowledgeBase() {
      this.$router.push('/knowledge-base');
    },
    // 格式化模型名称显示
    formatModelName(name) {
      if (!name || typeof name !== 'string') {
        return 'Unknown Model';
      }
      try {
        const parts = name.split(':');
        const modelName = parts[0];
        const version = parts[1] || 'latest';
        return modelName.charAt(0).toUpperCase() + modelName.slice(1) + ' ' + version;
      } catch (error) {
        console.error('Error formatting model name:', error);
        return String(name);
      }
    },

    // 切换知识库引用源展开/收起
    toggleSource(idx) {
      this.sourceExpanded[idx] = !this.sourceExpanded[idx]
    },

    // 调整文本框高度
    adjustTextareaHeight() {
      const textarea = this.$refs.messageInput
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
    },

    // 格式化时间显示
    formatTime(timestamp) {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
      })
    },

    // 开始新对话
    startNewConversation() {
      this.currentConversationId = null
      this.messages = []
      // 保持当前选择的知识库状态
    },

    // 修改消息格式化方法
    formatMessage(content) {
      if (!content) return '';
      
      // 将代码块转换为 Markdown 格式
      content = content.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        const id = 'code-' + Math.random().toString(36).substr(2, 9);
        return `
          <div class="code-block-wrapper">
            <div class="code-header">
              <div class="header-left">
                <span class="code-lang">${lang}</span>
              </div>
              <button class="copy-btn" onclick="window.copyCode('${id}')">
                复制代码
              </button>
            </div>
            <pre class="code-block ${lang}" id="${id}"><code>${this.escapeHtml(code.trim())}</code></pre>
          </div>
        `;
      });
      
      // 处理 Markdown 语法
      content = content
        // 处理标题
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        
        // 处理粗体和斜体
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        
        // 处理列表
        .replace(/^\s*\d+\.\s+(.*$)/gm, '<ol><li>$1</li></ol>')
        .replace(/^\s*[-*]\s+(.*$)/gm, '<ul><li>$1</li></ul>')
        
        // 处理链接
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        
        // 处理行内代码
        .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
        
        // 处理换行
        .replace(/\n/g, '<br>');
      
      return content;
    },

    // HTML 转义
    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  },
  async created() {
    try {
      await Promise.all([
        this.loadModels(),
        this.loadKnowledgeBases(),
        this.loadAllConversations()
      ])
    } catch (error) {
      console.error('Error initializing component:', error)
    }

    // 修改复制功能的实现
    window.copyCode = async (id) => {
      const codeBlock = document.getElementById(id);
      if (!codeBlock) return;

      try {
        // 获取代码内容和语言
        const code = codeBlock.textContent;
        const lang = codeBlock.className.split(' ')
          .find(cls => cls !== 'code-block')
          ?.trim() || '';

        // 构建 Markdown 格式的代码
        const markdownCode = `\`\`\`${lang}\n${code}\n\`\`\``;
        
        // 复制到剪贴板
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(markdownCode);
        } else {
          const textArea = document.createElement('textarea');
          textArea.value = markdownCode;
          document.body.appendChild(textArea);
          textArea.select();
          try {
            document.execCommand('copy');
          } catch (err) {
            console.error('Failed to copy text:', err);
          }
          document.body.removeChild(textArea);
        }

        // 更新按钮状态
        const copyBtn = codeBlock.parentElement.querySelector('.copy-btn');
        copyBtn.textContent = '复制成功';
        setTimeout(() => {
          copyBtn.textContent = '复制代码';
        }, 2000);

      } catch (error) {
        console.error('Failed to copy code:', error);
        const copyBtn = codeBlock.parentElement.querySelector('.copy-btn');
        copyBtn.textContent = '复制失败';
        setTimeout(() => {
          copyBtn.textContent = '复制代码';
        }, 2000);
      }
    };
  },
  watch: {
    // 监听知识库选择变化
    selectedKnowledgeBase(newVal, oldVal) {
      if (newVal !== oldVal && this.currentConversationId) {
        // 切换知识库时提示用户
        if (confirm('切换知识库将开始新的对话，是否继续？')) {
          this.startNewConversation()
        } else {
          // 如果用户取消，恢复之前的择
          this.selectedKnowledgeBase = oldVal
        }
      }
    }
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background-color: #ffffff;
}

/* 侧边栏样式 */
.sidebar {
  width: 260px;
  background-color: #f9fafb;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.new-chat-btn {
  width: 100%;
  padding: 8px 16px;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  color: #374151;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  background-color: #f3f4f6;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.chat-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 8px 12px;
  margin: 4px 0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  gap: 8px;
}

.chat-item:hover {
  background-color: #f3f4f6;
}

.chat-item.active {
  background-color: #e5e7eb;
}

.chat-title {
  font-size: 14px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
  max-width: 180px;
}

.delete-btn {
  opacity: 0;
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  font-size: 16px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
  height: 24px;
  width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.chat-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background-color: #fee2e2;
  color: #dc2626;
}

/* 主内容区域样式 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  position: relative;
  padding-bottom: 100px;
}

.top-bar {
  padding: 12px 24px;
  border-bottom: 1px solid #e5e7eb;
  background-color: #ffffff;
}

.chat-settings {
  max-width: 1200px;
  margin: 0 auto;
}

.settings-row {
  display: flex;
  align-items: center;
  gap: 32px;  /* 增加选择器之间的间距 */
}

.model-selector,
.kb-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;  /* 让两个选择器平均分配空间 */
}

.model-selector label,
.kb-selector label {
  font-size: 14px;
  color: #374151;
  white-space: nowrap;  /* 防止标签换行 */
  min-width: 80px;  /* 确保标签有固定的最小宽度 */
}

.model-selector select,
.kb-selector select {
  flex: 1;  /* 让选择框占据剩余空间 */
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  color: #374151;
  background-color: #ffffff;
  cursor: pointer;
  outline: none;
  transition: all 0.2s;
}

.model-selector select:hover,
.kb-selector select:hover {
  border-color: #d1d5db;
}

.model-selector select:focus,
.kb-selector select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

/* 暗色主题支持 */
@media (prefers-color-scheme: dark) {
  .top-bar {
    background-color: #1f2937;
    border-bottom-color: #374151;
  }

  .model-selector label,
  .kb-selector label {
    color: #e5e7eb;
  }

  .model-selector select,
  .kb-selector select {
    background-color: #374151;
    border-color: #4b5563;
    color: #e5e7eb;
  }

  .model-selector select:hover,
  .kb-selector select:hover {
    border-color: #6b7280;
  }

  .model-selector select:focus,
  .kb-selector select:focus {
    border-color: #60a5fa;
    box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.1);
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  padding-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-bottom: 20px;
}

.message {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.message.user {
  align-items: flex-end;
}

.message.assistant {
  align-items: flex-start;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
}

.message.user .message-header {
  flex-direction: row-reverse;
}

.avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  border-radius: 50%;
  color: white;
  font-weight: 500;
}

.avatar.user {
  background-color: #3b82f6;  /* 用户头像蓝色 */
}

.avatar.assistant {
  background-color: #10b981;  /* AI头像绿色 */
}

.role-name {
  font-size: 14px;
  color: #6b7280;
}

.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: #1f2937;
  max-width: 80%;
}

.user .message-content {
  background-color: #10b981;
  color: white;
  border-radius: 12px 12px 0 12px;
}

.assistant .message-content {
  background-color: #f3f4f6;
  color: #1f2937;
  border-radius: 12px 12px 12px 0;
}

.input-area {
  position: fixed;
  bottom: 0;
  left: 260px;  /* 侧边栏宽度 */
  right: 0;
  padding: 20px;
  background-color: #ffffff;
  border-top: 1px solid #e5e7eb;
  z-index: 100;
}

.input-container {
  position: relative;
  max-width: 800px;
  margin: 0 auto;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  padding: 12px 50px 12px 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

textarea {
  width: 100%;
  min-height: 24px;
  max-height: 150px;
  border: none;
  background: transparent;
  resize: none;
  outline: none;
  font-size: 14px;
  line-height: 1.5;
  color: #374151;
  padding: 0;
}

textarea::placeholder {
  color: #9ca3af;
}

.send-button {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background-color: #f3f4f6;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0;
}

/* 未输入消息时的样式 */
.send-button:disabled {
  background-color: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}

/* 输入消息后的样式 */
.send-button.can-send {
  background-color: #10b981;
  color: white;
}

.send-button.can-send:hover {
  background-color: #059669;
}

/* 发送中的样式 */
.send-button:disabled.can-send {
  background-color: #6ee7b7;
  cursor: not-allowed;
}

.send-button i {
  font-size: 14px;
}

/* 暗色主题支持 */
@media (prefers-color-scheme: dark) {
  .send-button {
    background-color: #374151;
    color: #6b7280;
  }

  .send-button:disabled {
    background-color: #374151;
    color: #6b7280;
  }

  .send-button.can-send {
    background-color: #059669;
    color: white;
  }

  .send-button.can-send:hover {
    background-color: #047857;
  }

  .send-button:disabled.can-send {
    background-color: #065f46;
  }
}

.chat-type-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  width: fit-content;
  margin-top: 4px;
}

.chat-type-badge.normal {
  background-color: #c2e7e9;
  color: #3f5e3f;
}

.chat-type-badge.rag {
  background-color: #dbeafe;
  color: #315b81;
}

.chat-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;  /* 允许内容收缩 */
}

.chat-title {
  font-size: 14px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
  max-width: 180px;
}

/* 暗色主题支持 */
@media (prefers-color-scheme: dark) {
  .chat-type-badge.normal {
    background-color: #374151;
    color: #9ca3af;
  }

  .chat-type-badge.rag {
    background-color: #89ff64;
    color: #b1fd93;
  }

  .chat-title {
    color: #e5e7eb;
  }
}

.message-sources {
  margin-top: 12px;
  padding: 12px;
  background-color: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.sources-title {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
  font-weight: 500;
}

.source-item {
  margin-bottom: 8px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  cursor: pointer;
}

.source-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: #f1f5f9;
  transition: background-color 0.2s;
}

.source-header:hover {
  background-color: #e2e8f0;
}

.source-filename {
  font-size: 13px;
  color: #334155;
  flex: 1;
}

.file-type-badge {
  padding: 2px 6px;
  background-color: #e2e8f0;
  border-radius: 4px;
  font-size: 11px;
  color: #475569;
}

.source-content {
  padding: 12px;
  background-color: #ffffff;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
  white-space: pre-wrap;
  border-top: 1px solid #e2e8f0;
}

/* 暗色主题支持 */
@media (prefers-color-scheme: dark) {
  .message-sources {
    background-color: #1e293b;
    border-color: #334155;
  }

  .sources-title {
    color: #94a3b8;
  }

  .source-item {
    border-color: #334155;
  }

  .source-header {
    background-color: #1e293b;
  }

  .source-header:hover {
    background-color: #334155;
  }

  .source-filename {
    color: #e2e8f0;
  }

  .file-type-badge {
    background-color: #334155;
    color: #cbd5e1;
  }

  .source-content {
    background-color: #0f172a;
    color: #e2e8f0;
    border-top-color: #334155;
  }
}

.chat-messages::after {
  content: '';
  position: fixed;
  bottom: 90px;
  left: 260px;
  right: 0;
  height: 40px;
  background: linear-gradient(to bottom, transparent, #ffffff);
  pointer-events: none;
  z-index: 99;
}

@media (prefers-color-scheme: dark) {
  .chat-messages::after {
    background: linear-gradient(to bottom, transparent, #1f2937);
  }
  
  .input-area {
    background-color: #1f2937;
    border-top-color: #374151;
  }
}

.message.error {
  background-color: #fef2f2;
  border: 1px solid #fee2e2;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: 8px;
  margin: 8px 0;
  font-size: 14px;
  max-width: 80%;
}

.message.error .message-content {
  color: #dc2626;
}

/* 添加置信度样式 */
.message-confidence {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  margin-top: 4px;
  width: fit-content;
}

.message-confidence.高 {
  background-color: #dcfce7;
  color: #166534;
}

.message-confidence.中 {
  background-color: #fef9c3;
  color: #854d0e;
}

.message-confidence.低 {
  background-color: #fee2e2;
  color: #991b1b;
}
</style> 