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
            <th class="col-viz">Reaction</th>
            <th class="col-cond">Conditions</th>
            <th class="col-yield">Yield</th>
            <th class="col-ref">References & DOI</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="res in currentResults" :key="res.id" class="reaction-row" @click="showDetails(res)">
            <td class="col-viz">
              <div class="reaction-container" v-html="res.svg_content"></div>
            </td>
            <td class="col-cond" data-label="Conditions">{{ res.conditions || '—' }}</td>
            <td class="col-yield" data-label="Yield">{{ res.yield_text || '—' }}%</td>
            <td class="col-ref" data-label="Source" @click.stop>
              <div class="ref-block">
                <span class="ref-text">{{ res.references }}</span>
                <a v-if="res.doi" :href="'https://doi.org/' + res.doi" target="_blank" class="doi-link">
                  {{ res.doi }}
                </a>
                <div class="eval-bar">
                  <button class="eval-btn check" :class="{ 'empty': !evaluations[res.id]?.CHECK }" @click="openEvalModal(res.id)" title="Reproduced">
                    <span class="icon">✅</span>
                    <span class="count">{{ evaluations[res.id]?.CHECK || 0 }}</span>
                  </button>

                  <button v-if="evaluations[res.id]?.POO > 0" class="eval-btn poo" @click="openEvalModal(res.id)" title="Not reproduced">
                    <span class="icon">💩</span>
                    <span class="count">{{ evaluations[res.id].POO }}</span>
                  </button>

                  <button v-if="evaluations[res.id]?.ERROR > 0" class="eval-btn error" @click="openEvalModal(res.id)" title="Data error">
                    <span class="icon">🛑</span>
                    <span class="count">{{ evaluations[res.id].ERROR }}</span>
                  </button>

                  <button class="eval-btn comments" @click="openEvalModal(res.id)" title="Comments">
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
        <button :disabled="currentPage === 1" @click="fetchPageData(currentPage - 1)" class="pag-btn">
          ← Prev
        </button>
        <div class="page-numbers">
          <span class="current">{{ currentPage }}</span> / <span>{{ totalPages }}</span>
        </div>
        <button :disabled="currentPage === totalPages" @click="fetchPageData(currentPage + 1)" class="pag-btn">
          Next →
        </button>
      </div>
    </div>

    <div v-else-if="!loading" class="no-results">Введите запрос и нажмите поиск</div>
  </div>

  <EvaluationModal :isOpen="isEvalModalOpen" :entryId="selectedEntryId" @close="isEvalModalOpen = false" @success="onEvalSuccess" />
  <ReactionDetailsModal :isOpen="isDetailsOpen" :reaction="selectedReaction" @close="isDetailsOpen = false" />
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import EvaluationModal from '@/components/modals/EvaluationModal.vue'
import ReactionDetailsModal from '@/components/modals/ReactionDetailsModal.vue'

const props = defineProps({
  smiles: String,
  exact: Boolean,
  mode: String // 'simple' или 'advanced'
})

const isDetailsOpen = ref(false)
const selectedReaction = ref(null)
const evaluations = ref({})
const allIds = ref([])
const cachedData = ref({})
const currentPage = ref(1)
const pageSize = 10
const loading = ref(false)
const error = ref(null)
const isEvalModalOpen = ref(false)
const selectedEntryId = ref(null)

const totalPages = computed(() => Math.ceil(allIds.value.length / pageSize))
const currentResults = computed(() => cachedData.value[currentPage.value] || [])

const showDetails = (reaction) => {
  selectedReaction.value = reaction
  isDetailsOpen.value = true
}

const openEvalModal = (id) => {
  selectedEntryId.value = id
  isEvalModalOpen.value = true
}

const onEvalSuccess = ({id, status}) => {
  if (!evaluations.value[id]) evaluations.value[id] = {CHECK: 0, POO: 0, ERROR: 0}
  evaluations.value[id][status]++
}

const fetchEvaluations = async (ids) => {
  try {
    const params = new URLSearchParams()
    params.append('target', 'REACTIONS')
    ids.forEach(id => params.append('entry_ids', id))
    const response = await axios.get('/api/evaluations/batch', {params})
    evaluations.value = {...evaluations.value, ...response.data}
  } catch (err) { console.error(err) }
}

