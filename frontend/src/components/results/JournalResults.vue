<template>
  <div class="results-section">
    <div class="header">
      <h3>Journal Base</h3>
      <span v-if="allIds.length > 0" class="stat">
        Found: {{ allIds.length }} (showing {{
          (currentPage - 1) * 10 + 1
        }}-{{ Math.min(currentPage * 10, allIds.length) }})
      </span>
    </div>

    <div v-if="loading && allIds.length === 0" class="loading">Searching...</div>

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
            <td class="col-cond" data-label="Conditions">
               {{ formatText(res.conditions) }}
            </td>
            <td class="col-yield" data-label="Yield">{{ res.yield_text || '—' }}%</td>
            <td class="col-ref" data-label="Source" @click.stop>
              <div class="ref-block">
  <div class="ref-text-wrapper">
  <span class="ref-text">{{ formatText(res.references) }}</span>

  <div class="dropdown-container">
    <button class="more-btn" @click.stop="toggleDropdown(res.id)" title="Actions">...</button>
    <div v-if="activeDropdownId === res.id" class="dropdown-menu" v-click-outside="closeDropdown">
      <div class="dropdown-info-text">{{ formatText(res.references) }}</div>
      <button class="dropdown-action-btn" @click.stop="copyToClipboard(res.references, res.id)">
        {{ copiedId === res.id ? '✓ Copied' : '📋 Copy' }}
      </button>
    </div>
  </div>
</div>

  <div class="doi-wrapper" v-if="res.doi">
    <a
      v-for="doi in parseDois(res.doi)"
      :key="doi"
      :href="'https://doi.org/' + doi"
      target="_blank"
      class="doi-link"
    >
      {{ doi }}
    </a>
  </div>
                <div class="eval-bar">
                  <button class="eval-btn check" :class="{ 'empty': !evaluations[res.external_id]?.CHECK }" @click="openEvalModal(res.external_id)">
                    <span class="icon">✅</span>
                    <span class="count">{{ evaluations[res.external_id]?.CHECK || 0 }}</span>
                  </button>

                  <button v-if="evaluations[res.external_id]?.POO > 0" class="eval-btn poo" @click="openEvalModal(res.external_id)" title="Not reproduced">
                    <span class="icon">💩</span>
                    <span class="count">{{ evaluations[res.external_id].POO }}</span>
                  </button>

                  <button v-if="evaluations[res.external_id]?.ERROR > 0" class="eval-btn error" @click="openEvalModal(res.external_id)" title="Data error">
                    <span class="icon">🛑</span>
                    <span class="count">{{ evaluations[res.external_id].ERROR }}</span>
                  </button>

                  <button class="eval-btn comments" @click="openEvalModal(res.external_id)" title="Comments">
                    <span class="icon">💬</span>
                    <span class="count">{{ commentCounts[res.external_id] || 0 }}</span>
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

    <div v-if="loading" class="loading-state">
  <div class="spinner"></div> <p>Searching in database...</p>
</div>

<div v-else-if="error" class="error-msg">
  <span class="icon">⚠️</span>
  {{ error }}
</div>

<div v-else-if="allIds.length === 0" class="empty-state">
  <div v-if="hasSearched">
    <p>No results found for this query.</p>
  </div>
  <div v-else>
    <p>Enter a query and press search to begin.</p>
  </div>
</div>
  </div>

  <EvaluationModal :isOpen="isEvalModalOpen" :entryId="selectedEntryId" target="REACTIONS" @close="isEvalModalOpen = false" @success="onEvalSuccess" />
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
const commentCounts = ref({})
const allIds = ref([])
const cachedData = ref({})
const currentPage = ref(1)
const pageSize = 10
const loading = ref(false)
const error = ref(null)
const isEvalModalOpen = ref(false)
const selectedEntryId = ref(null)
const hasSearched = ref(false)

const activeDropdownId = ref(null)
const copiedId = ref(null)

const totalPages = computed(() => Math.ceil(allIds.value.length / pageSize))
const currentResults = computed(() => cachedData.value[currentPage.value] || [])


// Кастомная директива (click-outside) чтобы закрывать меню при клике в любое другое место
const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value(event);
      }
    };
    document.addEventListener("click", el.clickOutsideEvent);
  },
  unmounted(el) {
    document.removeEventListener("click", el.clickOutsideEvent);
  },
};

