<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-window">

      <div class="modal-header">
        <div class="header-title">
          <span class="header-icon">📥</span>
          <h3>Journal Data Import</h3>
        </div>
        <button class="btn-close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <!-- Состояние: Процесс импорта уже идет (блокировка) -->
        <div v-if="isImportingInProcess" class="processing-state">
          <div class="spinner"></div>
          <p class="status-msg">Database is currently locked</p>
          <div class="status-badge status-orange">
            {{ importStatus?.status }}
          </div>
          <p class="sub-text">Please wait until the operation is finished.</p>
        </div>

        <!-- Состояние: Выбор файла -->
        <div v-else class="upload-container">
          <div
            class="drop-zone"
            :class="{ 'drop-active': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="$refs.fileInput.click()"
          >
            <input
              type="file"
              ref="fileInput"
              class="hidden-input"
              accept=".zip"
              @change="handleFileSelect"
            >

            <div v-if="!selectedFile" class="drop-placeholder">
              <span class="upload-icon">📄</span>
              <p>Click or drag your <strong>.zip</strong> archive here</p>
            </div>
            <div v-else class="selected-file-info">
              <span class="upload-icon">✅</span>
              <p class="file-name">{{ selectedFile.name }}</p>
              <p class="file-size">{{ (selectedFile.size / 1024 / 1024).toFixed(2) }} MB</p>
            </div>
          </div>

          <div class="import-options">
            <label class="checkbox-container">
              <input type="checkbox" v-model="replaceData">
              <span class="checkmark"></span>
              <span class="label-text">Replace existing data</span>
            </label>

            <div v-if="replaceData" class="warning-box">
              <strong>⚠️ WARNING:</strong> This will delete ALL current journal records, attachments and structures before importing. This action cannot be undone.
            </div>
          </div>
        </div>

        <!-- Блок ошибки если импорт упал -->
        <div v-if="importStatus?.status === 'FAILED'" class="error-banner">
          <strong>Import failed:</strong> {{ importStatus.error_message }}
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-secondary" @click="$emit('close')" :disabled="isUploading">
          Close
        </button>

        <div class="footer-actions">
          <button
            class="btn-success"
            :disabled="!selectedFile || isUploading || isImportingInProcess"
            @click="startImport"
          >
            {{ isUploading ? 'Uploading...' : 'Start Import' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'

const emit = defineEmits(['close'])
const selectedFile = ref(null)
const isDragging = ref(false)
const replaceData = ref(false)
const isUploading = ref(false)
const importStatus = ref(null)
const isWaitingForCurrentResult = ref(false) // Чтобы знать, что импорт запущен именно сейчас
let pollingTimer = null

// Проверяем, заблокирована ли база (идет ли сейчас импорт или экспорт)
const isImportingInProcess = computed(() => {
  const s = importStatus.value?.status
  return s === 'PROCESSING_IMPORT' || s === 'PROCESSING_EXPORT'
})

const fetchStatus = async () => {
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('/api/export-all/status', {
      headers: { 'Authorization': `Bearer ${token}` },
      params: { process_type: 'IMPORT' }
    })
    importStatus.value = res.data

    if (res.data.status === 'COMPLETED') {
      stopPolling()
      // Перезагружаем ТОЛЬКО если мы сами нажали кнопку в этой сессии
      if (isWaitingForCurrentResult.value) {
        alert("Import successfully completed!")
        const token = localStorage.getItem('token')
        await axios.delete('/api/export-all', { headers: { 'Authorization': `Bearer ${token}` }, params: { process_type: 'IMPORT' } })
        window.location.reload()
      }
    }
    if (res.data.status === 'FAILED') {
      stopPolling()
      isWaitingForCurrentResult.value = false
    }
  } catch (err) {
    if (err.response?.status === 404) {
      importStatus.value = null
      stopPolling()
    }
  }
}

const startPolling = () => {
  stopPolling()
  pollingTimer = setInterval(fetchStatus, 10000)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file && file.name.endsWith('.zip')) {
    selectedFile.value = file
  } else {
    alert("Please select a valid ZIP archive.")
  }
}

