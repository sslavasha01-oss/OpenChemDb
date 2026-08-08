<template>
  <div class="card product-card">
    <div class="card-header">Reaction Product</div>

    <div class="card-body">
      <div
        class="structure-zone"
        :class="{ 'editable-zone': isEditing }"
        @click="isEditing && openEditor()"
      >
        <div v-if="!modelValue.product_preview_svg" class="placeholder">
          <span class="icon">⚗️</span>
          <p>Click to draw structure</p>
        </div>
        <div v-else class="svg-render" v-html="modelValue.product_preview_svg"></div>
      </div>

      <div class="fields-zone">
        <div class="field-group">
          <label>SMILES</label>
          <div class="smiles-input-group">
            <input
              type="text"
              :value="modelValue.product_smiles"
              @input="onSmilesInput"
              :disabled="!isEditing"
              placeholder="C1=CC=CC=C1..."
              class="smiles-compact-input"
            >
          </div>
        </div>

        <div class="metrics-grid">
          <div class="field-group readonly">
            <label>M.W. (g/mol)</label>
            <input type="number" :value="modelValue.product_molar_mass" disabled>
          </div>

          <div class="field-group mass-highlight">
            <label>Prac. mass (g)</label>
            <input
              type="number"
              v-model.number="modelValue.product_praktical_mass"
              :disabled="!isEditing"
              step="0.001"
            >
          </div>

          <div class="field-group readonly">
            <label>Moles</label>
            <input type="number" :value="modelValue.product_moles" disabled>
          </div>

          <div class="field-group readonly mass-highlight">
            <label>Theor. mass (g)</label>
            <input type="number" :value="modelValue.product_theoretical_mass" disabled>
          </div>

          <div class="field-group">
            <label>Eq.</label>
            <input
              type="number"
              v-model.number="modelValue.product_molar_ekv"
              :disabled="!isEditing"
              step="0.01"
            >
          </div>
        </div>
      </div>
    </div>

    <div class="card-footer-row">
      <!-- Поле даты создания (только чтение) -->
      <div class="field-group date-field readonly">
        <label>Created At</label>
        <input
          type="text"
          :value="modelValue.date_added ? new Date(modelValue.date_added).toLocaleDateString() : '—'"
          disabled
        >
      </div>

      <div class="field-group conditions-field">
        <label>Conditions</label>
        <input
          type="text"
          v-model="modelValue.conditions"
          :disabled="!isEditing"
          placeholder="EtOH, r.t., 2h, or Pd(PPh3)4, 80°C..."
        >
      </div>

      <div class="field-group yield-field">
        <label>Yield (%)</label>
        <input type="number" :value="modelValue.product_yield_calc" disabled class="yield-input">
      </div>
    </div>

    <div v-show="showKetcher" class="modal-overlay" style="z-index: 2000;">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Product Structure Editor</h3>
          <div class="modal-btns">
            <button @click="saveFromKetcher" class="btn-apply">Apply</button>
            <button @click="closeEditorWithoutSaving" class="btn-cancel">Cancel</button>
          </div>
        </div>
        <!-- Маркер-ориентир. Сюда визуально встанет глобальный фрейм -->
        <div id="product-ketcher-placeholder" class="ketcher-frame" style="background: transparent;"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { renderStructure, calculateMW } from '@/utils/chemUtils'
import OCL from 'openchemlib'

const props = defineProps({
  modelValue: Object,
  isEditing: Boolean
})

const emit = defineEmits(['update:modelValue', 'calculate'])

const showKetcher = ref(false)
const ketcherFrame = ref(null)
const hiddenKetcher = ref(null)

let debounceTimer = null

// 1. Обработка ручного ввода SMILES
const onSmilesInput = (e) => {
  const newSmiles = e.target.value
  const updatedValue = { ...props.modelValue, product_smiles: newSmiles };
  emit('update:modelValue', updatedValue);

  // Сбрасываем предыдущий таймер, если пользователь продолжает печатать
  clearTimeout(debounceTimer);

  // Запускаем рендер и расчет массы только через 400мс затишья
  debounceTimer = setTimeout(() => {
    drawSmiles(newSmiles);
  }, 400);
}