// Функции управления меню и копирования в буфер
const toggleDropdown = (id) => {
  activeDropdownId.value = activeDropdownId.value === id ? null : id
}

const closeDropdown = () => {
  activeDropdownId.value = null
}

const copyToClipboard = async (text, id) => {
  if (!text) return
  try {
    const cleanText = text.replace(/<NL>/g, '\n')
    await navigator.clipboard.writeText(cleanText)
    copiedId.value = id
    setTimeout(() => {
      copiedId.value = null
      activeDropdownId.value = null
    }, 1200)
  } catch (err) {
    console.error('Failed to copy text: ', err)
  }
}

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

const fetchCommentCounts = async (ids) => {
  try {
    const params = new URLSearchParams()
    params.append('target', 'REACTIONS')
    ids.forEach(id => params.append('entry_ids', id))

    // Используем твой новый эндпоинт /batch-counts
    const response = await axios.get('/api/comments/batch-counts', { params })
    commentCounts.value = { ...commentCounts.value, ...response.data }
  } catch (err) {
    console.error("Error fetching comment counts:", err)
  }
}

const performNewSearch = async () => {
  if (!props.smiles) return
  loading.value = true
  error.value = null // Сбрасываем старую ошибку
  hasSearched.value = true // Помечаем, что попытка поиска была
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
    error.value = err.response?.data?.detail || "Search error"
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

    const data = response.data
    cachedData.value[page] = data
    currentPage.value = page

    // ВЫТАСКИВАЕМ EXTERNAL_ID
    const externalIds = data.map(r => r.external_id).filter(id => id)

    if (externalIds.length > 0) {
      await Promise.all([
        fetchEvaluations(externalIds),
        fetchCommentCounts(externalIds)
      ])
    }
  } catch (err) { error.value = "Loading error" } finally { loading.value = false }
}

// Заменяет <NL> на реальные переносы для использования в v-html или просто тексте
const formatText = (text) => {
  if (!text) return '—'
  return text.replace(/<NL>/g, '\n')
}

// Превращает строку с DOI в массив чистых ссылок
const parseDois = (doiString) => {
  if (!doiString) return []
  // Разбиваем по <NL>, пробелам или обычным переносам строк
  return doiString
    .split(/<NL>|\s|\n/)
    .map(d => d.trim())
    .filter(d => d.length > 0)
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
  overflow-x: hidden;
}

.reaction-table {
  width: 100%;
  border-collapse: collapse;
  /* УДАЛИЛИ table-layout: fixed; */
}

.reaction-table th, .reaction-table td {
  padding: 12px 10px; /* Чуть увеличили боковые отступы для читаемости */
  border-bottom: 1px solid #eee;
  vertical-align: middle;
  word-break: break-word;
}

