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
        <button @click="navigateRecord(-1)" :disabled="isEditing" class="nav-arrow">←</button>
        <span class="selected-id-display">
          Record: {{ journalData?.external_id ? '#' + journalData.external_id : '---' }}
        </span>
        <button @click="navigateRecord(1)" :disabled="isEditing" class="nav-arrow">→</button>
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

        <JournalTable ref="tableRef" :selected-id="selectedRecordId"
         @select-record="handleTableSelect"
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
            v-model="journalData.procedure"
            :disabled="!isEditing"
            placeholder="Describe the synthesis procedure..."
          ></textarea>
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
    <iframe
      id="global-ketcher-iframe"
      ref="globalKetcherFrame"
      src="/standalone/index.html?hidden_controls=all"
      class="invisible-ketcher">
    </iframe>
  </div>

</template>

<script setup>
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import axios from 'axios'
import ProductCard from '@/components/ProductCard.vue'
import ReagentCard from '@/components/ReagentCard.vue'
import JournalTable from '@/components/JournalTable.vue'
import { useUserStore } from '@/stores/user'

// Импортируем наши новые хуки
import { useJournalCalculator } from '@/composables/useJournalCalculator'
import { useJournalKetcher } from '@/composables/useJournalKetcher'

const userStore = useUserStore()
const isGuest = computed(() => !userStore.isLoggedIn)

// Подключаем логику калькулятора структур
const { journalData, createEmptyEntry, getCleanDataForApi } = useJournalCalculator()

// DOM элементы и ссылки на дочерние компоненты
const tableRef = ref(null)
const productCardRef = ref(null)
const reagentCardRefs = ref([])
const globalKetcherFrame = ref(null)

// Подключаем логику работы с Ketcher движком
const { isKetcherInjected, triggerKetcherRedraw } = useJournalKetcher(globalKetcherFrame, journalData)

// Управление состоянием UI
const _isEditingInternal = ref(false)
const isEditing = computed({
  get: () => isGuest.value ? true : _isEditingInternal.value,
  set: (val) => { _isEditingInternal.value = val }
})

const activeTab = ref(isGuest.value ? 'method' : 'table')
const loading = ref(false)
const visibleReagentsCount = ref(3)
const selectedRecordId = ref(null)
const journalDataBackup = ref(null)

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

    journalData.value = response.data
    isEditing.value = false

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

  await nextTick()
  if (tableRef.value && activeTab.value === 'table' && !isGuest.value) {
    tableRef.value.refreshData()
  }
})

</script>

<style scoped>
.journal-container { max-width: 1200px; margin: 0 auto; padding: 10px; }
.tabs-nav { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #eee; }
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
.procedure-section textarea { width: 100%; height: 200px; padding: 10px; border-radius: 8px; border: 1px solid #ddd; }
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
  gap: 15px;
  margin-bottom: 15px;
  background: #fff;
  padding: 10px;
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
  border-radius: 50%;
  cursor: pointer;
  font-weight: bold;
}
.nav-arrow:disabled { background: #ccc; cursor: not-allowed; }
.selected-id-display {
  font-weight: bold;
  color: #2c3e50;
  min-width: 100px;
  text-align: center;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 15px; /* Уменьшили отступ */
  flex-wrap: wrap;     /* Чтобы на мобилках не ломалось */
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
  margin-bottom: 0; /* Убрали старый отступ */
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


</style>