const performNewSearch = async () => {
  if (!props.smiles) return
  loading.value = true
  allIds.value = []
  cachedData.value = {}
  currentPage.value = 1

  // Выбираем URL на основе режима
  const searchUrl = props.mode === 'advanced'
    ? '/api/reactions/search/ids/smarts'
    : '/api/reactions/search/ids/smiles'

  try {
    const response = await axios.get(searchUrl, {
      params: { smiles: props.smiles, exact: props.exact }
    })
    allIds.value = response.data.ids
    if (allIds.value.length > 0) await fetchPageData(1)
  } catch (err) {
    error.value = "Ошибка поиска"
  } finally {
    loading.value = false
  }
}

const fetchPageData = async (page) => {
  if (cachedData.value[page]) { currentPage.value = page; return }
  const start = (page - 1) * pageSize
  const idsToFetch = allIds.value.slice(start, start + pageSize)
  loading.value = true
  try {
    const response = await axios.get('/api/reactions/search/by-ids', {
      params: {ids: idsToFetch},
      paramsSerializer: {indexes: null}
    })
    cachedData.value[page] = response.data
    currentPage.value = page
    await fetchEvaluations(idsToFetch)
  } catch (err) { error.value = "Ошибка загрузки" } finally { loading.value = false }
}

defineExpose({performNewSearch})
</script>

<style scoped>
.results-section {
  box-sizing: border-box;
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
  width: 100%;
}

.header { display: flex; justify-content: space-between; border-bottom: 2px solid #42b983; margin-bottom: 15px; padding-bottom: 5px; }

.table-container {
  width: 100%;
  overflow-x: hidden; /* На десктопе скрываем */
}

.reaction-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.reaction-table th, .reaction-table td {
  padding: 12px 8px;
  border-bottom: 1px solid #eee;
  vertical-align: middle;
  word-break: break-word;
}

/* Колонки для десктопа */
.col-viz { width: 50%; }
.col-cond { width: 15%; text-align: center; font-size: 0.85rem; }
.col-yield { width: 10%; text-align: center; font-weight: bold; }
.col-ref { width: 25%; }

.reaction-container {
  width: 100%;
  background: #fff;
  border: 1px solid #f9f9f9;
  border-radius: 4px;
  display: flex;
  justify-content: center;
}

.reaction-container :deep(svg) {
  max-width: 100%;
  height: auto;
  display: block;
}

.ref-block { display: flex; flex-direction: column; gap: 8px; }
.doi-link { color: #3498db; text-decoration: none; font-size: 0.8rem; word-break: break-all; }

/* ПАГИНАЦИЯ */
.pagination { margin-top: 30px; display: flex; justify-content: center; align-items: center; gap: 20px; }
.pag-btn { padding: 8px 16px; border: 1px solid #42b983; background: white; color: #42b983; border-radius: 20px; cursor: pointer; font-weight: bold; transition: 0.3s; }
.pag-btn:hover:not(:disabled) { background: #42b983; color: white; }
.pag-btn:disabled { opacity: 0.3; cursor: not-allowed; border-color: #ccc; color: #ccc; }
.page-numbers .current { color: #42b983; font-size: 1.2rem; font-weight: bold; }

/* Кнопки оценок */
.eval-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 5px; }
.eval-btn { background: #f9f9f9; border: 1px solid #eee; border-radius: 6px; padding: 3px 8px; cursor: pointer; }

/* МОБИЛЬНАЯ АДАПТАЦИЯ (КАРТОЧКИ) */
@media (max-width: 768px) {
  .table-container { overflow-x: visible; }

  .reaction-table,
  .reaction-table thead,
  .reaction-table tbody,
  .reaction-table th,
  .reaction-table td,
  .reaction-table tr {
    display: block; /* Превращаем таблицу в набор блоков */
  }

  .reaction-table thead { display: none; } /* Скрываем заголовки */

  .reaction-table tr {
    margin-bottom: 25px;
    border: 1px solid #eee;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    background: #fff;
  }

  .reaction-table td {
    width: 100% !important; /* На весь экран */
    box-sizing: border-box;
    padding: 10px 0;
    border-bottom: 1px solid #f5f5f5;
    text-align: left !important;
  }

  .reaction-table td:last-child { border-bottom: none; }

  /* Подписи для ячеек */
  .reaction-table td::before {
    content: attr(data-label);
    font-weight: bold;
    display: block;
    font-size: 0.7rem;
    color: #999;
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  /* Реакция без подписи и первая */
  .col-viz {
    order: -1;
    border-bottom: 2px solid #eee !important;
    padding-bottom: 15px !important;
  }
  .col-viz::before { display: none; }

  .reaction-container {
    border: none;
    padding: 0;
  }
}
</style>