/* ДИНАМИЧЕСКИЕ НАСТРОЙКИ КОЛОНОК (Вместо фиксированных процентов) */
.col-viz   { width: auto; min-width: 350px; max-width: 70%; } /* Растет только если схема длинная */
.col-cond  { width: 120px; text-align: left; font-size: 0.85rem; color: #555; }
.col-yield { width: 55px;  text-align: center; font-weight: bold; font-size: 0.95rem; }
.col-ref   { width: 220px; text-align: left; }

.reaction-container {
  display: inline-block; /* Позволяет ячейке схлопываться до реальной ширины SVG */
  background: #fff;
  padding: 2px 0;
}

.reaction-container :deep(svg) {
  width: auto;
  max-width: 100%; /* Позволяет схеме растянуться почти на весь экран */

  /* Поднимаем планку высоты до 180px. Теперь длинные молекулы развернутся вширь,
     а сложные/высокие циклы не будут сплющиваться в кашу */
  max-height: 180px;

  display: block;
  margin: 0; /* Выравнивание по левому краю ячейки */
}

.ref-block { display: flex; flex-direction: column; gap: 2px; }
.ref-text {
  font-size: 0.75rem;
  color: #333;
  line-height: 1.2;
  display: -webkit-box;
  -webkit-line-clamp: 4; /* Ограничиваем слишком длинные названия журналов, если они растягивают строку */
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ПАГИНАЦИЯ */
.pagination { margin-top: 25px; display: flex; justify-content: center; align-items: center; gap: 20px; }
.pag-btn { padding: 6px 14px; border: 1px solid #42b983; background: white; color: #42b983; border-radius: 20px; cursor: pointer; font-weight: bold; transition: 0.3s; }
.pag-btn:hover:not(:disabled) { background: #42b983; color: white; }
.pag-btn:disabled { opacity: 0.3; cursor: not-allowed; border-color: #ccc; color: #ccc; }
.page-numbers .current { color: #42b983; font-size: 1.1rem; font-weight: bold; }

/* Оценки */
.eval-bar { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.eval-btn { background: #f9f9f9; border: 1px solid #eee; border-radius: 5px; padding: 2px 5px; cursor: pointer; font-size: 0.7rem; }

/* МОБИЛЬНАЯ АДАПТАЦИЯ (ПЕРЕВОД В КАРТОЧКИ) */
@media (max-width: 992px) { /* Подняли брейкпоинт до 992px, так как при 75% на средних экранах тексту будет тесно */
  .table-container { overflow-x: visible; }

  .reaction-table,
  .reaction-table thead,
  .reaction-table tbody,
  .reaction-table th,
  .reaction-table td,
  .reaction-table tr {
    display: block;
  }

  .reaction-table thead { display: none; }

  .reaction-table tr {
    margin-bottom: 20px;
    border: 1px solid #eee;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 3px 8px rgba(0,0,0,0.04);
    background: #fff;
  }

  .reaction-table td {
    width: 100% !important;
    box-sizing: border-box;
    padding: 8px 0;
    border-bottom: 1px solid #f5f5f5;
    text-align: left !important;
  }

  .reaction-table td:last-child { border-bottom: none; }

  .reaction-table td::before {
    content: attr(data-label);
    font-weight: bold;
    display: block;
    font-size: 0.7rem;
    color: #999;
    text-transform: uppercase;
    margin-bottom: 3px;
  }

  .col-viz {
    order: -1;
    border-bottom: 2px solid #eee !important;
    padding-bottom: 12px !important;
  }
  .col-viz::before { display: none; }

  .reaction-container {
    border: none;
    padding: 0;
  }

  .reaction-container :deep(svg) {
    max-height: 160px;
    margin: 0 auto;
  }
}

.col-cond, .ref-text {
  white-space: pre-line;
}

.doi-wrapper {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.doi-link {
  color: #3498db;
  text-decoration: none;
  font-size: 0.7rem;
  word-break: break-all;
  display: block;
}

.doi-link:hover {
  text-decoration: underline;
}

.error-msg { color: #e74c3c; padding: 15px; text-align: center; background: #fdf2f2; border-radius: 8px; border: 1px solid #facccc; margin: 10px 0; }
.loading-state, .empty-state { text-align: center; padding: 30px; color: #666; }

/* Позиционируем троеточие поверх текста в конце третьей строки */
.ref-text-wrapper {
  position: relative;
  display: block;
  width: 100%;
  padding-right: 20px; /* Делаем небольшой отступ справа под кнопку */
  box-sizing: border-box;
}

.ref-text {
  font-size: 0.8rem;
  color: #333;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 3; /* Надежно режем до 3 строк */
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Контейнер кнопки прижимаем к правому нижнему углу текстового блока */
.dropdown-container {
  position: absolute;
  right: 2px;
  bottom: 0px;
  background: white; /* Перекрываем родной текст ссылки под кнопкой */
  padding-left: 4px;
}

.more-btn {
  background: none;
  border: none;
  color: #3498db;
  font-size: 0.9rem;
  font-weight: bold;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
  border-radius: 3px;
}
.more-btn:hover { background: #e8f4fd; }

/* Всплывающее меню теперь вылетает наружу и не режется */
.dropdown-menu {
  position: absolute;
  right: 0;
  bottom: 20px; /* Открывается вверх над кнопкой, чтобы не перекрывать нижние строки/оценки */
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 110;
  width: 220px;
  padding: 10px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.dropdown-info-text {
  display: block;
  font-size: 0.75rem;
  color: #444;
  max-height: 100px;
  overflow-y: auto;
  white-space: pre-wrap;
  margin-bottom: 8px;
  line-height: 1.3;
  border-bottom: 1px solid #eee;
  padding-bottom: 6px;
  text-align: left;
}

.dropdown-action-btn {
  align-self: center;
  background: #42b983;
  color: white;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: bold;
  white-space: nowrap;
}
.dropdown-action-btn:hover { background: #3aa876; }
</style>