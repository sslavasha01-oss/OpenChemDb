<template>
  <div class="journal-container">
    <!-- Навигация по вкладкам -->
    <nav class="tabs-nav">
      <button :class="{ active: activeTab === 'table' }" :disabled="isGuest" @click="activeTab = 'table'">Table</button>
      <button :class="{ active: activeTab === 'method' }" @click="activeTab = 'method'">Method</button>
      <button :class="{ active: activeTab === 'search' }" :disabled="isGuest" @click="activeTab = 'search'">Search</button>
    </nav>

  <div class="header-controls">
      <div v-if="!isGuest && activeTab !== 'search'" class="global-record-nav">
        <button @click="goToFirstRecord" :disabled="isEditing || loading" class="nav-arrow" title="First record">|←</button>
        <button @click="navigateRecord(-1)" :disabled="isEditing" class="nav-arrow">←</button>
        <span class="selected-id-display">
          Record: {{ journalData?.external_id ? '#' + journalData.external_id : '---' }}
        </span>
        <button @click="navigateRecord(1)" :disabled="isEditing" class="nav-arrow">→</button>
        <button @click="goToLastRecord" :disabled="isEditing || loading" class="nav-arrow" title="Last record">→|</button>
      </div>

      <template v-if="!isGuest">
        <button
          v-if="activeTab === 'table' || activeTab === 'method'"
          class="btn-add-main"
          @click="initNewEntryFromTable"
        >
          <span class="icon">+</span> New Entry
        </button>



        <button
          v-if="activeTab === 'method'"
          :class="isEditing ? 'btn-cancel-main' : 'btn-edit-main'"
          @click="handleEditToggle"
        >
          {{ isEditing ? 'Cancel' : 'Edit' }}
        </button>

        <button
          v-if="activeTab === 'method' && isEditing"
          class="btn-save"
          @click="saveEntry"
          :disabled="loading"
        >
          {{ loading ? 'Saving...' : 'Save' }}
        </button>

        <button
          v-if="activeTab === 'method' && journalData?.external_id"
          class="btn-delete-main"
          :disabled="isEditing || loading"
          @click="deleteEntry"
        >
          Delete
        </button>

        <div v-if="activeTab === 'table' || activeTab === 'method'" class="header-right-group">
          <!-- Кнопки для таблицы -->
          <template v-if="activeTab === 'table'">
            <button
              :class="isSelectionMode ? 'btn-cancel-main' : 'btn-edit-main'"
              @click="isSelectionMode = !isSelectionMode"
            >
              {{ isSelectionMode ? 'Cancel Selection' : 'Select Records' }}
            </button>
            <button class="btn-edit-main" @click="showExportModal = true">Export</button>
            <button class="btn-edit-main" @click="showImportModal = true">Import</button>
          </template>

          <!-- Кнопка PDF для методики -->
          <button
            v-if="activeTab === 'method' && journalData?.id"
            class="btn-edit-main"
            @click="exportToPDF"
            title="Print to PDF"
          >
            <span style="margin-right: 5px;">🖨️</span> PDF
          </button>
        </div>
      </template>

      <template v-else>
        <button class="btn-cancel-main" @click="journalData = createEmptyEntry()">
          Clear Calculator
        </button>
      </template>
    </div>

    <main class="tab-content">
        <section v-show="activeTab === 'table' && !isGuest">
        <div class="table-actions">
          <button class="btn-add-main" @click="initNewEntryFromTable">
            <span class="icon">+</span> Add new entry to journal
          </button>
        </div>

        <JournalTable
         ref="tableRef"
         :selected-id="selectedRecordId"
         :is-selection-mode="isSelectionMode"
         @select-record="handleTableSelect"
         @update:selected-export-ids="val => selectedExportIds = val"
         />
      </section>

      <!-- Вкладка Методика -->
      <section v-show="activeTab === 'method'" class="method-page">

        <div v-if="isGuest" class="guest-alert-banner">
          <span class="banner-icon">⚗️</span>
          <p class="banner-text">
            <strong>Calculator Mode:</strong> Here you can calculate the stoichiometry of a chemical reaction.
          To keep a complete lab journal, save history, and search by structures, please
          <router-link to="/login" class="banner-link">log into the system</router-link>.
          </p>
        </div>

        <div class="product-row">
          <ProductCard
            ref="productCardRef"
            v-model="journalData"
            :isEditing="isEditing"
          />
        </div>

        <div class="reagents-container">
           <div class="reagents-grid">
             <ReagentCard
               v-for="i in 5"
               :key="i"
               :index="i"
               :ref="el => { if (el) reagentCardRefs[i-1] = el }"
               v-model="journalData"
               :isEditing="isEditing"
               v-show="(isEditing && i <= visibleReagentsCount) || (!isEditing && journalData[`reagent${i}_smiles`]) || i === 1"
             />

             <button
               v-if="isEditing && visibleReagentsCount < 5"
               class="add-reagent-card"
               @click="addReagent"
             >
               <span class="plus-icon">+</span>
               Add Reagent
             </button>
           </div>
        </div>

        <div class="procedure-section">
          <h3>Method</h3>
          <textarea
            ref="procedureRef"
            v-model="journalData.procedure"
            :disabled="!isEditing"
            rows="1"
            @input="e => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px' }"
            placeholder="Describe the synthesis procedure..."
          ></textarea>

          <div class="extra-fields-row">
            <div class="field-group">
              <label>References</label>
              <input
                type="text"
                v-model="journalData.references"
                :disabled="!isEditing"
                placeholder="Author, Journal, Year..."
              >
            </div>
            <div class="field-group">
              <label>DOI</label>
              <input
                type="text"
                v-model="journalData.doi"
                :disabled="!isEditing"
                placeholder="10.1021/..."
              >
            </div>
          </div>
        </div>
        <!-- Секция Аттачментов -->
        <div v-if="!isGuest && (journalData.id || isEditing)" class="attachments-section">

          <!-- Блок Статей -->
          <div class="attachment-block">
            <h3>Articles / Links</h3>
            <div
  class="drop-zone"
  :class="{ 'drop-active': isEditing, 'clickable': isEditing }"
  @dragover.prevent
  @drop.prevent="onDrop($event, 'ARTICLE')"
  @click="triggerUploadOnZone($event, articleInput)"
