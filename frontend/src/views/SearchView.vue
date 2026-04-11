<script setup>
import {ref, nextTick, watch} from 'vue'

import JournalResults from '@/components/results/JournalResults.vue'
import BookResults from '@/components/results/BookResults.vue'
import PublicJournalResults from '@/components/results/PublicJournalResults.vue'

const journalRef = ref(null)

//состояние чекбоксов
const sources = ref({
  journal: true,
  book: true,
  public: true
})

const reactionSmiles = ref('')
const reactionSvg = ref('') // Для хранения картинки в формате SVG
const isExact = ref(false) // Состояние для чекбокса Exact Match
const showKetcher = ref(false)
const ketcherFrame = ref(null)
const searchMode = ref('simple')


const openEditor = async () => {
  showKetcher.value = true
  await nextTick()

  const timer = setInterval(async () => {
    try {
      const frame = ketcherFrame.value
      const ketcher = frame?.contentWindow?.ketcher

      // Проверяем, что объект ketcher полностью инициализирован
      if (ketcher && typeof ketcher.getSmiles === 'function') {
        clearInterval(timer)

        let smilesToLoad = reactionSmiles.value

        if (smilesToLoad) {
          // Если мы сами добавили >> в начало (поиск продукта),
          // для РЕДАКТОРА их ОБЯЗАТЕЛЬНО убираем, иначе он откроет пустоту
          if (smilesToLoad.startsWith('>>')) {
            smilesToLoad = smilesToLoad.substring(2)
          }

          // Используем setMolecule, но оборачиваем в try,
          // так как Indigo может быть еще занят
          try {
            await ketcher.setMolecule(smilesToLoad)
          } catch (e) {
            console.warn("Retrying setMolecule...", e)
            // Последний шанс через 100мс
            setTimeout(() => ketcher.setMolecule(smilesToLoad), 100)
          }
        }
      }
    } catch (e) {
      // Игнорируем ошибки доступа к фрейму
    }
  }, 250) // Интервал чуть больше для стабильности на Xeon/сервере

  setTimeout(() => clearInterval(timer), 5000)
}

// Главная функция: забираем данные из Ketcher
const saveFromKetcher = async () => {
  try {
    const ketcher = ketcherFrame.value?.contentWindow?.ketcher
    if (!ketcher) return

    // Выбираем метод получения данных в зависимости от режима
    const result = searchMode.value === 'advanced'
      ? await ketcher.getSmarts()
      : await ketcher.getSmiles()

    if (result && result.trim().length > 0) {
      let finalStr = result.trim()

      if (!finalStr.includes('>>')) {
        finalStr = `>>${finalStr}`
      }

      reactionSmiles.value = finalStr
      const blob = await ketcher.generateImage(finalStr, {outputFormat: 'svg'})
      reactionSvg.value = await blob.text()
    }
    showKetcher.value = false
  } catch (e) {
    console.error("Save Error:", e)
  }
}

const handleSearch = () => {
  console.log('Global Search Triggered for:', reactionSmiles.value, 'Exact:', isExact.value)
  if (sources.value.journal) {
    journalRef.value?.performNewSearch()
  }
}

// Функция для обновления превью, если SMILES ввели вручную
const updatePreviewFromSmiles = async (smiles) => {
  if (!smiles || smiles.trim().length === 0) {
    reactionSvg.value = ''
    return
  }

  try {
    const frame = ketcherFrame.value
    const ketcher = frame?.contentWindow?.ketcher

    if (ketcher && typeof ketcher.generateImage === 'function') {
      // Генерируем SVG. Если в SMILES нет стрелки, Ketcher нарисует просто молекулу.
      // Если мы хотим, чтобы в превью всегда была стрелка (как продукт),
      // можем добавить её и здесь: const s = smiles.includes('>>') ? smiles : '>>' + smiles
      const blob = await ketcher.generateImage(smiles, {outputFormat: 'svg'})
      reactionSvg.value = await blob.text()
    }
  } catch (e) {
    console.warn("Не удалось обновить превью из SMILES:", e)
  }
}

// Следим за вводом в текстовое поле
watch(reactionSmiles, (newValue) => {
  // Обновляем только если окно редактора закрыто
  // (чтобы не зацикливать обновление при рисовании)
  if (!showKetcher.value) {
    updatePreviewFromSmiles(newValue)
  }
})

watch(searchMode, (newMode) => {
  if (newMode === 'advanced') {
    isExact.value = false
  }
})


</script>

