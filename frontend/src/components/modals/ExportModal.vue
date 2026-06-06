<template>
  <!-- Затемненный фон (Overlay) -->
  <div class="modal-overlay" @click.self="$emit('close')">

    <!-- Само окно модалки -->
    <div class="modal-window">

      <div class="modal-header">
        <div class="header-title">
          <span class="header-icon">📦</span>
          <h3>Journal Data Export</h3>
        </div>
        <button class="btn-close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <div v-if="loadingStatus" class="loading-state">
          <div class="spinner"></div>
          <p>Checking export status...</p>
        </div>

        <div v-else-if="!exportInfo" class="empty-state">
          <p>No export archive found on the server.</p>
          <p class="sub-text">Click "Start Export" to collect all your records, structures, and attachments into a single ZIP file.</p>
        </div>

        <div v-else class="status-card">
          <div class="info-grid">
            <span class="label">Status:</span>
            <span :class="['status-badge', statusClass]">
              {{ exportInfo.status || (exportInfo.path ? 'COMPLETED' : 'PROCESSING') }}
            </span>

            <span class="label">Created:</span>
            <span class="value">{{ new Date(exportInfo.created_date).toLocaleString() }}</span>

            <span v-if="exportInfo.path" class="label">File name:</span>
            <span v-if="exportInfo.path" class="value file-name">{{ exportInfo.path.split('/').pop() }}</span>
          </div>

          <div v-if="exportInfo.error_message" class="error-banner">
            <strong>Error:</strong> {{ exportInfo.error_message }}
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button
          class="btn-secondary"
          @click="$emit('close')"
        >
          Close
        </button>

        <div class="footer-actions">
          <button
            v-if="exportInfo"
            class="btn-danger"
            :disabled="isProcessing"
            @click="deleteExport"
          >
            Delete
          </button>

          <button
            v-if="exportInfo?.path"
            class="btn-primary"
            @click="downloadExport"
          >
            Download ZIP
          </button>

          <button
            class="btn-success"
            :disabled="isProcessing"
            @click="startExport"
          >
            {{ exportInfo?.path ? 'Regenerate' : 'Start Export' }}
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
const exportInfo = ref(null)
const loadingStatus = ref(true)
const isProcessing = ref(false)
let pollingTimer = null // Переменная для хранения таймера

const statusClass = computed(() => {
  if (!exportInfo.value) return ''
  const s = exportInfo.value.status
  if (s === 'FAILED') return 'status-red'
  // Если есть путь, значит файл готов
  if (exportInfo.value.path || s === 'COMPLETED') return 'status-green'
  return 'status-orange'
})

// Основная функция загрузки статуса
const fetchStatus = async () => {
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('/api/export-all/status', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    exportInfo.value = res.data

    // Если экспорт завершился (появился путь) или упал с ошибкой — можно прекратить часто обновлять
    if (exportInfo.value.path || exportInfo.value.status === 'FAILED') {
      stopPolling()
    }
  } catch (err) {
    if (err.response?.status === 404) {
      exportInfo.value = null
      stopPolling() // Если записи нет, тоже нечего опрашивать
    }
  } finally {
    loadingStatus.value = false
  }
}

// Запуск цикла опроса
const startPolling = () => {
  stopPolling() // Очищаем старый, если был
  pollingTimer = setInterval(fetchStatus, 10000) // 10 секунд
}

// Остановка цикла опроса
const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const startExport = async () => {
  isProcessing.value = true
  try {
    const token = localStorage.getItem('token')
    await axios.post('/api/export-all/start', {}, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    await fetchStatus() // Сразу получаем новый статус
    startPolling()      // Запускаем опрос, так как процесс пошел в фоне
  } catch (err) {
    alert("Error: " + (err.response?.data?.detail || err.message))
  } finally {
    isProcessing.value = false
  }
}

const downloadExport = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/export-all/download', {
      headers: { 'Authorization': `Bearer ${token}` },
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `journal_export.zip`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (err) {
    alert("Download failed. The file may no longer exist.")
  }
}

const deleteExport = async () => {
  if (!confirm("Are you sure you want to delete this export from the server?")) return
  try {
    const token = localStorage.getItem('token')
    await axios.delete('/api/export-all', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    exportInfo.value = null
    stopPolling()
  } catch (err) {
    alert("Failed to delete export.")
  }
}

onMounted(async () => {
  await fetchStatus()
  // Если при открытии мы видим, что экспорт в процессе (нет пути и нет ошибки), запускаем опрос
  if (exportInfo.value && !exportInfo.value.path && exportInfo.value.status !== 'FAILED') {
    startPolling()
  }
})

// Обязательно очищаем таймер при уничтожении компонента (закрытии модалки)
onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
/* Фон (Затемнение) */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.6); /* Темный полупрозрачный фон */
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000; /* Выше всех */
  backdrop-filter: blur(4px); /* Легкое размытие заднего плана */
}

/* Окно модалки */
.modal-window {
  background: #ffffff; /* Непрозрачный белый фон */
  width: 100%;
  max-width: 500px;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modal-appear 0.2s ease-out;
}

@keyframes modal-appear {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

/* Шапка */
.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon { font-size: 1.4rem; }

.modal-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #2c3e50;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #999;
}

/* Контент */
.modal-body {
  padding: 24px;
  min-height: 150px;
}

.empty-state {
  text-align: center;
  color: #666;
}

.sub-text {
  font-size: 0.85rem;
  color: #999;
  margin-top: 8px;
}

/* Информация о статусе */
.status-card {
  background: #fdfdfd;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 16px;
}

.info-grid {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 12px;
  align-items: center;
}

.label {
  font-weight: bold;
  color: #7f8c8d;
  font-size: 0.9rem;
}

.value {
  color: #2c3e50;
  font-size: 0.95rem;
}

.file-name {
  font-family: monospace;
  background: #eee;
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
}

/* Бейджи статусов */
.status-badge {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: bold;
  display: inline-block;
  width: fit-content;
}

.status-green { background: #e6f7ee; color: #27ae60; }
.status-orange { background: #fff4e6; color: #f39c12; }
.status-red { background: #fdf2f2; color: #e74c3c; }

/* Футер */
.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid #eee;
  background: #f8f9fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-actions {
  display: flex;
  gap: 8px;
}

/* Кнопки */
button {
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary { background: #3498db; color: white; }
.btn-primary:hover { background: #2980b9; }

.btn-success { background: #42b983; color: white; }
.btn-success:hover { background: #3aa876; }

.btn-danger { background: #fdf2f2; color: #e74c3c; border: 1px solid #fadbd8; }
.btn-danger:hover { background: #e74c3c; color: white; }

.btn-secondary { background: #eee; color: #666; }
.btn-secondary:hover { background: #ddd; }

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Спиннер загрузки */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 15px;
}

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>