const handleDrop = (e) => {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.name.endsWith('.zip')) {
    selectedFile.value = file
  } else {
    alert("Please drop a valid ZIP archive.")
  }
}

const startImport = async () => {
  if (replaceData.value && !confirm("DANGER: Are you sure you want to REPLACE all your current data? Everything will be deleted.")) {
    return
  }
  isWaitingForCurrentResult.value = true
  isUploading.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('replace', replaceData.value)

  try {
    const token = localStorage.getItem('token')
    await axios.post('/api/import/start', formData, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'multipart/form-data'
      }
    })
    await fetchStatus()
    startPolling()
  } catch (err) {
    const msg = err.response?.data?.detail || err.message
    alert("Failed to start import: " + msg)
  } finally {
    isUploading.value = false
  }
}

onMounted(async () => {
  await fetchStatus()

  // Если при открытии статус уже "завершен" или "ошибка" — это хвосты прошлого раза
  if (importStatus.value?.status === 'COMPLETED' || importStatus.value?.status === 'FAILED') {
    const token = localStorage.getItem('token')
    await axios.delete('/api/export-all', { headers: { 'Authorization': `Bearer ${token}` } })
    importStatus.value = null
  }
  // Если реально идет процесс — подхватываем и следим
  else if (isImportingInProcess.value) {
    isWaitingForCurrentResult.value = true
    startPolling()
  }
})

onUnmounted(stopPolling)
</script>

<style scoped>
/* Используем те же базовые стили что и в экспорт модалке */
.modal-overlay {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(0, 0, 0, 0.6); display: flex; align-items: center; justify-content: center;
  z-index: 3000; backdrop-filter: blur(4px);
}
.modal-window {
  background: #ffffff; width: 100%; max-width: 500px; border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); display: flex; flex-direction: column;
  overflow: hidden; animation: modal-appear 0.2s ease-out;
}
@keyframes modal-appear { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }

.modal-header { padding: 16px 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; background: #f8f9fa; }
.header-title { display: flex; align-items: center; gap: 10px; }
.header-icon { font-size: 1.4rem; }
.modal-header h3 { margin: 0; font-size: 1.2rem; color: #2c3e50; }
.btn-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: #999; }

.modal-body { padding: 24px; min-height: 200px; }

/* Drop Zone Styles */
.drop-zone {
  border: 2px dashed #ccc; border-radius: 10px; padding: 40px 20px; text-align: center;
  cursor: pointer; transition: all 0.2s; background: #fafafa;
}
.drop-zone:hover, .drop-active { border-color: #42b983; background: #f0fcf7; }
.hidden-input { display: none; }
.upload-icon { font-size: 2.5rem; display: block; margin-bottom: 10px; }
.file-name { font-weight: bold; color: #2c3e50; margin: 5px 0; word-break: break-all; }
.file-size { font-size: 0.8rem; color: #999; }

/* Options & Warning */
.import-options { margin-top: 20px; }
.checkbox-container { display: flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 600; color: #2c3e50; }
.warning-box {
  margin-top: 12px; padding: 12px; background: #fff5f5; border-left: 4px solid #e74c3c;
  color: #c0392b; font-size: 0.85rem; line-height: 1.4;
}

/* Processing State */
.processing-state { text-align: center; padding: 20px 0; }
.spinner { width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #f39c12; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 15px; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.status-msg { font-weight: bold; color: #2c3e50; margin-bottom: 10px; }

.modal-footer { padding: 16px 20px; border-top: 1px solid #eee; background: #f8f9fa; display: flex; justify-content: space-between; align-items: center; }
.footer-actions { display: flex; gap: 8px; }

.btn-success { background: #42b983; color: white; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; border: none; }
.btn-success:disabled { background: #ccc; cursor: not-allowed; }
.btn-secondary { background: #eee; color: #666; padding: 8px 16px; border-radius: 6px; cursor: pointer; border: none; }

.status-badge { padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; display: inline-block; }
.status-orange { background: #fff4e6; color: #f39c12; }

.error-banner { margin-top: 15px; background: #fdf2f2; color: #e74c3c; padding: 10px; border-radius: 6px; font-size: 0.9rem; border: 1px solid #fadbd8; }
</style>