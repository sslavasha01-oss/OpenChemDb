<template>
  <div class="results-section">
    <div class="header">
      <h3>Journal Records</h3>
      <span v-if="totalCount > 0" class="stat">
        Total: {{ totalCount }} (showing {{ offset + 1 }}-{{ Math.min(offset + limit, totalCount) }})
      </span>
    </div>

    <!-- Загрузка -->
    <div v-if="loading" class="status-msg loading">
      <div class="spinner"></div>
      <p>Loading journal records...</p>
    </div>

    <!-- Ошибка -->
    <div v-else-if="error" class="status-msg error">
      <span class="icon">⚠️</span>
      <p>{{ error }}</p>
    </div>

    <!-- Пусто -->
    <div v-else-if="records.length === 0" class="status-msg empty">
      <p>Your journal is empty. Create your first record in "Method" tab!</p>
    </div>

    <!-- Таблица -->
    <div v-else>
      <div class="table-container">
        <table class="reaction-table">
          <thead>
            <tr>
              <th class="col-viz">Product</th>
              <th class="col-id">ID / Date</th>
              <th class="col-procedure">Procedure Preview</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rec in records" :key="rec.id" class="reaction-row" @click="$emit('select-record', rec)">
              <td class="col-viz">
                <div class="reaction-container" v-if="rec.product_svg" v-html="rec.product_svg"></div>
                <div class="no-viz" v-else>No Structure</div>
              </td>
              <td class="col-id" data-label="Entry">
                <div class="id-badge">#{{ rec.external_id }}</div>
                <div class="date-text">{{ formatDate(rec.date_added) }}</div>
              </td>
              <td class="col-procedure" data-label="Procedure">
                <div class="procedure-preview">
                  {{ rec.procedure || 'No procedure description...' }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Пагинация -->
      <div class="pagination" v-if="totalPages > 1">
        <button :disabled="currentPage === 1" @click="changePage(currentPage - 1)" class="pag-btn">← Prev</button>
        <div class="page-numbers"><span class="current">{{ currentPage }}</span> / {{ totalPages }}</div>
        <button :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)" class="pag-btn">Next →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const emit = defineEmits(['select-record'])

const records = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const limit = 10 // Количество записей на страницу
const loading = ref(false)
const error = ref(null)

const pagesCache = ref({})

const offset = computed(() => (currentPage.value - 1) * limit)
const totalPages = computed(() => Math.ceil(totalCount.value / limit))

const fetchCount = async () => {
  if (totalCount.value > 0) return; // Уже знаем, не идем на бэк
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/my-journal/count', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    totalCount.value = response.data.total
  } catch (err) {
    console.error("Count fetch error:", err)
  }
}

const fetchRecords = async (forceRefresh = false) => {
  // 1. Если данные для этой страницы уже есть в кеше и мы не заставляем обновлять — берем из кеша
  if (!forceRefresh && pagesCache.value[currentPage.value]) {
    records.value = pagesCache.value[currentPage.value];
    return;
  }

  loading.value = true
  error.value = null
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/my-journal/list', {
      params: { limit: limit, offset: offset.value },
      headers: { 'Authorization': `Bearer ${token}` }
    })

    // Сохраняем в кеш и в текущие записи
    pagesCache.value[currentPage.value] = response.data
    records.value = response.data
  } catch (err) {
    error.value = "Failed to load records"
    console.error(err)
  } finally {
    loading.value = false
  }
}

// Публичный метод для сброса кеша (вызовем из родителя после Save)
const refreshData = async () => {
  pagesCache.value = {}; // Чистим кеш
  totalCount.value = 0;   // Сбрасываем счетчик
  currentPage.value = 1; // Возвращаемся на первую
  await fetchCount();
  await fetchRecords(true);
}

const changePage = (newPage) => {
  currentPage.value = newPage
  fetchRecords()
}

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

// Заглушка для будущего поиска
const performSearch = (searchParams) => {
  console.log("Search mode will be implemented here:", searchParams)
}

onMounted(() => {
  fetchCount()
  fetchRecords()
})

defineExpose({ refreshData, performSearch: (p) => console.log(p) })
</script>

<style scoped>
/* Стили в стиле книжной базы */
.results-section {
  background: white; border-radius: 8px; padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); width: 100%;
}
.header { display: flex; justify-content: space-between; border-bottom: 2px solid #42b983; margin-bottom: 15px; padding-bottom: 5px; }
.header h3 { margin: 0; color: #2c3e50; }
.stat { font-size: 0.9rem; color: #666; }

.table-container { width: 100%; overflow-x: auto; }
.reaction-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.reaction-table th { background: #f8f9fa; text-align: left; font-size: 0.85rem; color: #7f8c8d; text-transform: uppercase; }
.reaction-table th, .reaction-table td { padding: 12px 10px; border-bottom: 1px solid #eee; vertical-align: middle; }

.col-viz { width: 250px; }
.col-id { width: 150px; }
.col-procedure { width: auto; }

.reaction-container {
  width: 100%; background: #fff; border: 1px solid #f0f0f0;
  border-radius: 4px; display: flex; justify-content: center; padding: 5px;
}
.reaction-container :deep(svg) { max-width: 100%; height: auto; max-height: 120px; }

.id-badge {
  background: #42b983; color: white; padding: 2px 8px;
  border-radius: 12px; display: inline-block; font-weight: bold; font-size: 0.9rem;
}
.date-text { font-size: 0.75rem; color: #999; margin-top: 4px; }

.procedure-preview {
  font-size: 0.9rem; color: #444; display: -webkit-box;
  -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
  line-height: 1.4;
}

.reaction-row { cursor: pointer; transition: background 0.2s; }
.reaction-row:hover { background: #f0fff8; }

/* Пагинация */
.pagination { margin-top: 20px; display: flex; justify-content: center; align-items: center; gap: 15px; }
.pag-btn {
  padding: 6px 14px; border: 1px solid #42b983; background: white;
  color: #42b983; border-radius: 20px; cursor: pointer; transition: 0.2s;
}
.pag-btn:hover:not(:disabled) { background: #42b983; color: white; }
.pag-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.status-msg { text-align: center; padding: 40px; color: #7f8c8d; }
.spinner {
  width: 30px; height: 30px; border: 3px solid #f3f3f3; border-top: 3px solid #42b983;
  border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 10px;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>