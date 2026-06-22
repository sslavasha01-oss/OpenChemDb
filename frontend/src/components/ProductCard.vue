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

// 2. Фоновая отрисовка структуры и расчет молярной массы продукта
const drawSmiles = async (smiles) => {
  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  if (smiles === lastRenderedSmiles && smiles !== '') return;
  lastRenderedSmiles = smiles;
  if (!smiles || smiles.trim() === "") {
    const ketcher = window.ketcherSingleton ||
                    globalFrame?.contentWindow?.ketcher ||
                    document.getElementById('global-ketcher-iframe')?.contentWindow?.ketcher;
    if (ketcher && typeof ketcher.setMolecule === 'function') ketcher.setMolecule("");

    const updated = { ...props.modelValue };
    updated.product_preview_svg = '';
    updated.product_molar_mass = '';
    emit('update:modelValue', updated);
    emit('calculate');
    return;
  }

  const tryDraw = (attempts = 0) => {
    if (window.ketcherIsBusy) {
         if (attempts < 50) setTimeout(() => tryDraw(attempts + 1), 200);
    return;
    }
    const ketcher = window.ketcherSingleton ||
                    globalFrame?.contentWindow?.ketcher ||
                    document.getElementById('global-ketcher-iframe')?.contentWindow?.ketcher;

    if (ketcher && typeof ketcher.setMolecule === 'function') {
      if (!window.ketcherSingleton) window.ketcherSingleton = ketcher;

      (async () => {
        try {
          await ketcher.setMolecule(smiles);
          const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });
          const svgText = await blob.text();

          const molfile = await ketcher.getMolfile();
          let massVal = null;

          if (ketcher.structService) {
            try {
              const result = await ketcher.structService.calculate({
                struct: molfile,
                properties: ['molecular-weight']
              });
              massVal = result?.['molecular-weight'];
            } catch (calcError) {
              console.error("Product background calculation failed:", calcError);
            }
          }

          const updated = { ...props.modelValue };
          updated.product_preview_svg = svgText;

          if (massVal) {
            const totalMass = String(massVal)
              .split(';')
              .reduce((sum, part) => {
                const num = parseFloat(part.trim());
                return sum + (isNaN(num) ? 0 : num);
              }, 0);

            updated.product_molar_mass = totalMass.toFixed(2);
          }

          emit('update:modelValue', updated);

          nextTick(() => {
            emit('calculate');
          });

          // Фикс зума для фоновой отрисовки
          setTimeout(() => {
            try {
              if (typeof ketcher.setZoom === 'function') ketcher.setZoom(1.0);
              else if (ketcher.editor?.setZoom) ketcher.editor.setZoom(1.0);
            } catch (e) {}
          }, 50);
        } catch (err) {
          console.error("[Product Draw Error]:", err);
        }
      })();
    } else if (attempts < 25) {
      setTimeout(() => tryDraw(attempts + 1), 100);
    }
  };
  tryDraw();
};

defineExpose({ drawSmiles });

// 4. Сохранение изменений из глобального Кетчера
const saveFromKetcher = async () => {
  try {
    const ketcher = window.ketcherSingleton
    if (!ketcher) return;

    const smiles = await ketcher.getSmiles();
    const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });
    const svgText = await blob.text();
    const molfile = await ketcher.getMolfile();

    let massVal = null;

    if (ketcher.structService) {
      try {
        const result = await ketcher.structService.calculate({
          struct: molfile,
          properties: ['molecular-weight']
        });
        massVal = result?.['molecular-weight'];
      } catch (calcError) {
        console.error("StructService calculation failed:", calcError);
      }
    }

    const updatedValue = { ...props.modelValue };
    updatedValue.product_smiles = smiles;
    updatedValue.product_preview_svg = svgText;

    if (massVal) {
      const totalMass = String(massVal)
        .split(';')
        .reduce((sum, part) => {
          const num = parseFloat(part.trim());
          return sum + (isNaN(num) ? 0 : num);
        }, 0);

      updatedValue.product_molar_mass = totalMass.toFixed(2);
    }

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

      try {
        if (typeof ketcher.setZoom === 'function') ketcher.setZoom(1.0);
        else if (ketcher.editor && typeof ketcher.editor.setZoom === 'function') ketcher.editor.setZoom(1.0);
      } catch (e) {}

      if (ketcher.editor?.centerXy) ketcher.editor.centerXy();

      // <- ИСПРАВЛЕНО: Принудительно передаем фокус ввода внутрь фрейма,
      // чтобы клавиатурные сокращения и холст сразу стали активными
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