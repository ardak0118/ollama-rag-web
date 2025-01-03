<template>
  <div class="params-tester">
    <h2>URL参数注册测试</h2>
    <div class="test-form">
      <div class="form-group">
        <label>用户名:</label>
        <input v-model="name" type="text" placeholder="输入用户名">
      </div>
      <div class="form-group">
        <label>手机号:</label>
        <input v-model="mobile" type="text" placeholder="输入手机号">
      </div>
      <div class="actions">
        <button @click="generateUrl" :disabled="!name || !mobile">
          生成测试链接
        </button>
        <button @click="openInNewTab" :disabled="!testUrl">
          在新标签页打开
        </button>
      </div>
    </div>

    <div v-if="testUrl" class="result">
      <h3>测试链接:</h3>
      <div class="url-display">
        {{ testUrl }}
        <button @click="copyUrl" class="copy-btn">
          复制链接
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'UrlParamsTester',
  setup() {
    const name = ref('')
    const mobile = ref('')
    const baseUrl = window.location.origin

    const testUrl = computed(() => {
      if (!name.value || !mobile.value) return ''
      return `${baseUrl}/url-register?name=${encodeURIComponent(name.value)}&mobile=${encodeURIComponent(mobile.value)}`
    })

    const generateUrl = () => {
      if (!name.value || !mobile.value) {
        alert('请输入用户名和手机号')
        return
      }
    }

    const openInNewTab = () => {
      if (testUrl.value) {
        window.open(testUrl.value, '_blank')
      }
    }

    const copyUrl = async () => {
      try {
        await navigator.clipboard.writeText(testUrl.value)
        alert('链接已复制到剪贴板')
      } catch (err) {
        console.error('复制失败:', err)
        alert('复制失败，请手动复制')
      }
    }

    return {
      name,
      mobile,
      testUrl,
      generateUrl,
      openInNewTab,
      copyUrl
    }
  }
}
</script>

<style scoped>
.params-tester {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.test-form {
  margin-top: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
}

.form-group input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.actions button {
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.actions button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.result {
  margin-top: 30px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.url-display {
  position: relative;
  padding: 10px;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  word-break: break-all;
}

.copy-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  padding: 4px 8px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>