>
  <input type="file" ref="articleInput" hidden multiple @change="e => handleFilesAdded(e.target.files, 'ARTICLE')">
              <table class="attachment-table">
                <thead>
                  <tr>
                    <th>Link / File</th>
                    <th>Description</th>
                    <th v-if="isEditing" style="width: 80px;">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <!-- Сохраненные -->
                  <tr v-for="file in currentAttachments.ARTICLE" :key="file.id">
                    <td><a href="#" @click.prevent="viewAttachment(file)" class="att-link">📄 {{ file.file_path.split('/').pop() }}</a></td>
                    <td>
                      <input v-if="isEditing" v-model="file.description" @input="file._isDirty = true" class="desc-edit-input" placeholder="Add description...">
                      <span v-else>{{ file.description || 'No description' }}</span>
                    </td>
                    <td class="att-actions">
                      <button class="btn-att-save" title="Download" @click="downloadAttachment(file)">📥</button>
                      <button v-if="isEditing" class="btn-att-delete" title="Delete" @click="removeAttachment(file, 'ARTICLE')">🗑️</button>
                    </td>
                  </tr>
                  <!-- В очереди (для новых записей) -->
                  <tr v-for="(item, idx) in pendingAttachments.filter(a => a.type === 'ARTICLE')" :key="'p'+idx" class="pending-row">
                    <td><span class="att-link">⏳ {{ item.previewName }}</span></td>
                    <td><input v-model="item.description" class="desc-edit-input" placeholder="Add description..."></td>
                    <td class="att-actions">
                      <button class="btn-att-delete" title="Remove" @click="removeAttachment(item, 'ARTICLE', idx)">✕</button>
                    </td>
                  </tr>
                  <tr v-if="currentAttachments.ARTICLE.length === 0 && !pendingAttachments.some(a => a.type === 'ARTICLE')">
                    <td :colspan="isEditing ? 3 : 2" class="empty-text">{{ isEditing ? 'Drag & Drop files here' : 'No articles attached' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-if="isEditing" class="upload-hint">Drag & Drop or click to upload</div>
              </div>
          </div>

          <!-- Блок Спектров -->
          <div class="attachment-block">
            <h3>Spectra</h3>
            <div
  class="drop-zone"
  :class="{ 'drop-active': isEditing, 'clickable': isEditing }"
  @dragover.prevent
  @drop.prevent="onDrop($event, 'SPECTRUM')"
  @click="triggerUploadOnZone($event, spectrumInput)"ь
>
  <input type="file" ref="spectrumInput" hidden multiple @change="e => handleFilesAdded(e.target.files, 'SPECTRUM')">
              <table class="attachment-table">
                <thead>
                  <tr>
                    <th>Link / File</th>
                    <th>Description</th>
                    <th v-if="isEditing" style="width: 80px;">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <!-- Сохраненные -->
                  <tr v-for="file in currentAttachments.SPECTRUM" :key="file.id">
                    <td><a href="#" @click.prevent="viewAttachment(file)" class="att-link">📊 {{ file.file_path.split('/').pop() }}</a></td>
                    <td>
                      <input v-if="isEditing" v-model="file.description" @input="file._isDirty = true" class="desc-edit-input" placeholder="Add description...">
                      <span v-else>{{ file.description || 'No description' }}</span>
                    </td>
                    <td class="att-actions">
                       <button class="btn-att-save" title="Download" @click="downloadAttachment(file)">📥</button>
                       <button v-if="isEditing" class="btn-att-delete" title="Delete" @click="removeAttachment(file, 'SPECTRUM')">🗑️</button>
                    </td>
                  </tr>
                  <!-- В очереди (для новых записей) -->
                  <tr v-for="(item, idx) in pendingAttachments.filter(a => a.type === 'SPECTRUM')" :key="'p'+idx" class="pending-row">
                    <td><span class="att-link">⏳ {{ item.previewName }}</span></td>
                    <td><input v-model="item.description" class="desc-edit-input" placeholder="Add description..."></td>
                    <td class="att-actions">
                      <button class="btn-att-delete" title="Remove" @click="removeAttachment(item, 'SPECTRUM', idx)">✕</button>
                    </td>
                  </tr>
                  <tr v-if="currentAttachments.SPECTRUM.length === 0 && !pendingAttachments.some(a => a.type === 'SPECTRUM')">
                    <td :colspan="isEditing ? 3 : 2" class="empty-text">{{ isEditing ? 'Drag & Drop files here' : 'No spectra attached' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-if="isEditing" class="upload-hint">Drag & Drop or click to upload</div>
            </div>
          </div>

          <!-- Блок Медиа (Фото/Видео) -->
<div class="attachment-block media-full-width">
  <h3>Media (Photos / Videos)</h3>
  <div
  class="drop-zone"
  :class="{ 'drop-active': isEditing, 'clickable': isEditing }"
  @dragover.prevent
  @drop.prevent="onDrop($event, 'MEDIA')"
  @click="triggerUploadOnZone($event, mediaInput)"
>
  <input type="file" ref="mediaInput" hidden multiple accept="image/*,video/*" @change="e => handleFilesAdded(e.target.files, 'MEDIA')">
    <div class="media-grid">
      <!-- Сохраненные медиа -->
      <div v-for="file in currentAttachments.MEDIA" :key="file.id" class="media-card">
        <div class="media-preview" @click="viewAttachment(file)">
          <img v-if="file.thumbnail_b64" :src="'data:image/png;base64,' + file.thumbnail_b64" alt="preview">
          <div v-else class="media-placeholder">🎬</div>
          <div class="media-overlay-actions">
            <button class="btn-mini" title="Download" @click.stop="downloadAttachment(file)">📥</button>
          </div>
        </div>
        <div class="media-info">
          <textarea
            v-if="isEditing"
            v-model="file.description"
            @input="file._isDirty = true"
            class="media-desc-edit"
            placeholder="Description..."
          ></textarea>
          <p v-else class="media-desc-text">{{ file.description || 'No description' }}</p>
          <div v-if="isEditing" class="media-card-controls">
             <button class="btn-att-delete" @click="removeAttachment(file, 'MEDIA')">🗑️ Delete</button>
          </div>
        </div>
      </div>

      <!-- В очереди (новые) -->
      <div v-for="(item, idx) in pendingAttachments.filter(a => a.type === 'MEDIA')" :key="'pm'+idx" class="media-card pending">
        <div class="media-preview">
          <div class="media-placeholder">⏳</div>
        </div>
        <div class="media-info">
          <textarea v-model="item.description" class="media-desc-edit" placeholder="Add description..."></textarea>
          <button class="btn-att-delete" @click="removeAttachment(item, 'MEDIA', idx)">✕ Remove</button>
        </div>
      </div>

      <!-- Пустое состояние -->
      <div v-if="currentAttachments.MEDIA.length === 0 && !pendingAttachments.some(a => a.type === 'MEDIA')" class="media-empty">
        {{ isEditing ? 'Drag & Drop media files here' : 'No media attached' }}
      </div>
    </div>
    <div v-if="isEditing" class="upload-hint">Drag & Drop or click to upload photos/videos</div>
  </div>
</div>
        </div>

      </section>

      <!-- Вкладка Поиск -->
      <section v-if="activeTab === 'search'" class="search-page">
        <div class="search-actions-row" style="display: flex; justify-content: flex-end; margin-top: 10px; margin-bottom: 15px;">
          <div class="actions-group" style="display: flex; align-items: center; gap: 20px;">

            <label class="exact-match-label" style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: bold; color: #2c3e50; user-select: none;">
              <input
                type="checkbox"
                v-model="searchState.exact_match"
                style="width: 18px; height: 18px; cursor: pointer; margin: 0;"
              >
              Exact match
            </label>

            <button class="btn-add-main" @click="handleSubstructureSearch">
              <span class="icon">🔍</span> Run substructure search
            </button>

          </div>
        </div>

        <div class="search-zones-grid">
          <!-- Окно искомого продукта -->
          <div class="card search-card">
            <div class="card-header">Reaction Product</div>
            <div class="card-body">
              <div class="structure-zone editable-zone" @click="openSearchEditor('product')">
                <div v-if="!searchState.product_svg" class="placeholder">
                  <span class="icon">🧪</span>
                  <p>Click to draw product</p>
                </div>
                <div v-else class="svg-render" v-html="isolatedSearchProductSvg"></div>
              </div>
              <div class="fields-zone">
                <div class="field-group">
                  <label>Product SMILES</label>
                  <input
                    type="text"
                    :value="searchState.product_smiles"
                    @input="e => onSearchSmilesInput('product', e)"
                    placeholder="CC(=O)OC1=CC=CC=C1C(=O)O..."
                    class="smiles-compact-input"
                  >
                </div>
              </div>
            </div>
          </div>
          <!-- Окно исходного реагента -->
          <div class="card search-card">
            <div class="card-header">Reagent (Starting Material)</div>
            <div class="card-body">
              <div class="structure-zone editable-zone" @click="openSearchEditor('reagent')">
                <div v-if="!searchState.reagent_svg" class="placeholder">
                  <span class="icon">🔍</span>
                  <p>Click to draw reagent</p>
                </div>
                <div v-else class="svg-render" v-html="isolatedSearchReagentSvg"></div>
              </div>
              <div class="fields-zone">
                <div class="field-group">
                  <label>Starting Material SMILES</label>
                  <input
                    type="text"
                    :value="searchState.reagent_smiles"
                    @input="e => onSearchSmilesInput('reagent', e)"
                    placeholder="C1=CC=CC=C1..."
                    class="smiles-compact-input"
                  >
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- Модальное окно редактора Кетчер для вкладки поиска -->
        <div v-show="showSearchKetcher" class="modal-overlay" style="z-index: 2000;">
          <div class="modal-content">
            <div class="modal-header">
              <h3>Edit search structure ({{ currentSearchTarget === 'reagent' ? 'Реагент' : 'Продукт' }})</h3>
              <div class="modal-btns">
                <button @click="saveFromSearchKetcher" class="btn-apply">Apply</button>
                <button @click="closeSearchEditorWithoutSaving" class="btn-cancel">Cancel</button>
              </div>
            </div>
            <div id="search-ketcher-placeholder" class="ketcher-frame" style="background: transparent;"></div>
          </div>
        </div>
      </section>
    </main>
    <ExportModal
      v-if="showExportModal"
      :selected-ids="selectedExportIds"
      @close="showExportModal = false"
      />
    <ImportModal v-if="showImportModal" @close="showImportModal = false" />
  </div>

</template>

<script setup>
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import axios from 'axios'
import ProductCard from '@/components/ProductCard.vue'
import ReagentCard from '@/components/ReagentCard.vue'
import JournalTable from '@/components/JournalTable.vue'
import { useUserStore } from '@/stores/user'
import ExportModal from '@/components/modals/ExportModal.vue'
import ImportModal from '@/components/modals/ImportModal.vue'
import { generateJournalPdf } from '@/utils/journalPdfExport'

// Импортируем наши новые хуки
import { useJournalCalculator } from '@/composables/useJournalCalculator'
import { useJournalKetcher } from '@/composables/useJournalKetcher'

const isSelectionMode = ref(false)
const selectedExportIds = ref([])

const userStore = useUserStore()
const isGuest = computed(() => !userStore.isLoggedIn)

// Подключаем логику калькулятора структур
const { journalData, createEmptyEntry, getCleanDataForApi } = useJournalCalculator()

// DOM элементы и ссылки на дочерние компоненты
const tableRef = ref(null)
const productCardRef = ref(null)
const reagentCardRefs = ref([])
const globalKetcherFrame = ref(null)

const showExportModal = ref(false)
const showImportModal = ref(false)

// Подключаем логику работы с Ketcher движком
const { isKetcherInjected, triggerKetcherRedraw } = useJournalKetcher(globalKetcherFrame, journalData)

// Управление состоянием UI
const _isEditingInternal = ref(false)
const isEditing = computed({
  get: () => isGuest.value ? true : _isEditingInternal.value,
  set: (val) => { _isEditingInternal.value = val }
})

const procedureRef = ref(null)

const adjustHeight = () => {
  nextTick(() => {
    const el = procedureRef.value
    if (el) {
      el.style.height = 'auto'
      el.style.height = el.scrollHeight + 'px'
    }
  })
}

// Следим за изменением текста (при загрузке записи или вводе)
watch(() => journalData.value.procedure, () => {
  adjustHeight()
})


const activeTab = ref(isGuest.value ? 'method' : 'table')
const loading = ref(false)
const visibleReagentsCount = ref(3)
const selectedRecordId = ref(null)
const journalDataBackup = ref(null)

// Хранилище аттачментов в формате { recordId: { ARTICLE: [], SPECTRUM: [] } }
const attachmentsMap = ref({})

const pendingAttachments = ref([]) // Для новых записей: [{ file, type, description }]
const isUploading = ref(false)

const articleInput = ref(null)
const spectrumInput = ref(null)
const mediaInput = ref(null)

const exportToPDF = async () => {
  try {
    loading.value = true;
    await generateJournalPdf(journalData.value);
  } catch (err) {
    console.error("PDF Export failed:", err);
    alert("Could not generate PDF. Please check the console.");
  } finally {
    loading.value = false;
  }
};

const triggerUploadOnZone = (event, inputRef) => {
  if (!isEditing.value || !inputRef) return

  // Проверяем, на что именно нажал пользователь
  const target = event.target
  const isInteractive =
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.tagName === 'A' ||
    target.tagName === 'BUTTON' ||
    target.closest('button') ||
    target.closest('a')

  // Если нажали на интерактивный элемент — ничего не делаем, пусть работают их родные обработчики
  if (isInteractive) return

  // Иначе — открываем выбор файлов
  inputRef.click()
}

// Функция непосредственной загрузки на сервер (для существующих записей)
const uploadFileToServer = async (recordId, file, type, description = '') => {
  const formData = new FormData()
  formData.append('journal_record_id', recordId)
  formData.append('attachment_type', type)
  formData.append('file', file)
  formData.append('description', description)

  const token = localStorage.getItem('token')
  const response = await axios.post('/api/journal_attachment/upload', formData, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

// Обработка выбора файлов (через input или drop)
const handleFilesAdded = async (files, type) => {
  const recordId = journalData.value.id

  for (const file of Array.from(files)) {
    if (recordId) {
      // РЕЖИМ 1: Запись уже существует - грузим сразу
      try {
        const newAtt = await uploadFileToServer(recordId, file, type)
        // Локально обновляем кеш, чтобы пользователь сразу увидел файл
        if (!attachmentsMap.value[recordId]) {
          attachmentsMap.value[recordId] = { ARTICLE: [], SPECTRUM: [] }
        }
        attachmentsMap.value[recordId][type].push(newAtt)
      } catch (err) {
        alert(`Failed to upload ${file.name}`)
      }
    } else {
      // РЕЖИМ 2: Новая запись - добавляем в очередь
      pendingAttachments.value.push({
        file,
        type,
        description: '',
        previewName: file.name // Для отображения в таблице до загрузки
      })
    }
  }
}

// Обновление описания на сервере
const updateAttachmentDescription = async (file, type) => {
  try {
    const token = localStorage.getItem('token')
    await axios.patch(`/api/journal_attachment/${file.id}`,
      { description: file.description },
      { headers: { 'Authorization': `Bearer ${token}` } }
    )
  } catch (err) {
    console.error("Error updating description:", err)
    alert("Failed to update description.")
  }
}

// Удаление аттачмента (и локально, и с сервера)
const removeAttachment = async (file, type, index) => {
  // 1. Если это временный файл (еще не на сервере)
  if (!file.id) {
    const realIndex = pendingAttachments.value.findIndex(a => a === file)
    if (realIndex !== -1) pendingAttachments.value.splice(realIndex, 1)
    return
  }

  // 2. Если файл на сервере
  if (!confirm("Are you sure you want to delete this attachment?")) return

  try {
    const token = localStorage.getItem('token')
    await axios.delete(`/api/journal_attachment/${file.id}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    // Удаляем из локального кеша
    const recordId = journalData.value.id
    if (attachmentsMap.value[recordId]) {
      attachmentsMap.value[recordId][type] = attachmentsMap.value[recordId][type].filter(a => a.id !== file.id)
    }
  } catch (err) {
    console.error("Error deleting attachment:", err)
    alert("Failed to delete attachment.")
  }
}

const handleFileAction = async (file, disposition) => {
  if (!file.file_path) return
  try {
    const token = localStorage.getItem('token')

    // ШАГ 1: Получаем URL от бэкенда (как и раньше)
    const res = await axios.get('/api/journal_attachment/get-download-url', {
      params: { file_path: file.file_path, disposition },
      headers: { 'Authorization': `Bearer ${token}` }
    })

    const targetUrl = res.data.url

    // ШАГ 2: Ключевое изменение. Проверяем саму ссылку, а не флаг в сторе.
    // Если ссылка ведет на облако (начинается с http), работаем как с архивом.
    if (targetUrl.startsWith('http')) {
      // ОБЛАЧНЫЙ РЕЖИМ: Просто открываем ссылку в новой вкладке.
      // Бэкенд уже подписал URL и добавил туда нужный disposition.
      // Браузер сам решит: открыть PDF (inline) или скачать (attachment).
      window.open(targetUrl, '_blank')
    } else {
      // ЛОКАЛЬНЫЙ РЕЖИМ: Оставляем как есть, так как для локального API нужен Bearer Token
      const fileResponse = await axios.get(targetUrl, {
        headers: { 'Authorization': `Bearer ${token}` },
        responseType: 'blob'
      })

      const blob = new Blob([fileResponse.data], { type: fileResponse.headers['content-type'] })
      const blobUrl = window.URL.createObjectURL(blob)

      if (disposition === 'inline') {
        window.open(blobUrl, '_blank')
      } else {
        const link = document.createElement('a')
        link.href = blobUrl
        link.setAttribute('download', file.file_path.split('/').pop())
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60000)
    }
  } catch (err) {
    console.error("Action failed:", err)
    alert("Could not process file.")
  }
}

const viewAttachment = (file) => handleFileAction(file, 'inline')
const downloadAttachment = (file) => handleFileAction(file, 'attachment')

// Drag & Drop обработчики
const onDrop = (event, type) => {
  if (!isEditing.value) return
  const files = event.dataTransfer.files
  handleFilesAdded(files, type)
}

const fetchBatchAttachments = async (recordIds) => {
  // 1. Фильтруем список: оставляем только те ID, которых еще НЕТ в нашем кеше (attachmentsMap)
  const idsToFetch = recordIds.filter(id => id != null && !attachmentsMap.value.hasOwnProperty(id))

  // 2. Если все записи уже в кеше, ничего не делаем
  if (idsToFetch.length === 0) {
    console.log("[Attachments] All records already in cache, skipping request.")
    return
  }

  try {
    const token = localStorage.getItem('token')
    const response = await axios.post('/api/journal_attachment/batch',
      { journal_record_ids: idsToFetch },
      { headers: { 'Authorization': `Bearer ${token}` } }
    )

    // 3. Мержим только новые данные в кеш
    attachmentsMap.value = { ...attachmentsMap.value, ...response.data.attachments }
  } catch (err) {
    console.error("Error fetching batch attachments:", err)
  }
}

// Удобный computed для текущей выбранной записи
const currentAttachments = computed(() => {
  const recordId = journalData.value?.id
  return attachmentsMap.value[recordId] || { ARTICLE: [], SPECTRUM: [], MEDIA: [] }
})

// Вычисляемые свойства для нативной изоляции ID в SVG на вкладке поиска
const isolatedSearchProductSvg = computed(() => {
  const rawSvg = searchState.value.product_svg;
  if (!rawSvg) return '';

  const prefix = 'search-product';
  return rawSvg
    .replace(/id=["']([^"']+)["']/g, (match, id) => `id="${prefix}-${id}"`)
    .replace(/href=["']#([^"']+)["']/g, (match, href) => `href="#${prefix}-${href}"`)
    .replace(/url\(#([^)]+)\)/g, (match, url) => `url(#${prefix}-${url})`);
});

const isolatedSearchReagentSvg = computed(() => {
  const rawSvg = searchState.value.reagent_svg;
  if (!rawSvg) return '';

  const prefix = 'search-reagent';
  return rawSvg
    .replace(/id=["']([^"']+)["']/g, (match, id) => `id="${prefix}-${id}"`)
    .replace(/href=["']#([^"']+)["']/g, (match, href) => `href="#${prefix}-${href}"`)
    .replace(/url\(#([^)]+)\)/g, (match, url) => `url(#${prefix}-${url})`);
});

// Переменные для вкладки Поиска
const searchState = ref({
  reagent_smiles: '',
  reagent_svg: '',
  product_smiles: '',
  product_svg: '',
  exact_match: false
})
const showSearchKetcher = ref(false)
const currentSearchTarget = ref('') // 'reagent' или 'product'
let searchDebounceTimer = null

// Вспомогательная функция отправки глобального фрейма обратно "в космос"
const ketcherToBackground = () => {
  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  if (globalFrame) {
    globalFrame.style.cssText = "position: fixed; top: -5000px; left: -5000px; width: 800px; height: 600px; visibility: visible; z-index: -1000; pointer-events: none; border: none;"
  }
}

// Обработка ручного ввода SMILES в поиске
const onSearchSmilesInput = (target, e) => {
  const newSmiles = e.target.value
  searchState.value[`${target}_smiles`] = newSmiles

  clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    drawSearchSmiles(target, newSmiles)
  }, 400)
}

// Фоновая отрисовка структуры поиска
const drawSearchSmiles = async (target, smiles) => {
  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')

  if (!smiles || smiles.trim() === "") {
    searchState.value[`${target}_svg`] = ''
    return
  }

  const tryDraw = (attempts = 0) => {
    const ketcher = window.ketcherSingleton || globalFrame?.contentWindow?.ketcher
    if (ketcher && typeof ketcher.setMolecule === 'function') {
      if (!window.ketcherSingleton) window.ketcherSingleton = ketcher;
      (async () => {
        try {
          await ketcher.setMolecule(smiles)
          const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' })
          const svgText = await blob.text()
          searchState.value[`${target}_svg`] = svgText
        } catch (err) {
          console.error(`[Search Draw Error ${target}]:`, err)
        }
      })()
    } else if (attempts < 25) {
      setTimeout(() => tryDraw(attempts + 1), 100)
    }
  }
  tryDraw()
}

// Открытие Кетчера для поиска
const openSearchEditor = async (target) => {
  currentSearchTarget.value = target
  showSearchKetcher.value = true
  await nextTick()

  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  const marker = document.getElementById('search-ketcher-placeholder')

  if (globalFrame && marker) {
    const rect = marker.getBoundingClientRect()
    globalFrame.style.cssText = `
      position: fixed;
      top: ${rect.top}px;
      left: ${rect.left}px;
      width: ${rect.width}px;
      height: ${rect.height}px;
      border: none;
      visibility: visible;
      display: block;
      z-index: 2100;
      pointer-events: auto;
    `
  }

  const checkAndSet = async () => {
    const ketcher = window.ketcherSingleton || globalFrame?.contentWindow?.ketcher
    if (ketcher && ketcher.setMolecule) {
      if (!window.ketcherSingleton) window.ketcherSingleton = ketcher
      const smiles = searchState.value[`${currentSearchTarget.value}_smiles`]
      await ketcher.setMolecule(smiles || "")
      globalFrame?.contentWindow?.focus()
    } else {
      setTimeout(checkAndSet, 50)
    }
  }
  checkAndSet()
}

// Сохранение из Кетчера для поиска
const saveFromSearchKetcher = async () => {
  try {
    const ketcher = window.ketcherSingleton
    if (!ketcher) return

    const smiles = await ketcher.getSmiles()
    const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' })
    const svgText = await blob.text()

    searchState.value[`${currentSearchTarget.value}_smiles`] = smiles
    searchState.value[`${currentSearchTarget.value}_svg`] = svgText
  } catch (err) {
    console.error("Error saving search structure:", err)
  } finally {
    ketcherToBackground()
    showSearchKetcher.value = false
  }
}

const closeSearchEditorWithoutSaving = () => {
  ketcherToBackground()
  showSearchKetcher.value = false
}

const handleSubstructureSearch = async () => {

  const rSmiles = searchState.value.reagent_smiles?.trim();
  const pSmiles = searchState.value.product_smiles?.trim();

  if (!rSmiles && !pSmiles) {
    alert("Please enter or draw at least one structure to search (reagent or product).");
    return;
  }

  // 1. ПЕРВЫМ ДЕЛОМ блокируем стандартный onMounted таблицы!
  if (tableRef.value) {
    console.log("[Journal Debug Parent] Выставляем блокировку isSearchPending = true");
    tableRef.value.isSearchPending = true;
  }

  // 2. Только теперь переключаем вкладку
  activeTab.value = 'table';

  // 3. Ждем, пока отработает жизненный цикл Vue
  await nextTick();

  // Если компонент смонтировался только сейчас, реф появится здесь. Взводим флаг снова на всякий случай
  if (tableRef.value) {
    tableRef.value.isSearchPending = true;

    // 3. Запускаем поиск. Внутри него произойдет fetchRecords, который и вернет нужные данные
    try {
      const isExact = searchState.value.exact_match || undefined;
      await tableRef.value.runSubstructureSearch(rSmiles, pSmiles, isExact);
    } finally {
      // Снимаем блокировку в самом конце, чтобы обычные действия (клик по пагинации) работали штатно
      tableRef.value.isSearchPending = false;
    }
  } else {
    // Редкий фоллбек для ленивого рендеринга
    setTimeout(async () => {
      if (tableRef.value) {
        tableRef.value.isSearchPending = true;
        await tableRef.value.runSubstructureSearch(rSmiles, pSmiles);
        tableRef.value.isSearchPending = false;
      }
    }, 50);
  }
}

onMounted(() => {
  // Находим глобальный айфрейм, так как локальный мы удалили
  globalKetcherFrame.value = document.getElementById('global-ketcher-iframe')

  // Принудительно сбрасываем флаг занятости, чтобы журнал мог рисовать
  window.ketcherIsBusy = false
  setTimeout(() => {
    isKetcherInjected.value = true
  }, 1000)
})

const addReagent = () => {
  if (visibleReagentsCount.value < 5) {
    visibleReagentsCount.value++
  }
}

// Переключение вкладки на создание новой пустой структуры
const initNewEntryFromTable = () => {
  selectedRecordId.value = null
  journalData.value = createEmptyEntry()
  visibleReagentsCount.value = 3
  activeTab.value = 'method'
  isEditing.value = true
  // При создании новой записи аттачментов быть не может
  if (journalData.value.id) attachmentsMap.value[journalData.value.id] = { ARTICLE: [], SPECTRUM: [], MEDIA: [] }
  pendingAttachments.value = []
}

// Переключение режимов Редактировать / Отменить
const handleEditToggle = () => {
  if (!isEditing.value) {
    journalDataBackup.value = JSON.parse(JSON.stringify(journalData.value))
    isEditing.value = true
  } else {
    if (journalDataBackup.value) {
      journalData.value = JSON.parse(JSON.stringify(journalDataBackup.value))
      triggerKetcherRedraw(journalData.value)
    }
    isEditing.value = false
    journalDataBackup.value = null
  }
}

// Запись данных в форму и обновление счетчика видимых реактивов
const updateFormDataOnly = (record) => {
  journalData.value = { ...record }
  selectedRecordId.value = record.id
  isEditing.value = false

  let count = 0
  for (let i = 1; i <= 5; i++) {
    if (record[`reagent${i}_smiles`]) count = i
  }
  visibleReagentsCount.value = Math.max(count, 1)
  triggerKetcherRedraw(record)
}

// Выбор строки в интерактивной таблице журнала
const handleTableSelect = (record, forceTabChange = true) => {
  updateFormDataOnly(record)
  if (forceTabChange) {
    activeTab.value = 'method'
  }
}

// Сохранение записи (POST/PUT)
const saveEntry = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const cleanBodyData = getCleanDataForApi()
    const hasExternalId = journalData.value.external_id != null

    let response
    const isNewRecord = !hasExternalId
    if (hasExternalId) {
      response = await axios.put(`/api/my-journal/update/${journalData.value.external_id}`, cleanBodyData, {
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
      })
    } else {
      response = await axios.post('/api/my-journal/add', cleanBodyData, {
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
      })
    }

    const newRecordId = response.data.id
    journalData.value = response.data

    // --- ОБНОВЛЕННЫЙ БЛОК: СОХРАНЕНИЕ ТОЛЬКО ИЗМЕНЕННЫХ ОПИСАНИЙ ---
    const updatePromises = []
    const attachmentTypes = ['ARTICLE', 'SPECTRUM', 'MEDIA']

    attachmentTypes.forEach(type => {
      // Используем наше computed свойство currentAttachments
      const files = currentAttachments.value[type] || []

      files.forEach(file => {
        // Шлем PATCH только если файл уже на сервере (есть id) и он был изменен (_isDirty)
        if (file.id && file._isDirty) {
          updatePromises.push(
            axios.patch(`/api/journal_attachment/${file.id}`,
              { description: file.description },
              { headers: { 'Authorization': `Bearer ${token}` } }
            ).then(() => {
              delete file._isDirty // Снимаем флаг после успешного сохранения
            }).catch(err => {
              console.error(`Failed to update description for file ${file.id}`, err)
            })
          )
        }
      })
    })

    if (updatePromises.length > 0) {
      await Promise.all(updatePromises)
    }
    // --- КОНЕЦ БЛОКА ---

    // Если были файлы в очереди (для новой записи) - загружаем их теперь
    if (pendingAttachments.value.length > 0 && newRecordId) {
      isUploading.value = true
      for (const item of pendingAttachments.value) {
        try {
          await uploadFileToServer(newRecordId, item.file, item.type, item.description)
        } catch (err) {
          console.error("Error uploading pending file:", err)
        }
      }
      pendingAttachments.value = [] // Очищаем очередь
      isUploading.value = false
    }

    isEditing.value = false

    // Сбрасываем кеш для этой записи, чтобы подтянулись полные данные с сервера
    if (newRecordId) {
      delete attachmentsMap.value[newRecordId]
      // fetchBatchAttachments сработает автоматически через watch таблицы
    }

    triggerKetcherRedraw(response.data)
    alert(hasExternalId ? "Entry successfully updated!" : "Entry successfully saved!")

    if (tableRef.value) {
      // 1. Устанавливаем ID выделенной записи ДО обновлений
      if (isNewRecord && response.data?.id) {
        selectedRecordId.value = response.data.id;
      }

      // 2. Инжектим ID в массив поиска
      if (isNewRecord && tableRef.value.isSearchMode && response.data?.id) {
        if (!tableRef.value.searchResultsIds) tableRef.value.searchResultsIds = [];

        tableRef.value.searchResultsIds.unshift(response.data.id);
        tableRef.value.currentPage = 1;

      }

      // 3. Даем Vue обновить пропсы
      await nextTick();

      // 4. Триггерим обновление таблицы
      await tableRef.value.refreshData(true);
    }
  } catch (err) {
    console.error("Ошибка при сохранении:", err.response?.data || err)
    alert("Error! Please check the console.")
  } finally {
    loading.value = false
  }
}

// Удаление записи
const deleteEntry = async () => {
  const extId = journalData.value?.external_id
  if (!extId) return

  if (confirm(`Are you sure you want to completely delete record #${extId}?`)) {
    loading.value = true
    try {
      const token = localStorage.getItem('token')
      await axios.delete(`/api/my-journal/delete/${extId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      alert(`Record #${extId} successfully deleted.`)

      if (!tableRef.value) throw new Error("Компонент таблицы не найден")

      if (tableRef.value.isSearchMode && tableRef.value.searchResultsIds) {
        tableRef.value.searchResultsIds = tableRef.value.searchResultsIds.filter(id => id !== selectedRecordId.value);
      }

      const currentRecords = tableRef.value.records || []
      const currentIndex = currentRecords.findIndex(r => r.id === selectedRecordId.value)

      let nextRecordToLoad = null
      let needPageChange = false
      let targetPage = tableRef.value.currentPage

      // Запоминаем текущую страницу до каких-либо изменений
      const previousPage = tableRef.value.currentPage

      // 1. Проверяем, есть ли следующая запись на текущей странице
      if (currentIndex !== -1 && currentIndex < currentRecords.length - 1) {
        nextRecordToLoad = currentRecords[currentIndex + 1]
      } else {
        // 2. Если это была последняя запись на странице, нужно менять страницу
        if (tableRef.value.currentPage < tableRef.value.totalPages) {
          targetPage = tableRef.value.currentPage + 1
          needPageChange = true
        } else if (tableRef.value.currentPage > 1) {
          targetPage = tableRef.value.currentPage - 1
          needPageChange = true
        }
      }

      if (needPageChange) {
        // Фиксируем направление движения ДО вызова смены страницы
        const isMovingForward = targetPage > previousPage

        const newPageRecords = await tableRef.value.changePage(targetPage)

        if (newPageRecords && newPageRecords.length > 0) {
          await nextTick()
          // Теперь выборка сработает железно:
          // Если шли вперед (на след. страницу) -> берем первую запись [0]
          // Если шли назад (на пред. страницу) -> берем последнюю запись
          nextRecordToLoad = isMovingForward ? newPageRecords[0] : newPageRecords[newPageRecords.length - 1]
        }
      } else {
        // Если страница не менялась, просто обновляем текущую
        tableRef.value.refreshData(true)
        const freshRecords = tableRef.value.records || []
        if (nextRecordToLoad) {
          nextRecordToLoad = freshRecords.find(r => r.id === nextRecordToLoad.id) || freshRecords[currentIndex] || null
        }
      }

      // 3. Загружаем найденную запись в форму или очищаем, если журнал пуст
      if (nextRecordToLoad) {
        updateFormDataOnly(nextRecordToLoad)
      } else {
        selectedRecordId.value = null
        journalData.value = createEmptyEntry()
        visibleReagentsCount.value = 3
        isEditing.value = false
      }
    } catch (err) {
      console.error("Ошибка при удалении:", err.response?.data || err)
      alert("Failed to delete the record.")
    } finally {
      loading.value = false
    }
  }
}

// Стрелочная навигация (Вперед/Назад) по ID записей
const navigateRecord = async (direction) => {
  if (!tableRef.value || loading.value) return

  const currentRecords = tableRef.value.records || []
  const currentIndex = currentRecords.findIndex(r => r.id === selectedRecordId.value)
  let nextIndex = currentIndex + direction

  if (nextIndex >= currentRecords.length) {
    if (tableRef.value.currentPage < tableRef.value.totalPages) {
      loading.value = true
      const newPageRecords = await tableRef.value.changePage(tableRef.value.currentPage + 1)
      loading.value = false
      if (newPageRecords && newPageRecords.length > 0) {
        await nextTick()
        handleTableSelect(newPageRecords[0], false)
      }
    }
    return
  }

  if (nextIndex < 0) {
    if (tableRef.value.currentPage > 1) {
      loading.value = true
      const newPageRecords = await tableRef.value.changePage(tableRef.value.currentPage - 1)
      loading.value = false
      if (newPageRecords && newPageRecords.length > 0) {
        await nextTick()
        handleTableSelect(newPageRecords[newPageRecords.length - 1], false)
      }
    }
    return
  }

  const nextRecord = currentRecords[nextIndex]
  if (nextRecord) {
    handleTableSelect(nextRecord, false)
  }
}

// Глобальные вотчеры на изменение состояния аккаунтов и гостя
watch(isGuest, (newIsGuest) => {
  if (newIsGuest) {
    activeTab.value = 'method'
    journalData.value = createEmptyEntry()
    visibleReagentsCount.value = 3
  }
})

watch(() => userStore.currentAccountIndex, async () => {
  const currentAcc = userStore.currentUser
  if (currentAcc && currentAcc.token) {
    localStorage.setItem('token', currentAcc.token)
  } else {
    localStorage.removeItem('token')
  }

  journalData.value = createEmptyEntry()
  selectedRecordId.value = null
  attachmentsMap.value = {}

  await nextTick()
  if (tableRef.value && activeTab.value === 'table' && !isGuest.value) {
    tableRef.value.refreshData()
  }
})

// Перейти к самой первой записи (1 страница, 1 элемент)
const goToFirstRecord = async () => {
  if (!tableRef.value || loading.value) return
  loading.value = true
  try {
    // Принудительно переходим на 1 страницу
    const pageRecords = await tableRef.value.changePage(1)
    if (pageRecords && pageRecords.length > 0) {
      await nextTick()
      handleTableSelect(pageRecords[0], false)
    }
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

// Перейти к самой последней записи (Последняя страница, последний элемент)
const goToLastRecord = async () => {
  if (!tableRef.value || loading.value) return
  loading.value = true
  try {
    const lastPage = tableRef.value.totalPages
    // Принудительно переходим на последнюю страницу
    const pageRecords = await tableRef.value.changePage(lastPage)
    if (pageRecords && pageRecords.length > 0) {
      await nextTick()
      // Берем самый последний элемент из полученного массива
      handleTableSelect(pageRecords[pageRecords.length - 1], false)
    }
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

// Следим за списком записей в таблице. Как только они меняются — грузим для них аттачменты
watch(() => tableRef.value?.records, (newRecords) => {
  if (newRecords && newRecords.length > 0) {
    const ids = newRecords.map(r => r.id).filter(id => id != null)
    fetchBatchAttachments(ids)
  }
}, { immediate: true })

watch(activeTab, (newTab) => {
  if (newTab === 'method') {
    adjustHeight()
  }
})

</script>

<style scoped>
.journal-container { max-width: 1200px; margin: 0 auto; padding: 10px; }
.tabs-nav {
  display: flex;
  gap: 10px;
  margin-bottom: 10px; /* Было 20px */
  border-bottom: 2px solid #eee;
}
.tabs-nav button { padding: 10px 20px; cursor: pointer; border: none; background: none; font-size: 1.1rem; }
.tabs-nav button.active { border-bottom: 3px solid #42b983; font-weight: bold; }

.toolbar { margin-bottom: 20px; display: flex; gap: 10px; background: #f9f9f9; padding: 10px; border-radius: 8px; }
.btn-save {
  height: 42px;
  border-radius: 8px;
  padding: 8px 16px;
  font-weight: bold;
}
.btn-save:disabled { background: #ccc; }

.btn-edit-main {
  background-color: #34495e;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  height: 42px;
  transition: background 0.2s;
}
.btn-edit-main:hover:not(:disabled) { background-color: #2c3e50; }

/* Кнопка "Отменить" */
.btn-cancel-main {
  background-color: #e67e22;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  height: 42px;
  transition: background 0.2s;
}
.btn-cancel-main:hover { background-color: #d35400; }

/* Кнопка "Удалить" */
.btn-delete-main {
  background-color: #e74c3c;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  height: 42px;
  transition: background 0.2s;
}
.btn-delete-main:hover:not(:disabled) { background-color: #c0392b; }
.btn-delete-main:disabled {
  background-color: #ccc;
  color: #666;
  cursor: not-allowed;
}

.product-row { margin-bottom: 20px; width: 100%; }
.procedure-section { margin-top: 20px; }
.procedure-section textarea {
  width: 100%;
  min-height: 120px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #ddd;
  resize: none;
  overflow-y: hidden; /* Скрываем вертикальный скролл, так как высота будет расти */
  line-height: 1.5;
  display: block;    /* Убирает лишние отступы снизу */
  height: auto;      /* Позволяет скрипту управлять высотой */
}
.extra-fields-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 15px;
}
.extra-fields-row .field-group label {
  font-size: 0.85rem;
  font-weight: bold;
  color: #666;
  margin-bottom: 5px;
}
.extra-fields-row input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
}
@media (max-width: 600px) {
  .extra-fields-row { grid-template-columns: 1fr; gap: 10px; }
}
.reagents-container {
  margin: 20px 0;
  width: 100%;
}

.reagents-grid {
  display: grid;
  /* Карточка минимум 220px, максимум 1 часть доступного места */
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
  align-items: start;
}

/* На совсем маленьких экранах (мобилках) сделаем по 2 в ряд, если место позволяет */
@media (max-width: 500px) {
  .reagents-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }
}

.add-reagent-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%; /* Заполнит высоту сетки */
  min-height: 200px;
  border: 2px dashed #ccc;
  border-radius: 8px;
  background: #fdfdfd;
  color: #888;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1rem;
}

.add-reagent-card:hover {
  border-color: #42b983;
  color: #42b983;
  background: #f0fff8;
}

.plus-icon {
  font-size: 2rem;
  margin-bottom: 10px;
}

/* Адаптив для кнопки в мобильной сетке */
@media (max-width: 500px) {
  .add-reagent-card {
    min-height: 150px;
    font-size: 0.8rem;
  }
}

.invisible-ketcher {
  position: fixed;
  /* Даем реальные размеры, чтобы Ketcher не паниковал! */
  width: 800px;
  height: 600px;
  /* Уносим в космос */
  left: -5000px;
  top: -5000px;
  /* Но оставляем его "видимым" для системы рендеринга */
  visibility: visible;
  z-index: -1000;
  border: none;
  pointer-events: none;
}

.btn-add-main {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: background 0.2s;
}

.btn-add-main:hover {
  background-color: #3aa876;
}

.btn-add-main .icon {
  font-size: 1.2rem;
}

.global-record-nav {
  display: flex;
  align-items: center;
  gap: 5px; /* Уменьшили отступ между кнопками */
  background: #fff;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid #eee;
  width: fit-content;
}

.nav-arrow {
  background: #42b983;
  color: white;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 6px; /* Квадратные со скруглением смотрятся лучше, когда их много */
  cursor: pointer;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.nav-arrow:hover:not(:disabled) {
  background: #3aa876;
}

.nav-arrow:disabled { background: #ccc; cursor: not-allowed; }
.selected-id-display {
  font-weight: bold;
  color: #2c3e50;
  min-width: 70px; /* Немного уменьшили ширину */
  text-align: center;
  line-height: 32px;
  font-size: 0.9rem;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap; /* Разрешаем перенос на новую строку */
}

/* Корректируем навигацию, убираем лишний margin-bottom */
.global-record-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  padding: 5px 10px; /* Ужали по вертикали */
  border-radius: 8px;
  border: 1px solid #eee;
  width: fit-content;
}

.header-right-group {
  margin-left: auto;
  display: flex;
  gap: 8px;
  flex-wrap: wrap; /* Если их очень много, они тоже перенесутся */
}

/* Специальное правило для мобильных экранов */
@media (max-width: 600px) {
  .header-right-group {
    margin-left: 0; /* Убираем притяжение вправо на мобилках */
    width: 100%;    /* Заставляем кнопки занять всю ширину, если они перенеслись вниз */
    justify-content: flex-start;
  }

  /* Делаем кнопки чуть компактнее на мобилках */
  .btn-edit-main, .btn-cancel-main, .btn-add-main {
    padding: 8px 12px;
    font-size: 0.9rem;
    flex-grow: 1; /* Кнопки будут растягиваться равномерно на всю ширину */
    justify-content: center;
  }
}

/* Компактная кнопка добавления */
.btn-add-main {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 8px 16px; /* Уменьшили паддинги */
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.2s;
  height: 42px; /* Выравниваем высоту со стрелками */
}

/* Уменьшаем отступ у основной навигации вкладок */
.tabs-nav {
  margin-bottom: 15px;
}

/* Убираем лишние отступы в контенте таблицы */
.table-actions {
  display: none; /* Мы ее перенесли выше */
}

/* Стили для гостевого режима */
.tabs-nav button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  border-bottom: none;
}
.tabs-nav button:disabled:hover {
  color: inherit;
  background: none;
}

.guest-alert-banner {
  display: flex;
  align-items: center;
  gap: 15px;
  background-color: #e8f4fd;
  border-left: 4px solid #3498db;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 20px;
}
.banner-icon {
  font-size: 1.5rem;
}
.banner-text {
  margin: 0;
  color: #2c3e50;
  font-size: 0.95rem;
  line-height: 1.4;
}
.banner-link {
  color: #3498db;
  text-decoration: underline;
  font-weight: bold;
}
.banner-link:hover {
  color: #2980b9;
}

.search-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.search-zones-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
  gap: 20px;
  width: 100%;
}
@media (max-width: 950px) {
  .search-zones-grid {
    grid-template-columns: 1fr;
  }
}
.search-card {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.search-actions-row {
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

/* Дублируем базовые стили отображения структуры (если они не глобальные) */
.card-header {
  background: #f5f5f5;
  padding: 10px 15px;
  font-weight: bold;
  border-bottom: 1px solid #ddd;
}
.card-body {
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.structure-zone {
  border: 1px solid #ccc;
  border-radius: 6px;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
}
.editable-zone {
  cursor: pointer;
  transition: background 0.2s;
}
.editable-zone:hover {
  background: #f0f7f4;
  border-color: #42b983;
}
.placeholder {
  text-align: center;
  color: #888;
}
.placeholder .icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 5px;
}
.fields-zone {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.field-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.field-group label {
  font-size: 0.85rem;
  font-weight: bold;
  color: #666;
}
.smiles-compact-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-family: monospace;
}
.svg-render {
  width: 100%;
  height: 100%;
  max-height: 220px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.svg-render :deep(svg) {
  max-width: 100%;
  max-height: 200px;
}

/* Стили модалки для вкладки поиска (аналогично product card) */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 2000; display: flex; align-items: center; justify-content: center; }
.modal-content { width: 85%; height: 85%; background: white; display: flex; flex-direction: column; border-radius: 8px; overflow: hidden; }
.ketcher-frame { flex: 1; border: none; }
.modal-header { padding: 10px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; }
.btn-apply { background: #42b983; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-cancel { background: #999; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }

.attachments-section {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 2px solid #eee;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
@media (max-width: 850px) {
  .attachments-section { grid-template-columns: 1fr; }
}
.attachment-block h3 {
  font-size: 1.1rem;
  margin-bottom: 10px;
  color: #2c3e50;
}
.attachment-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.attachment-table th, .attachment-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #eee;
  font-size: 0.9rem;
}
.attachment-table th {
  background: #f8f9fa;
  font-weight: bold;
  color: #666;
}
.att-link {
  color: #3498db;
  text-decoration: none;
  word-break: break-all;
}
.att-link:hover {
  text-decoration: underline;
}
.empty-text {
  color: #999;
  font-style: italic;
  text-align: center;
  padding: 15px !important;
}
.drop-zone {
  border: 2px transparent dashed;
  border-radius: 8px;
  transition: all 0.2s;
  position: relative;
}
.drop-active {
  border-color: #42b983;
  background: #f0fcf7;
}
.upload-hint {
  text-align: center;
  font-size: 0.8rem;
  color: #42b983;
  margin-top: 5px;
  font-weight: bold;
  opacity: 0.7;
}
.pending-row {
  background-color: #fff9e6;
}
.desc-edit-input {
  width: 100%;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 0.85rem;
}
.desc-edit-input:focus {
  outline: none;
  border-color: #42b983;
}
/* Анимация для индикации загрузки */
.pending-row .att-link {
  color: #e67e22;
  font-style: italic;
}

.att-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  align-items: center;
}
.btn-att-save, .btn-att-delete {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn-att-save:hover { background-color: #e8f4fd; }
.btn-att-delete:hover { background-color: #fee; }

.pending-row .btn-att-delete {
  color: #e74c3c;
  font-weight: bold;
  font-size: 1rem;
}

/* Расширение сетки аттачментов */
.attachments-section {
  grid-template-columns: 1fr 1fr; /* статьи и спектры сверху */
}

.media-full-width {
  grid-column: 1 / -1; /* Медиа занимает всю ширину */
  margin-top: 20px;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 15px;
  min-height: 100px;
  padding: 10px;
}

.media-card {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.media-card:hover {
  transform: translateY(-2px);
}

.media-preview {
  width: 100%;
  height: 120px;
  background: #f0f0f0;
  position: relative;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.media-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-placeholder {
  font-size: 3rem;
}

.media-overlay-actions {
  position: absolute;
  top: 5px;
  right: 5px;
  display: none;
}

.media-preview:hover .media-overlay-actions {
  display: flex;
}

.media-info {
  padding: 8px;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.media-desc-edit {
  width: 100%;
  height: 45px;
  font-size: 0.8rem;
  border: 1px solid #eee;
  border-radius: 4px;
  resize: none;
  padding: 4px;
}

.media-desc-text {
  font-size: 0.85rem;
  margin: 0;
  color: #444;
  display: -webkit-box;
  -webkit-line-clamp: 2; /* Ограничение в 2 строки */
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 34px;
}

.media-card-controls {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.media-empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 30px;
  color: #999;
  font-style: italic;
}

.btn-mini {
  background: rgba(255,255,255,0.9);
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  padding: 2px 6px;
}

.media-card.pending {
  border: 1px dashed #e67e22;
  opacity: 0.8;
}

/* Делаем зону кликабельной */
.drop-zone.clickable {
  cursor: pointer;
}
.drop-zone.clickable:hover {
  background: #f8fcf9;
  border-color: #42b983;
}

/* Большая зеленая кнопка добавления аттачмента */
.btn-add-att-large {
  width: 100%;
  margin-top: 10px;
  padding: 10px;
  background-color: #f0fcf7;
  color: #42b983;
  border: 2px dashed #42b983;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-add-att-large:hover {
  background-color: #42b983;
  color: white;
  border-style: solid;
}

.btn-add-att-large .icon {
  font-size: 1.2rem;
}
</style>