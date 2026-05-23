<script setup>
import {ref, nextTick, watch} from 'vue'

import JournalResults from '@/components/results/JournalResults.vue'
import BookResults from '@/components/results/BookResults.vue'
import PublicJournalResults from '@/components/results/PublicJournalResults.vue'

const journalRef = ref(null)
const bookRef = ref(null)

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


// Вспомогательная функция: возвращает фрейм в скрытое состояние в самый низ экрана
const ketcherToBackground = () => {
  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  if (globalFrame) {
    globalFrame.style.cssText = "position: fixed; top: -9999px; left: -9999px; width: 1px; height: 1px; visibility: hidden; z-index: -1;"
  }
}

const openEditor = async () => {
  showKetcher.value = true
  await nextTick()

  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  const marker = document.getElementById('ketcher-placeholder-marker')

  if (globalFrame && marker) {
    // Получаем точные экранные координаты блока-маркера внутри модального окна
    const rect = marker.getBoundingClientRect()

    // Поверх него накладываем наш глобальный фрейм через fixed, не перезагружая iframe!
    globalFrame.style.cssText = `
      position: fixed;
      top: ${rect.top}px;
      left: ${rect.left}px;
      width: ${rect.width}px;
      height: ${rect.height}px;
      border: none;
      visibility: visible;
      display: block;
      z-index: 2100; /* Выше модального окна */
    `
  }

  // Запускаем ваш оригинальный интервал 1 в 1
  const timer = setInterval(async () => {
    try {
      const ketcher = window.ketcherSingleton || globalFrame?.contentWindow?.ketcher

      if (ketcher && typeof ketcher.getSmiles === 'function') {
        clearInterval(timer)
        if (!window.ketcherSingleton) window.ketcherSingleton = ketcher

        let smilesToLoad = reactionSmiles.value

        if (smilesToLoad) {
          if (smilesToLoad.startsWith('>>')) {
            smilesToLoad = smilesToLoad.substring(2)
          }

          try {
            await ketcher.setMolecule(smilesToLoad)
          } catch (e) {
            console.warn("Retrying setMolecule...", e)
            setTimeout(() => ketcher.setMolecule(smilesToLoad), 100)
          }
        } else {
          // Если строка поиска пустая — обязательно очищаем холст Кетчера от старых структур!
          await ketcher.setMolecule('')
        }
      }
    } catch (e) {
      // Игнорируем ошибки доступа
    }
  }, 250)

  setTimeout(() => clearInterval(timer), 5000)
}

const saveFromKetcher = async () => {
  try {
    const ketcher = window.ketcherSingleton
    if (!ketcher) return

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
    } else {
      // Если в редакторе всё стерли и нажали Save
      reactionSmiles.value = ''
      reactionSvg.value = ''
    }
    ketcherToBackground()
    showKetcher.value = false
  } catch (e) {
    console.error("Save Error:", e)
    ketcherToBackground()
    showKetcher.value = false
  }
}

const closeEditorWithoutSaving = () => {
  ketcherToBackground()
  showKetcher.value = false
}

const handleSearch = () => {
  console.log('Global Search Triggered for:', reactionSmiles.value, 'Exact:', isExact.value)
  if (sources.value.journal) {
    journalRef.value?.performNewSearch()
  }

  if (sources.value.book) {
    bookRef.value?.performNewSearch()
  }

}

// Функция для обновления превью, если SMILES ввели вручную
const updatePreviewFromSmiles = async (smiles) => {
  if (!smiles || smiles.trim().length === 0) {
    reactionSvg.value = ''
    return
  }

  try {
    const ketcher = window.ketcherSingleton

    if (ketcher && typeof ketcher.generateImage === 'function') {
      const blob = await ketcher.generateImage(smiles, {outputFormat: 'svg'})
      reactionSvg.value = await blob.text()
    }
  } catch (e) {
    console.warn("Failed to update preview from SMILES:", e)
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
      <p>Draw a reaction(or just a product) or paste SMILES to search the database</p>
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
      <BookResults
    ref="bookRef"
    v-if="sources.book"
    :smiles="reactionSmiles"
    :exact="isExact"
    :mode="searchMode"
      />
      <PublicJournalResults v-if="sources.public" :smiles="reactionSmiles"/>
    </div>


    <div v-show="showKetcher" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Structure Editor</h3>
          <div class="modal-buttons">
            <button @click="saveFromKetcher" class="btn-save">Apply Structure</button>
            <button @click="closeEditorWithoutSaving" class="btn-close">Cancel</button>
          </div>
        </div>
        <!-- Контейнер-заглушка, куда временно переместится глобальный фрейм -->
        <div id="ketcher-placeholder-marker" class="ketcher-frame" style="background: transparent;"></div>
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
  width: 95vw;
  max-width: 1600px;
  height: 95vh;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  padding: 12px 20px;
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
  height: 100%;
  display: block;
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