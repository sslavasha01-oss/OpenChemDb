<template>
  <div class="results-section">
    <div class="header">
      <h3>Book Base</h3>
      <span v-if="allIds && allIds.length > 0" class="stat">
        Найдено: {{ allIds.length }} (показано {{
          (currentPage - 1) * 10 + 1
        }}-{{ Math.min(currentPage * 10, allIds.length) }})
      </span>
    </div>

    <div v-if="loading && allIds.length === 0" class="loading">Поиск в книгах...</div>

    <div v-if="allIds && allIds.length > 0">
      <div class="table-container">
        <table class="reaction-table">
          <thead>
            <tr>
              <th class="col-viz">Molecule</th>
              <th class="col-book">Book Name</th>
              <th class="col-pages">Pages</th>
              <th class="col-ref">References</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="res in currentResults" :key="res.id" class="reaction-row" @click="showDetails(res)">
              <td class="col-viz">
                <div class="reaction-container" v-html="res.svg_content"></div>
              </td>
              <td class="col-book" data-label="Book" @click.stop="openFileModal(res.book_name)">
                <a href="#" class="book-link" @click.prevent>{{ getShortName(res.book_name) }}</a>
              </td>
              <td class="col-pages" data-label="Pages">
  <div class="pages-list">
    <div v-for="(page, index) in parsePages(res.pages)" :key="index" class="page-item">
      <a
        :href="'/api/files/view?file_path=' + encodeURIComponent(page.fullPath)"
        target="_blank"
        class="page-link"
        @click.stop
      >
        {{ page.fileName }}
      </a>
    </div>
    <span v-if="!res.pages">—</span>
  </div>
</td>
              <td class="col-ref" data-label="Source" @click.stop>
                <div class="ref-block">
                  <span class="ref-text">{{ formatText(res.references) }}</span>
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
        <button :disabled="currentPage === 1" @click="fetchPageData(currentPage - 1)" class="pag-btn">← Prev</button>
        <div class="page-numbers"><span class="current">{{ currentPage }}</span> / {{ totalPages }}</div>
        <button :disabled="currentPage === totalPages" @click="fetchPageData(currentPage + 1)" class="pag-btn">Next →</button>
      </div>
    </div>

    <div v-else-if="!loading" class="no-results">В книжной базе ничего не найдено</div>
  </div>

  <div v-if="isFileModalOpen" class="modal-overlay" @click="isFileModalOpen = false">
    <div class="modal-content file-list-modal" @click.stop>
      <div class="modal-header">
        <h3>Files in: {{ getShortName(currentBookPath) }}</h3>
        <button @click="isFileModalOpen = false" class="btn-close">Close</button>
      </div>
      <div class="modal-body">
        <div v-if="loadingFiles" class="loading">Loading files...</div>
        <ul v-else class="file-list">
          <li v-for="file in fileList" :key="file">
            <span class="file-icon">📄</span>
            <a :href="'/api/files/view?file_path=' + encodeURIComponent(file)" target="_blank" class="file-link">
              {{ getFileName(file) }}
            </a>
          </li>
        </ul>
      </div>
    </div>
  </div>
<BookDetailsModal
  :isOpen="isDetailsOpen"
  :item="selectedReaction"
  @close="isDetailsOpen = false"
  @open-book-files="openFileModal"
/>
<EvaluationModal
  :isOpen="isEvalModalOpen"
  :entryId="selectedEntryId"
  target="BOOKS"
  @close="isEvalModalOpen = false"
  @success="onEvalSuccess"
/>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import EvaluationModal from '@/components/modals/EvaluationModal.vue'
import BookDetailsModal from '@/components/modals/BookDetailsModal.vue'

