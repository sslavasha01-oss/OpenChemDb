<script setup>
sentiments: [
  {name: 'Journal', color: '#42b983'}
]
import {ref, computed} from 'vue'
import axios from 'axios'
import ReactionVisualizer from './ReactionVisualizer.vue'
import EvaluationModal from '@/components/modals/EvaluationModal.vue'
import ReactionDetailsModal from '@/components/modals/ReactionDetailsModal.vue'

const isDetailsOpen = ref(false)
const selectedReaction = ref(null)

const showDetails = (reaction) => {
  selectedReaction.value = reaction
  isDetailsOpen.value = true
}

const evaluations = ref({}) // { entry_id: { CHECK: 0, POO: 0, ERROR: 0 } }

const props = defineProps({
  smiles: String,
  exact: Boolean
})

// Состояние
const allIds = ref([])           // Все 200 ID
const cachedData = ref({})       // Кэш данных: { page: [reactions] }
const currentPage = ref(1)
const pageSize = 10
const loading = ref(false)
const error = ref(null)

// Общее количество страниц на основе загруженных ID
const totalPages = computed(() => Math.ceil(allIds.value.length / pageSize))

// Текущий срез данных для отображения
const currentResults = computed(() => cachedData.value[currentPage.value] || [])

const isEvalModalOpen = ref(false)
const selectedEntryId = ref(null)

const openEvalModal = (id) => {
  selectedEntryId.value = id
  isEvalModalOpen.value = true
}

const onEvalSuccess = ({id, status}) => {
  // Локально обновляем счетчик, чтобы интерфейс мгновенно среагировал
  if (!evaluations.value[id]) {
    evaluations.value[id] = {CHECK: 0, POO: 0, ERROR: 0}
  }
  evaluations.value[id][status]++
}

const submitEvaluation = async (id, status) => {
  try {
    await axios.post('/api/evaluations/add', null, {
      params: {
        target: 'REACTIONS',
        entry_id: id,
        status: status,
        comment: '' // Пока пусто
      }
    })
    // Обновляем локально счетчик, чтобы не делать лишний запрос
    if (!evaluations.value[id]) {
      evaluations.value[id] = {CHECK: 0, POO: 0, ERROR: 0}
    }
    evaluations.value[id][status]++
  } catch (err) {
    alert("Нужна авторизация для оценки!")
  }
}

/**
 * Загрузка оценок для текущей страницы
 */
const fetchEvaluations = async (ids) => {
  try {
    const params = new URLSearchParams()
    params.append('target', 'REACTIONS')
    ids.forEach(id => params.append('entry_ids', id))

    const response = await axios.get('/api/evaluations/batch', {params})
    // Объединяем с уже имеющимися (кэшируем)
    evaluations.value = {...evaluations.value, ...response.data}
  } catch (err) {
    console.error("Ошибка загрузки оценок:", err)
  }
}

/**
 * ЭТАП 1: Поиск ID (вызывается из родителя через ref или по кнопке)
 * Мы выносим это в метод, который будет дергать SearchView
 */
const performNewSearch = async () => {
  if (!props.smiles) return

  loading.value = true
  error.value = null
  allIds.value = []
  cachedData.value = {}
  currentPage.value = 1

  try {
    const response = await axios.get('/api/reactions/search/ids', {
      params: {
        smiles: props.smiles,
        exact: props.exact
      }
    })
    allIds.value = response.data.ids

    // Если что-то нашли, сразу грузим первую страницу
    if (allIds.value.length > 0) {
      await fetchPageData(1)
    }
  } catch (err) {
    error.value = "Ошибка при поиске ID"
    console.error(err)
  } finally {
    loading.value = false
  }
}

/**
 * ЭТАП 2: Загрузка конкретной страницы по ID
 */