// Вспомогательная функция отправки глобального фрейма обратно "в космос"
const ketcherToBackground = () => {
  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  if (globalFrame) {
    globalFrame.style.cssText = "position: fixed; top: -5000px; left: -5000px; width: 1000px; height: 800px; visibility: visible; border: none; pointer-events: none;";
  }
}

let lastRenderedSmiles = '';

const drawSmiles = (smiles) => {
  console.log("[DrawSmiles] Triggered with:", smiles);

  if (smiles === lastRenderedSmiles && smiles !== '') {
    console.log("[DrawSmiles] Smiles matches last rendered, skipping.");
    return;
  }
  lastRenderedSmiles = smiles;

  // Создаем копию объекта, чтобы Vue "увидел" изменение ссылки
  const updated = { ...props.modelValue };

  if (!smiles || smiles.trim() === "") {
    updated.product_preview_svg = '';
    updated.product_molar_mass = '';
  } else {
    // 1. Рендерим SVG
    const svg = renderStructure(smiles, 160, 160);
    updated.product_preview_svg = svg;

    // 2. Считаем массу
    const mw = calculateMW(smiles);
    updated.product_molar_mass = mw;

    console.log("[DrawSmiles] New MW assigned to object:", updated.product_molar_mass);
  }

  emit('update:modelValue', updated);

  nextTick(() => {
    console.log("[DrawSmiles] Emitting calculate event...");
    emit('calculate');
  });
};

defineExpose({ drawSmiles });

// 4. Сохранение изменений из глобального Кетчера
const saveFromKetcher = async () => {
  try {
    const ketcher = window.ketcherSingleton
    if (!ketcher) return;

    const smiles = await ketcher.getSmiles();
    console.log("[SaveFromKetcher] Smiles from editor:", smiles);

    const updatedValue = { ...props.modelValue };
    updatedValue.product_smiles = smiles;

    // Генерируем через OCL
    updatedValue.product_preview_svg = renderStructure(smiles, 160, 160);
    updatedValue.product_molar_mass = calculateMW(smiles);

    console.log("[SaveFromKetcher] Resulting MW:", updatedValue.product_molar_mass);

    emit('update:modelValue', updatedValue);

    nextTick(() => {
      emit('calculate');
    });

  } catch (err) {
    console.error("Error saving product:", err);
  } finally {
    ketcherToBackground();
    showKetcher.value = false;
  }
};

// 3. Безопасное открытие редактора через CSS-телепорт
const openEditor = async () => {
  showKetcher.value = true;
  await nextTick();

  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  const marker = document.getElementById('product-ketcher-placeholder')

  if (globalFrame && marker) {
    // Вычисляем, где на экране открылось наше модальное окно
    const rect = marker.getBoundingClientRect()

    // Перемещаем глобальный фрейм точно на место маркера
    globalFrame.style.cssText = `
      position: fixed;
      top: ${rect.top}px;
      left: ${rect.left}px;
      width: ${rect.width}px;
      height: ${rect.height}px;
      border: none;
      visibility: visible;
      display: block;
      z-index: 2100; /* Поверх оверлея модалки */
      pointer-events: auto; /* <- ИСПРАВЛЕНО: Явно разрешаем события мыши! */
    `
  }

  const checkAndSet = async () => {
    const ketcher = window.ketcherSingleton ||
                    globalFrame?.contentWindow?.ketcher ||
                    document.getElementById('global-ketcher-iframe')?.contentWindow?.ketcher;
    if (ketcher && ketcher.setMolecule) {
      if (!window.ketcherSingleton) window.ketcherSingleton = ketcher;

      const smiles = props.modelValue.product_smiles;
      await ketcher.setMolecule(smiles || "");

      // Обертка для фикса истории и зума после рендеринга структуры
      setTimeout(() => {
        try {
          if (typeof ketcher.setZoom === 'function') ketcher.setZoom(1.0);
          else if (ketcher.editor?.setZoom) ketcher.editor.setZoom(1.0);

          if (ketcher.editor?.centerXy) ketcher.editor.centerXy();

          // Очистка стеков истории, которые мы нашли в дампе
          const editor = ketcher.editor;
          if (editor) {
            if (Array.isArray(editor.historyStack)) editor.historyStack = [];
            editor.historyPtr = 0;

            if (Array.isArray(editor.originalHistoryStack)) editor.originalHistoryStack = [];
            editor.originalHistoryPointer = 0;

            // Принудительно тушим стрелочки Undo/Redo в UI Кетчера
            if (editor.event?.historyChange?.dispatch) {
              editor.event.historyChange.dispatch();
            }
          }
        } catch (e) {
          console.warn("Ketcher history clear failed silently:", e);
        }
      }, 150); // 150мс задержки как раз хватает, чтобы Epam-стейт "успокоился"

      globalFrame?.contentWindow?.focus();

    } else {
      setTimeout(checkAndSet, 50);
    }
  };
  checkAndSet();
};

