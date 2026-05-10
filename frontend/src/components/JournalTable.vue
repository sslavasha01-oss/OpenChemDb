<template>
  <div class="results-section">
    <div class="header">
      <h3>Journal Records</h3>
      <span v-if="totalCount > 0" class="stat">
        Total: {{ totalCount }} (showing {{ offset + 1 }}-{{ Math.min(offset + limit, totalCount) }})
      </span>
    </div>

    <!-- Загрузка / Ошибка / Пусто (без изменений) -->
    <div v-if="loading" class="status-msg loading">
      <div class="spinner"></div>
      <p>Loading journal records...</p>
    </div>

    <div v-else-if="error" class="status-msg error">
      <span class="icon">⚠️</span>
      <p>{{ error }}</p>
    </div>

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
              <th class="col-cond">Conditions</th>
              <th class="col-yield">Yield</th>
              <th class="col-procedure">Procedure</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rec in records" :key="rec.id" class="reaction-row" @click="$emit('select-record', rec)">
              <!-- 1. Картинка -->
              <td class="col-viz">
                <div class="reaction-container" v-if="rec.product_svg" v-html="rec.product_svg"></div>
                <div class="no-viz" v-else>No Structure</div>
              </td>

              <!-- 2. ID и Дата -->
              <td class="col-id">
                <div class="id-badge">#{{ rec.external_id }}</div>
                <div class="date-text">{{ formatDate(rec.date_added) }}</div>
              </td>

              <!-- 3. Conditions (Условия) -->
              <td class="col-cond">
                <div class="cond-text">
                  <!-- Пока выводим заглушку, так как в схеме нет отдельного поля,
                       либо можно выводить краткий комментарий -->
                  {{ rec.conditions || 'n/a' }}
                </div>
              </td>

              <!-- 4. Выход (%) -->
              <td class="col-yield">
                <div v-if="rec.product_yield_calc" class="yield-badge">
                  {{ rec.product_yield_calc }}%
                </div>
                <div v-else class="no-yield">—</div>
              </td>

              <!-- 5. Методика -->
              <td class="col-procedure">
                <div class="procedure-preview">
                  {{ rec.procedure || 'No description...' }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Пагинация (без изменений) -->
      <div class="pagination" v-if="totalPages > 1">
        <button :disabled="currentPage === 1" @click="changePage(currentPage - 1)" class="pag-btn">← Prev</button>
        <div class="page-numbers"><span class="current">{{ currentPage }}</span> / {{ totalPages }}</div>
        <button :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)" class="pag-btn">Next →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
// ... (Весь JS код остается точно таким же, как в твоем рабочем примере) ...
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const emit = defineEmits(['select-record'])
const records = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const limit = 10
const loading = ref(false)
const error = ref(null)
const pagesCache = ref({})

const offset = computed(() => (currentPage.value - 1) * limit)
const totalPages = computed(() => Math.ceil(totalCount.value / limit))

const fetchCount = async () => {
  if (totalCount.value > 0) return;
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/my-journal/count', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    totalCount.value = response.data.total
  } catch (err) { console.error(err) }
}

const fetchRecords = async (forceRefresh = false) => {
  if (!forceRefresh && pagesCache.value[currentPage.value]) {
    records.value = pagesCache.value[currentPage.value];
    return;
  }
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/my-journal/list', {
      params: { limit: limit, offset: offset.value },
      headers: { 'Authorization': `Bearer ${token}` }
    })
    pagesCache.value[currentPage.value] = response.data
    records.value = response.data
  } catch (err) { error.value = "Load failed" } finally { loading.value = false }
}

const refreshData = async () => {
  pagesCache.value = {};
  totalCount.value = 0;
  currentPage.value = 1;
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
    day: '2-digit', month: '2-digit'
  })
}

onMounted(() => { fetchCount(); fetchRecords(); })
defineExpose({ refreshData })
</script>

<style scoped>
.results-section { background: white; border-radius: 8px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.header { display: flex; justify-content: space-between; border-bottom: 2px solid #42b983; margin-bottom: 15px; }

.table-container { width: 100%; overflow-x: auto; }
.reaction-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.reaction-table th { background: #f8f9fa; padding: 12px 10px; text-align: left; font-size: 0.75rem; color: #7f8c8d; text-transform: uppercase; }
.reaction-table td { padding: 10px; border-bottom: 1px solid #eee; vertical-align: middle; }

/* Настройка колонок */
.col-viz { width: 180px; }      /* Картинка чуть компактнее */
.col-id { width: 100px; }       /* ID и дата */
.col-cond { width: 150px; }     /* Условия */
.col-yield { width: 80px; }      /* Выход */
.col-procedure { width: auto; }  /* Методика тянется */

.reaction-container :deep(svg) { max-width: 100%; height: auto; max-height: 100px; }

.id-badge { background: #42b983; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.85rem; }
.date-text { font-size: 0.7rem; color: #999; margin-top: 4px; }

.yield-badge {
  background: #e6f7ef; color: #2d8a5d; font-weight: bold;
  padding: 4px 8px; border-radius: 6px; display: inline-block;
  border: 1px solid #c2eadd;
}
.no-yield { color: #ccc; font-size: 0.9rem; }

.cond-text { font-size: 0.85rem; color: #666; font-style: italic; }

.procedure-preview {
  font-size: 0.85rem; color: #444; display: -webkit-box;
  -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}

.reaction-row { cursor: pointer; }
.reaction-row:hover { background: #f9fdfb; }

/* Пагинация и спиннер без изменений */
.pagination { margin-top: 20px; display: flex; justify-content: center; align-items: center; gap: 15px; }
.pag-btn { padding: 6px 14px; border: 1px solid #42b983; background: white; color: #42b983; border-radius: 20px; cursor: pointer; }
.pag-btn:disabled { opacity: 0.3; }
.status-msg { text-align: center; padding: 40px; color: #7f8c8d; }
.spinner { width: 30px; height: 30px; border: 3px solid #f3f3f3; border-top: 3px solid #42b983; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>