const fetchPageData = async (page) => {
  if (cachedData.value[page]) {
    currentPage.value = page
    return
  }

  const start = (page - 1) * pageSize
  const idsToFetch = allIds.value.slice(start, start + pageSize)

  if (idsToFetch.length === 0) return

  loading.value = true
  try {
    const response = await axios.get('/api/reactions/search/by-ids', {
      params: {ids: idsToFetch},
      // Axios сериализует массивы как ids=1&ids=2, что подходит для FastAPI Query(...)
      paramsSerializer: {indexes: null}
    })

    cachedData.value[page] = response.data
    currentPage.value = page
  } catch (err) {
    error.value = "Ошибка загрузки данных реакций"
  } finally {
    loading.value = false
  }
  await fetchEvaluations(idsToFetch)
}

// Пробрасываем метод поиска наружу, чтобы SearchView мог его вызвать
defineExpose({performNewSearch})
</script>

<template>
  <div class="results-section">
    <div class="header">
      <h3>Journal Base</h3>
      <span v-if="allIds.length > 0" class="stat">
        Найдено: {{ allIds.length }} (показано {{
          (currentPage - 1) * 10 + 1
        }}-{{ Math.min(currentPage * 10, allIds.length) }})
      </span>
    </div>

    <div v-if="loading && allIds.length === 0" class="loading">Поиск в архивах...</div>

    <div v-if="allIds.length > 0">
      <div class="table-container">
        <table class="reaction-table">
          <thead>
          <tr>
            <th>Reaction</th>
            <th>Conditions</th>
            <th>Yield</th>
            <th>References & DOI</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="res in currentResults" :key="res.id" class="reaction-row" @click="showDetails(res)">
            <td class="col-viz">
              <div class="reaction-img-placeholder">
                <ReactionVisualizer :smiles="res.reaction_raw_smiles"/>
              </div>
            </td>
            <td class="col-cond" data-label="Conditions">{{ res.conditions || '—' }}</td>
            <td class="col-yield" data-label="Yield">{{ res.yield_text || '—' }}%</td>
            <td class="col-ref" data-label="Source">
              <div class="ref-block">
                <span>{{ res.references }}</span>
                <a v-if="res.doi" :href="'https://doi.org/' + res.doi" target="_blank" class="doi-link">
                  {{ res.doi }}
                </a>
                <div class="eval-bar">
                  <button
                      class="eval-btn check"
                      :class="{ 'empty': !evaluations[res.id]?.CHECK }"
                      @click="openEvalModal(res.id)"
                      @click.stop="openEvalModal(res.id)"
                      title="Reproduced"
                  >
                    <span class="icon">✅</span>
                    <span class="count">{{ evaluations[res.id]?.CHECK || 0 }}</span>
                  </button>

                  <button
                      v-if="evaluations[res.id]?.POO > 0"
                      class="eval-btn poo"
                      @click="openEvalModal(res.id)"
                      @click.stop="openEvalModal(res.id)"
                      title="Not reproduced"
                  >
                    <span class="icon">💩</span>
                    <span class="count">{{ evaluations[res.id].POO }}</span>
                  </button>

                  <button
                      v-if="evaluations[res.id]?.ERROR > 0"
                      class="eval-btn error"
                      @click="openEvalModal(res.id)"
                      @click.stop="openEvalModal(res.id)"
                      title="Data error"
                  >
                    <span class="icon">🛑</span>
                    <span class="count">{{ evaluations[res.id].ERROR }}</span>
                  </button>

                  <button class="eval-btn comments" @click="openEvalModal(res.id)"
                          @click.stop="openEvalModal(res.id)" title="Comments">
                    <span class="icon">💬</span>
                    <span class="count">?</span>
                  </button>
                </div>
              </div>
            </td>
          </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination" v-if="totalPages > 1">
        <button :disabled="currentPage === 1" @click="fetchPageData(currentPage - 1)">← Prev</button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button :disabled="currentPage === totalPages" @click="fetchPageData(currentPage + 1)">Next →</button>
      </div>
    </div>

    <div v-else-if="!loading" class="no-results">Введите запрос и нажмите поиск</div>
  </div>
  <EvaluationModal
      :isOpen="isEvalModalOpen"
      :entryId="selectedEntryId"
      @close="isEvalModalOpen = false"
      @success="onEvalSuccess"
  />

  <ReactionDetailsModal
      :isOpen="isDetailsOpen"
      :reaction="selectedReaction"
      @close="isDetailsOpen = false"
  />