const closeEditorWithoutSaving = () => {
  ketcherToBackground();
  showKetcher.value = false;
}
</script>

<style scoped>
.card {
  border: 1px solid #ccc;
  border-radius: 12px;
  background: white;
  background: white;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.card-header {
  background: #2c3e50;
  color: white;
  padding: 8px 15px;
  font-weight: bold;
}
.card-body {
  display: flex;
  gap: 20px;
  padding: 15px 15px 5px 15px;
}

/* Компактный квадрат структуры */
.structure-zone {
  width: 160px;
  height: 160px;
  border: 1px dashed #bbb;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #fcfcfc;
  box-sizing: border-box;
}
.editable-zone:hover {
  border-color: #42b983;
  background: #fafffd;
}
.placeholder { text-align: center; color: #777; padding: 5px; }
.placeholder .icon { font-size: 1.4rem; }
.placeholder p { font-size: 0.7rem; margin: 4px 0 0 0; line-height: 1.1; }

.svg-render { width: 100%; height: 100%; padding: 6px; display: flex; justify-content: center; align-items: center; }
.svg-render :deep(svg) { max-width: 100%; max-height: 100%; object-fit: contain; }

.fields-zone { flex: 1; display: flex; flex-direction: column; gap: 8px; }

.field-group { display: flex; flex-direction: column; }
.field-group label { font-size: 0.75rem; color: #666; margin-bottom: 2px; }
.field-group input {
  padding: 5px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.85rem;
  height: 28px;
  box-sizing: border-box;
}

/* Компактная инпут-группа SMILES */
.smiles-input-group {
  display: flex;
  width: 100%;
}
.smiles-compact-input {
  flex: 1;
}

/* Сетка метрик: 3 колонки вместо 2 ужимают высоту в полтора раза */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

/* Оформление инпутов чтения */
input:disabled {
  border-color: #ddd !important;
  background: #fff !important;
  color: #333;
  font-weight: 500;
  cursor: default;
}

.mass-highlight input {
  background: #fffdf0 !important; /* Мягкий янтарный фон */
  border-color: #f39c12 !important; /* Насыщенная рамка */
  font-weight: bold;
  color: #333;
}
.readonly input { background: #f9f9f9; color: #333; }
.yield-input { background: #e8f5e9 !important; font-weight: bold; color: #2e7d32; border-radius: 4px; border: 1px solid #c8e6c9 !important; text-align: center; }

/* Нижний ряд: условия и выход */
.card-footer-row {
  display: flex;
  gap: 15px;
  padding: 0 15px 15px 15px;
  margin-top: 5px;
}
.conditions-field { flex: 1; }
.yield-field { width: 120px; }

/* Модалка Ketcher */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 2000; display: flex; align-items: center; justify-content: center; }
.modal-content { width: 85%; height: 85%; background: white; display: flex; flex-direction: column; border-radius: 8px; overflow: hidden; }
.ketcher-frame { flex: 1; border: none; }
.modal-header { padding: 10px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; }
.btn-apply { background: #42b983; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-cancel { background: #999; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }

@media (max-width: 768px) {
  .card-body { flex-direction: column; }
  .structure-zone { width: 100%; height: 140px; }
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
  .card-footer-row { flex-direction: column; gap: 10px; }
  .yield-field { width: 100%; }
}

.date-field { width: 140px; }
@media (max-width: 768px) { .date-field { width: 100%; } }
</style>