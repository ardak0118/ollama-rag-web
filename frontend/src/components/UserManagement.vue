<template>
  <!-- ... 其他模板内容 ... -->
  <div class="import-section">
    <input
      type="file"
      ref="fileInput"
      @change="handleFileSelect"
      accept=".csv"
      style="display: none"
    >
    <button @click="$refs.fileInput.click()">选择CSV文件</button>
    <button @click="importUsers" :disabled="!selectedFile">
      导入用户
    </button>
    <span v-if="selectedFile">已选择: {{ selectedFile.name }}</span>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedFile: null,
      // ... 其他数据
    }
  },
  methods: {
    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file && file.type === 'text/csv') {
        this.selectedFile = file
      } else {
        alert('请选择CSV格式的文件')
        event.target.value = ''
      }
    },

    async importUsers() {
      if (!this.selectedFile) return

      try {
        const formData = new FormData()
        formData.append('file', this.selectedFile)

        const response = await api.post('/api/admin/users/import', formData)
        
        if (response.ok) {
          const result = await response.json()
          alert(`成功导入 ${result.imported_count} 个用户`)
          this.loadUsers() // 刷新用户列表
        } else {
          const error = await response.json()
          alert('导入失败：' + (error.detail || '未知错误'))
        }
      } catch (error) {
        console.error('Import error:', error)
        alert('导入出错：' + error.message)
      } finally {
        this.selectedFile = null
        this.$refs.fileInput.value = ''
      }
    }
  }
}
</script>