</template>

<style scoped>
.results-section {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  border-bottom: 2px solid #42b983;
  margin-bottom: 15px;
  padding-bottom: 5px;
}

/* Стили таблицы */
.table-container {
  width: 100%;
  overflow-x: auto;
}

.reaction-table {
  width: 100%;
  border-collapse: collapse;
  /* Убираем fixed, чтобы колонки могли подстраиваться под контент */
  table-layout: auto;
}

.reaction-table th, .reaction-table td {
  padding: 12px 8px;
  border-bottom: 1px solid #eee;
  vertical-align: middle; /* Центрируем по вертикали для красоты */
}

/* 2. Условия и Выход - сжимаем до минимума */
.col-cond {
  width: 10%;
  white-space: nowrap; /* Чтобы не разрывало короткие условия */
  font-size: 0.85rem;
  text-align: center;
}

.col-yield {
  width: 5%;
  text-align: center;
  font-weight: bold;
  color: #2c3e50;
}

.col-viz {
  width: 50%;
  min-width: 400px;
}

.col-text {
  width: 20%;
  font-size: 0.9rem;
  color: #444;
}

.col-ref {
  width: 35%;
  font-size: 0.8rem;
  line-height: 1.3;
}

.ref-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reaction-img-placeholder {
  background: #fff;
  border: 1px solid #f9f9f9;
  border-radius: 4px;
  padding: 5px;
}

.ref-block {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.doi-link {
  display: inline-block;
  color: #3498db;
  text-decoration: none;
  font-weight: 500;
  word-break: break-all; /* Чтобы длинные DOI не ломали верстку */
}

.doi-link:hover {
  text-decoration: underline;
}

/* Адаптивность (Mobile) */
@media (max-width: 768px) {
  .reaction-table thead {
    display: none;
  }

  /* Скрываем заголовки */
  .reaction-table tr {
    display: block;
    margin-bottom: 20px;
    border: 1px solid #eee;
    border-radius: 8px;
    padding: 10px;
  }

  .reaction-table td {
    display: block;
    width: 100% !important;
    padding: 5px 0;
    border: none;
  }

  .reaction-table td::before {
    content: attr(data-label);
    font-weight: bold;
    display: block;
    font-size: 0.75rem;
    color: #999;
    margin-bottom: 2px;
  }

  .reaction-table td:first-child::before {
    display: none;
  }

  /* Для картинки не нужен лейбл */
}

/* Пагинация */
.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
}

.pagination button {
  padding: 8px 15px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-weight: bold;
  color: #2c3e50;
}

.eval-bar {
  display: flex;
  flex-wrap: wrap; /* Чтобы на узких экранах иконки переносились */
  gap: 10px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.eval-btn {
  display: inline-flex;
  align-items: center;
  background: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 2px 6px;
  font-size: 0.85rem;
  transition: all 0.2s ease;
}

.eval-btn:hover {
  background: #fff;
  border-color: #42b983;
  transform: translateY(-1px);
}

.eval-btn.empty {
  opacity: 0.4;
  filter: grayscale(1);
}

.eval-btn.empty:hover {
  opacity: 1;
  filter: none;
}

.eval-btn .count {
  font-weight: bold;
  font-size: 0.8rem;
  color: #666;
}

/* Цвета при наведении или активном состоянии (опционально) */
.eval-btn.check:hover {
  background: #e8f5e9;
}

.eval-btn.poo:hover {
  background: #efebe9;
}

.eval-btn.error:hover {
  background: #ffebee;
}

.reaction-row {
  cursor: pointer;
  transition: background 0.2s;
}
.reaction-row:hover {
  background-color: #f9fffb; /* Легкий оттенок зеленого при наведении */
}
/* Чтобы клик по ссылке DOI не открывал модалку */
.doi-link {
  position: relative;
  z-index: 2;
}
</style>