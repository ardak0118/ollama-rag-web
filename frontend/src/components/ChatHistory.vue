<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <button class="new-chat-btn" @click="$emit('new-chat')">
        <span>+ 新对话</span>
      </button>
      <button class="knowledge-base-btn" @click="$emit('open-knowledge')">
        <span>📚 知识库</span>
      </button>
    </div>
    <div class="sidebar-content">
      <div class="chat-history">
        <div v-for="conv in conversations" 
             :key="conv.id"
             :class="['chat-item', { active: currentConversationId === conv.id }]"
             @click="$emit('select-chat', conv.id)">
          <span class="chat-title">{{ conv.title || '新对话' }}</span>
          <button class="delete-btn" @click.stop="$emit('delete-chat', conv.id)">
            <span>×</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatHistory',
  props: {
    conversations: {
      type: Array,
      required: true
    },
    currentConversationId: {
      type: String,
      default: null
    }
  }
}
</script>

<style scoped>
.sidebar {
  width: 260px;
  background-color: #f9fafb;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  height: 100%;
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

.chat-history {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chat-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  background-color: transparent;
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
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
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
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background-color: #fee2e2;
  color: #dc2626;
}

/* 添加滚动条样式 */
.sidebar-content::-webkit-scrollbar {
  width: 4px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background-color: #e5e7eb;
  border-radius: 2px;
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background-color: #d1d5db;
}

/* 添加知识库按钮样式 */
.knowledge-base-btn {
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
  margin-top: 8px;  /* 添加与上方按钮的间距 */
}

.knowledge-base-btn:hover {
  background-color: #f3f4f6;
}
</style> 