<template>
  <div class="knowledge-base" v-if="visible">
    <div class="knowledge-header">
      <h2>知识库</h2>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>
    <div class="knowledge-content">
      <div class="upload-section">
        <button class="upload-btn">
          <span>📄 上传文档</span>
          <input type="file" @change="handleFileUpload" accept=".txt,.pdf,.doc,.docx">
        </button>
      </div>
      <div class="documents-list">
        <div v-if="documents.length === 0" class="empty-state">
          暂无文档，请上传文档
        </div>
        <div v-else v-for="doc in documents" :key="doc.id" class="document-item">
          <div class="doc-info">
            <span class="doc-name">{{ doc.name }}</span>
            <span class="doc-size">{{ formatSize(doc.size) }}</span>
          </div>
          <button class="delete-doc-btn" @click="deleteDocument(doc.id)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'KnowledgeBase',
  props: {
    visible: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      documents: []
    }
  },
  methods: {
    async handleFileUpload(event) {
      const file = event.target.files[0];
      if (file) {
        try {
          const formData = new FormData();
          formData.append('file', file);

          const response = await fetch('http://localhost:8000/api/documents/upload', {
            method: 'POST',
            body: formData
          });

          if (!response.ok) {
            throw new Error('Upload failed');
          }

          const result = await response.json();
          
          this.documents.push({
            id: Date.now(),
            name: file.name,
            size: file.size,
            chunks: result.chunks_count
          });
        } catch (error) {
          console.error('Error uploading file:', error);
          // 添加错误提示
        }
      }
    },
    deleteDocument(id) {
      this.documents = this.documents.filter(doc => doc.id !== id);
    },
    formatSize(bytes) {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
  }
}
</script>

<style scoped>
.knowledge-base {
  position: fixed;
  top: 0;
  right: 0;
  width: 400px;
  height: 100vh;
  background-color: #ffffff;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  z-index: 1000;
  box-shadow: -2px 0 10px rgba(0, 0, 0, 0.1);
}

.knowledge-header {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.knowledge-header h2 {
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
  padding: 4px 8px;
  border-radius: 4px;
}

.close-btn:hover {
  background-color: #f3f4f6;
}

.knowledge-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.upload-section {
  margin-bottom: 20px;
}

.upload-btn {
  position: relative;
  width: 100%;
  padding: 12px;
  background-color: #f9fafb;
  border: 2px dashed #e5e7eb;
  border-radius: 6px;
  color: #374151;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.upload-btn:hover {
  background-color: #f3f4f6;
}

.upload-btn input[type="file"] {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-state {
  text-align: center;
  color: #6b7280;
  padding: 32px;
}

.document-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.doc-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-name {
  font-size: 14px;
  color: #374151;
}

.doc-size {
  font-size: 12px;
  color: #6b7280;
}

.delete-doc-btn {
  padding: 4px 8px;
  background: none;
  border: none;
  color: #dc2626;
  cursor: pointer;
  font-size: 14px;
  border-radius: 4px;
}

.delete-doc-btn:hover {
  background-color: #fee2e2;
}
</style> 