const props = defineProps({
  smiles: String,
  exact: Boolean,
  mode: String
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

const totalPages = computed(() => Math.ceil(allIds.value.length / pageSize))
const currentResults = computed(() => cachedData.value[currentPage.value] || [])

// Состояние для файлов
const isFileModalOpen = ref(false)
const fileList = ref([])
const loadingFiles = ref(false)
const currentBookPath = ref('')

// Хелпер: обрезает SOP/ и длинные пути до названия папки/книги
const getShortName = (path) => {
  if (!path) return '—'
  const parts = path.split('/')
  return parts[parts.length - 1] // Берем только последний элемент
}

// Хелпер: вытаскивает только имя файла из полного пути
const getFileName = (path) => {
  if (!path) return 'file'
  return path.split('/').pop()
}

const parsePages = (pagesRaw) => {
  if (!pagesRaw) return []

  return pagesRaw
    .toString()
    // 1. Заменяем артефакт <NL> на реальный перенос строки
    .replace(/<NL>/g, '\n')
    // 2. Разбиваем по переносу строки (любому: \n или \r\n)
    .split(/\r?\n/)
    // 3. Убираем пустые строки и лишние пробелы по краям
    .filter(p => p.trim() !== '')
    .map(path => {
      const cleanPath = path.trim()
      return {
        fullPath: cleanPath,
        // Вытаскиваем имя файла, поддерживаем и / и \ на всякий случай
        fileName: cleanPath.split(/[\\/]/).pop()
      }
    })
}

// Загрузка списка файлов
const openFileModal = async (dirPath) => {
  if (!dirPath) return
  currentBookPath.value = dirPath
  isFileModalOpen.value = true
  loadingFiles.value = true
  fileList.value = []

  try {
    const response = await axios.get('/api/files/list', {
      params: { dir_path: dirPath }
    })
    fileList.value = response.data
  } catch (err) {
    console.error("Error loading files:", err)
  } finally {
    loadingFiles.value = false
  }
}

const showDetails = (item) => {
  selectedReaction.value = item
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
    params.append('target', 'BOOKS')
    ids.forEach(id => params.append('entry_ids', id))
    const response = await axios.get('/api/evaluations/batch', {params})
    evaluations.value = {...evaluations.value, ...response.data}
  } catch (err) { console.error(err) }
}

const fetchCommentCounts = async (ids) => {
  try {
    const params = new URLSearchParams()
    params.append('target', 'BOOKS')
    ids.forEach(id => params.append('entry_ids', id))
    const response = await axios.get('/api/comments/batch-counts', { params })
    commentCounts.value = { ...commentCounts.value, ...response.data }
  } catch (err) { console.error(err) }
}

const performNewSearch = async () => {
  if (!props.smiles) return
  loading.value = true
  allIds.value = []
  cachedData.value = {}
  currentPage.value = 1

    let cleanQuery = props.smiles
  if (cleanQuery.includes('>>')) {
    const parts = cleanQuery.split('>>')
    // Берем правую часть. Если там пусто (например "CC>>"),
    // можно либо ничего не искать, либо брать левую часть.
    // Но обычно поиск молекул в БД идет по продукту.
    cleanQuery = parts[1] && parts[1].trim() !== '' ? parts[1] : parts[0]
  }
  cleanQuery = cleanQuery.trim()

  // Если после очистки строка пустая — выходим
  if (!cleanQuery) {
    loading.value = false
    return
  }

    console.log(cleanQuery)

  // Эндпоинты книжной базы
  const searchUrl = props.mode === 'advanced'
    ? '/api/books/search/ids/smarts'
    : '/api/books/search/ids'

  try {
    const response = await axios.get(searchUrl, {
      params: {
        [props.mode === 'advanced' ? 'smarts' : 'smiles']: cleanQuery,
        exact: props.exact
      }
    })
    allIds.value = response.data.ids
    if (allIds.value.length > 0) await fetchPageData(1)
  } catch (err) {
    error.value = "Ошибка поиска в книгах"
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
    const response = await axios.get('/api/books/search/by-ids', {
      params: {ids: idsToFetch},
      paramsSerializer: {indexes: null}
    })

    const data = response.data // Сохраняем полученные данные
    cachedData.value[page] = data
    currentPage.value = page

    // ВЫТАСКИВАЕМ EXTERNAL_ID (как в Journal)
    const externalIds = data.map(r => r.external_id).filter(id => id)

    if (externalIds.length > 0) {
      await Promise.all([
        fetchEvaluations(externalIds), // Теперь передаем внешние ID
        fetchCommentCounts(externalIds) // Теперь передаем внешние ID
      ])
    }
  } catch (err) {
    error.value = "Ошибка загрузки данных"
  } finally {
    loading.value = false
  }
}

const formatText = (text) => {
  if (!text) return '—'
  return text.replace(/<NL>/g, '\n')
}

defineExpose({performNewSearch})
</script>

<style scoped>
/* Стили полностью идентичны JournalResults для однообразия */
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

.table-container { width: 100%; overflow-x: hidden; }

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

/* Колонки */
.col-viz { width: 35%; }
.col-book { width: 25%; text-align: left; font-weight: bold; }
.col-pages { width: 10%; text-align: center; }
.col-ref { width: 30%; }

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
.ref-text { font-size: 0.9rem; white-space: pre-line; }

/* ПАГИНАЦИЯ */
.pagination { margin-top: 30px; display: flex; justify-content: center; align-items: center; gap: 20px; }
.pag-btn { padding: 8px 16px; border: 1px solid #42b983; background: white; color: #42b983; border-radius: 20px; cursor: pointer; font-weight: bold; transition: 0.3s; }
.pag-btn:hover:not(:disabled) { background: #42b983; color: white; }
.pag-btn:disabled { opacity: 0.3; cursor: not-allowed; border-color: #ccc; color: #ccc; }
.page-numbers .current { color: #42b983; font-size: 1.2rem; font-weight: bold; }

/* Кнопки оценок */
.eval-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 5px; }
.eval-btn { background: #f9f9f9; border: 1px solid #eee; border-radius: 6px; padding: 3px 8px; cursor: pointer; display: flex; align-items: center; gap: 4px; }
.eval-btn.check .icon { color: #42b983; }

/* Адаптация под мобильные (карточки) */
@media (max-width: 768px) {
  .table-container { overflow-x: visible; }
  .reaction-table, .reaction-table thead, .reaction-table tbody, .reaction-table th, .reaction-table td, .reaction-table tr {
    display: block;
  }
  .reaction-table thead { display: none; }
  .reaction-table tr {
    margin-bottom: 25px;
    border: 1px solid #eee;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    background: #fff;
  }
  .reaction-table td {
    width: 100% !important;
    box-sizing: border-box;
    padding: 10px 0;
    border-bottom: 1px solid #f5f5f5;
    text-align: left !important;
  }
  .reaction-table td::before {
    content: attr(data-label);
    font-weight: bold;
    display: block;
    font-size: 0.7rem;
    color: #999;
    text-transform: uppercase;
    margin-bottom: 4px;
  }
  .col-viz { order: -1; border-bottom: 2px solid #eee !important; padding-bottom: 15px !important; }
  .col-viz::before { display: none; }
}

.book-link {
  color: #42b983;
  text-decoration: none;
  font-weight: bold;
  border-bottom: 1px dashed #42b983;
}
.book-link:hover {
  color: #33a06f;
  border-bottom-style: solid;
}

/* Стили для модалки файлов */
.file-list-modal {
  max-width: 600px !important;
  height: auto !important;
  max-height: 70vh;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.file-list li {
  padding: 10px;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-list li:last-child {
  border-bottom: none;
}

.file-link {
  color: #2c3e50;
  text-decoration: none;
  font-size: 1rem;
}

.file-link:hover {
  color: #42b983;
  text-decoration: underline;
}

.file-icon {
  font-size: 1.2rem;
}

.pages-text {
  white-space: pre-line; /* Чтобы <NL> превращенные в \n переносились корректно */
  font-size: 0.85rem;
}

/* Фиксируем оверлей на весь экран */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.7); /* Затемнение фона */
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10005; /* Чтобы была поверх всего, включая хедеры */
}

/* Контейнер самой модалки */
.modal-content.file-list-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
}

/* Шапка внутри модалки */
.modal-header {
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

/* Кнопка закрытия */
.btn-close {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-close:hover {
  background: #c0392b;
}

.pages-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 100px; /* Ограничим высоту, если страниц слишком много */
  overflow-y: auto;  /* Добавим внутренний скролл, если список гигантский */
  font-size: 0.85rem;
}

.page-item {
  white-space: nowrap;
}

.page-link {
  color: #3498db;
  text-decoration: none;
  border-bottom: 1px transparent dashed;
  transition: all 0.2s;
}

.page-link:hover {
  color: #2980b9;
  border-bottom-color: #2980b9;
}

/* Стили для скроллбара внутри списка страниц, чтобы выглядело аккуратно */
.pages-list::-webkit-scrollbar {
  width: 4px;
}
.pages-list::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 10px;
}
</style>