<template>
  <div class="search-page">
    <header class="page-header">
      <h2>Public Reaction Database</h2>
      <p>Draw a reaction or paste SMILES to search the database</p>
    </header>

    <div class="search-container">
      <div class="reaction-preview" @click="openEditor">
        <div v-if="!reactionSvg" class="placeholder">
          <div class="icon">⚗️</div>
          <p>Click here to draw a reaction</p>
        </div>

        <div v-else class="svg-display" v-html="reactionSvg"></div>
      </div>

      <div class="source-filters">
        <label><input type="checkbox" v-model="sources.journal"> Journal Base</label>
        <label><input type="checkbox" v-model="sources.book"> Book Base</label>
        <label><input type="checkbox" v-model="sources.public"> Public Journal</label>
      </div>

<div class="mode-filters">
  <label>
    <input type="radio" value="simple" v-model="searchMode"> Simple (SMILES)
  </label>
  <label>
    <input type="radio" value="advanced" v-model="searchMode"> Advanced (SMARTS)
  </label>
</div>
      <div class="controls">
        <input
            v-model="reactionSmiles"
            placeholder="Reaction SMILES (e.g. CC>>CC)..."
            class="smiles-input"
        />
        <label class="exact-checkbox" :class="{ 'disabled-label': searchMode === 'advanced' }">
  <input
    type="checkbox"
    v-model="isExact"
    :disabled="searchMode === 'advanced'"
  >
  Exact Match
</label>
        <button
            class="btn-search"
            :disabled="!reactionSmiles"
            @click="handleSearch"
        >
          Search
        </button>
      </div>
    </div>
    <div class="results-wrapper">
      <JournalResults
    ref="journalRef"
    v-if="sources.journal"
    :smiles="reactionSmiles"
    :exact="isExact"
    :mode="searchMode"
/>
      <BookResults v-if="sources.book" :smiles="reactionSmiles"/>
      <PublicJournalResults v-if="sources.public" :smiles="reactionSmiles"/>
    </div>


    <div v-show="showKetcher" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Structure Editor</h3>
          <div class="modal-buttons">
            <button @click="saveFromKetcher" class="btn-save">Apply Structure</button>
            <button @click="showKetcher = false" class="btn-close">Cancel</button>
          </div>
        </div>
        <iframe
            ref="ketcherFrame"
            src="/standalone/index.html?hidden_controls=help,settings,save&api_path=/&allow_reaction=true"
            class="ketcher-frame"
            @load="updatePreviewFromSmiles(reactionSmiles)"
        ></iframe>
      </div>
    </div>
  </div>
</template>

<style scoped>
.source-filters {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 8px;
}

.source-filters label {
  cursor: pointer;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 5px;
}

.results-wrapper {
  margin-top: 30px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.search-page {
  max-width: 1000px;
  margin: 40px auto;
  padding: 0 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.search-container {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

/* Стили зоны превью */
.reaction-preview {
  width: 100%;
  height: 300px;
  border: 2px dashed #ddd;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #fafafa;
  margin-bottom: 20px;
  transition: all 0.3s ease;
  overflow: hidden;
}

.reaction-preview:hover {
  border-color: #42b983;
  background: #f0fff8;
}

.placeholder {
  text-align: center;
  color: #888;
}

.placeholder .icon {
  font-size: 3rem;
  margin-bottom: 10px;
}

/* Контейнер для SVG */
.svg-display {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
}

/* Делаем SVG адаптивным внутри контейнера */
.svg-display :deep(svg) {
  max-width: 95%;
  max-height: 95%;
  width: auto;
  height: auto;
}

/* Инпут и Кнопка */
.controls {
  display: flex;
  gap: 12px;
}

.smiles-input {
  flex: 1;
  padding: 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-family: monospace;
  font-size: 1rem;
}

.btn-search {
  padding: 0 30px;
  background: #2c3e50;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-search:hover:not(:disabled) {
  background: #3e5871;
}

.btn-search:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

/* Модалка */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.modal-content {
  background: white;
  width: 100%;
  max-width: 1200px;
  height: 90vh;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  padding: 15px 20px;
  background: #f8f9fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
}

.ketcher-frame {
  flex: 1;
  border: none;
  width: 100%;
}

.btn-save {
  background: #42b983;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
  margin-right: 10px;
}

.btn-close {
  background: #95a5a6;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.exact-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  font-size: 0.9rem;
  cursor: pointer;
  user-select: none;
}

/* Адаптивность для мобилок */
@media (max-width: 600px) {
  .controls {
    flex-direction: column;
    align-items: stretch;
  }

  .exact-checkbox {
    padding: 5px 0;
  }

  .btn-search {
    padding: 12px;
  }
}
.mode-filters {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
  padding: 5px 10px;
  font-size: 0.9rem;
}
.mode-filters label {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
}
.disabled-label {
  color: #bdc3c7;
  cursor: not-allowed !important;
}

.disabled-label input {
  cursor: not-allowed;
}
</style>