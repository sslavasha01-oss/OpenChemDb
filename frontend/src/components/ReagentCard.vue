<template>
  <div class="card reagent-card" :class="{ 'limiting-reagent': index === 1 }">
    <div class="card-header">
      Reagent {{ index }} {{ index === 1 ? '(Limiting)' : '' }}
    </div>

    <div class="card-body">
      <div
        class="structure-zone-mini"
        :class="{ 'editable-zone': isEditing }"
        @click="isEditing && openEditor()"
      >
        <div v-if="!modelValue[`reagent${index}_svg`]" class="placeholder-mini">
          <span>⚗️</span>
        </div>
        <div v-else class="svg-render" v-html="modelValue[`reagent${index}_svg`]"></div>
      </div>

      <div class="fields-column">

        <div class="field-group">
          <label>SMILES</label>
          <div class="smiles-input-group">
            <input
              type="text"
              :value="modelValue[`reagent${index}_smiles`]"
              @input="onSmilesInput"
              :disabled="!isEditing"
              placeholder="C1=CC=..."
              class="smiles-compact-input"
            >
            <button
              v-if="modelValue[`reagent${index}_smiles`]"
              type="button"
              class="btn-copy-smiles"
              @click.stop="copyToClipboard(modelValue[`reagent${index}_smiles`])"
              title="Copy SMILES"
            >
              📋
            </button>
          </div>
        </div>

        <div class="field-group readonly">
          <label>M.W.</label>
          <input type="number" :value="modelValue[`reagent${index}_molar_mass`]" disabled>
        </div>

        <div class="field-group" :class="{ readonly: index !== 1 }">
          <label>Mass (g)</label>
          <input
            type="number"
            v-model.number="modelValue[`reagent${index}_mass`]"
            :disabled="!isEditing || index !== 1"
            @input="$emit('update:modelValue', modelValue)"
            step="0.001"
          >
        </div>

        <div class="field-group readonly">
          <label>Moles</label>
          <input type="number" :value="modelValue[`reagent${index}_moles`]" disabled>
        </div>

        <div class="field-group">
          <label>Density (g/mL)</label>
          <input
            type="number"
            v-model.number="modelValue[`reagent${index}_density`]"
            :disabled="!isEditing"
            @input="$emit('update:modelValue', modelValue)"
            step="0.001"
          >
        </div>

        <div class="field-group">
          <label>Conc. (fraction)</label>
          <input
            type="number"
            v-model.number="modelValue[`reagent${index}_concentration`]"
            :disabled="!isEditing"
            step="0.01"
            @input="$emit('update:modelValue', modelValue)"
          >
        </div>

        <div class="field-group readonly">
          <label>Volume (mL)</label>
          <input type="number" :value="modelValue[`reagent${index}_volume`]" disabled>
        </div>

        <div class="field-group">
          <label>Eq.</label>
          <input
            type="number"
            v-model.number="modelValue[`reagent${index}_molar_ekv`]"
            :disabled="!isEditing"
            step="0.01"
            @input="$emit('update:modelValue', modelValue)"
          >
        </div>
      </div>
    </div>

    <!-- Модальное окно использует CSS-телепорт глобального фрейма -->
    <div v-show="showKetcher" class="modal-overlay" style="z-index: 2000;">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Reagent {{ index }} Editor</h3>
          <div class="modal-btns">
            <button @click="saveFromKetcher" class="btn-apply">Apply</button>
            <button @click="closeEditorWithoutSaving" class="btn-cancel">Cancel</button>
          </div>
        </div>
        <!-- Маркер-ориентир для глобального фрейма -->
        <div :id="`reagent-ketcher-placeholder-${index}`" class="ketcher-frame" style="background: transparent;"></div>
      </div>
    </div>
    </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

let debounceTimer = null

const props = defineProps({
  modelValue: Object,
  index: Number,
  isEditing: Boolean
})

const emit = defineEmits(['update:modelValue', 'calculate'])

const showKetcher = ref(false)
// Вспомогательная функция отправки глобального фрейма обратно в "подполье"
const ketcherToBackground = () => {
  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  if (globalFrame) {
    globalFrame.style.cssText = "position: fixed; top: -5000px; left: -5000px; width: 800px; height: 600px; visibility: visible; z-index: -1000; pointer-events: none; border: none;"
  }
}

// 1. Обработка ручного ввода SMILES
const onSmilesInput = (e) => {
  const newSmiles = e.target.value

  const updatedValue = { ...props.modelValue };
  updatedValue[`reagent${props.index}_smiles`] = newSmiles;
  emit('update:modelValue', updatedValue);

  // Сбрасываем старый таймер, если пользователь продолжает печатать
  clearTimeout(debounceTimer);

  // Запускаем отрисовку и пересчет стехиометрии только при паузе в 400мс
  debounceTimer = setTimeout(() => {
    drawSmiles(newSmiles);
  }, 400);
}

// Копирование в буфер
const copyToClipboard = (text) => {
  if (navigator && navigator.clipboard) {
    navigator.clipboard.writeText(text);
    alert('SMILES copied to clipboard!');
  }
}

// 2. Фоновая отрисовка и расчет при РУЧНОМ вводе (использует единый глобальный фрейм)
const drawSmiles = async (smiles) => {
  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')

  if (!smiles || smiles.trim() === "") {
    const ketcher = window.ketcherSingleton || globalFrame?.contentWindow?.ketcher;
    if (ketcher && typeof ketcher.setMolecule === 'function') ketcher.setMolecule("");

    const updated = { ...props.modelValue };
    updated[`reagent${props.index}_svg`] = '';
    updated[`reagent${props.index}_molar_mass`] = '';
    emit('update:modelValue', updated);
    emit('calculate');
    return;
  }

  const tryDraw = (attempts = 0) => {
    const ketcher = window.ketcherSingleton || globalFrame?.contentWindow?.ketcher;

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
              console.error("Background mass calculation failed:", calcError);
            }
          }

          const updated = { ...props.modelValue };
          updated[`reagent${props.index}_svg`] = svgText;

          if (massVal) {
            const totalMass = String(massVal)
              .split(';')
              .reduce((sum, part) => {
                const num = parseFloat(part.trim());
                return sum + (isNaN(num) ? 0 : num);
              }, 0);

            updated[`reagent${props.index}_molar_mass`] = totalMass.toFixed(2);
          }

          emit('update:modelValue', updated);

          nextTick(() => {
            emit('calculate');
          });

          // Фикс масштаба
          setTimeout(() => {
            try {
              if (typeof ketcher.setZoom === 'function') ketcher.setZoom(1.0);
              else if (ketcher.editor?.setZoom) ketcher.editor.setZoom(1.0);
            } catch (e) {}
          }, 50);

        } catch (err) {
          console.error("Reagent Draw Error:", err);
        }
      })();
    } else if (attempts < 15) {
      setTimeout(() => tryDraw(attempts + 1), 100);
    }
  };
  tryDraw();
};

defineExpose({ drawSmiles });

// 3. Безопасное открытие редактора через CSS-телепорт
const openEditor = async () => {
  showKetcher.value = true;

  // Даем Vue обновить DOM, а затем делаем микроскопическую паузу для отрисовки браузером
  await nextTick();

  setTimeout(async () => {
    const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe');
    const marker = document.getElementById(`reagent-ketcher-placeholder-${props.index}`);

    if (globalFrame && marker) {
      // На всякий случай проверяем, если маркер схлопнулся, берем размеры модалки
      let rect = marker.getBoundingClientRect();

      // Если браузер еще не успел посчитать высоту флекс-контейнера
      if (rect.height < 100) {
        const modalContent = marker.closest('.modal-content');
        if (modalContent) {
          const modalRect = modalContent.getBoundingClientRect();
          // Высота модалки минус примерная высота шапки (60px)
          rect = {
            top: modalRect.top + 55,
            left: modalRect.left + 2,
            width: modalRect.width - 4,
            height: modalRect.height - 60
          };
        }
      }

      // Перемещаем фрейм точно в цель
      globalFrame.style.cssText = `
        position: fixed;
        top: ${rect.top}px;
        left: ${rect.left}px;
        width: ${rect.width}px;
        height: ${rect.height}px;
        border: none;
        visibility: visible;
        display: block;
        pointer-events: auto; /* Гарантируем кликабельность Кетчера */
        z-index: 2100; /* Выше оверлея модалки */
      `;
    }

    // Загружаем структуру
    const checkAndSet = async () => {
      const ketcher = window.ketcherSingleton || globalFrame?.contentWindow?.ketcher;
      if (ketcher && typeof ketcher.setMolecule === 'function') {
        if (!window.ketcherSingleton) window.ketcherSingleton = ketcher;

        const smiles = props.modelValue[`reagent${props.index}_smiles`];

        // Очищаем редактор перед установкой, чтобы старые хвосты не наслаивались
        try {
          await ketcher.setMolecule("");
        } catch (e) {}

        if (smiles && smiles.trim() !== "") {
          await ketcher.setMolecule(smiles);
        }

        // Фиксируем масштаб и центрируем
        setTimeout(() => {
          try {
            if (typeof ketcher.setZoom === 'function') ketcher.setZoom(1.0);
            else if (ketcher.editor?.setZoom) ketcher.editor.setZoom(1.0);

            if (ketcher.editor?.centerXy) ketcher.editor.centerXy();
          } catch (zoomErr) {}
        }, 50);

      } else {
        setTimeout(checkAndSet, 50);
      }
    };
    checkAndSet();
  }, 30); // 30мс задержки как раз хватает, чтобы убрать эффект "нулевых координат"
};

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

    const updated = { ...props.modelValue };
    updated[`reagent${props.index}_smiles`] = smiles;
    updated[`reagent${props.index}_svg`] = svgText;

    if (massVal) {
      const totalMass = String(massVal)
        .split(';')
        .reduce((sum, part) => {
          const num = parseFloat(part.trim());
          return sum + (isNaN(num) ? 0 : num);
        }, 0);

      updated[`reagent${props.index}_molar_mass`] = totalMass.toFixed(2);
    }

    emit('update:modelValue', updated);

    nextTick(() => {
      emit('calculate');
    });

  } catch (err) {
    console.error("Global saveFromKetcher error:", err);
  } finally {
    ketcherToBackground();
    showKetcher.value = false;
  }
}

const closeEditorWithoutSaving = () => {
  ketcherToBackground();
  showKetcher.value = false;
}
</script>

<style scoped>
.reagent-card {
  width: 100%;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.limiting-reagent { border: 2px solid #42b983; }
.limiting-reagent .card-header { background: #42b983; color: white; }

.card-header {
  padding: 8px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #eee;
  border-radius: 6px 6px 0 0;
  font-weight: bold;
  font-size: 0.9rem;
  text-align: center;
  color: #333;
}

.card-body { padding: 10px; display: flex; flex-direction: column; gap: 8px; }

/* Чистая зона картинки без лишних элементов внутри */
.structure-zone-mini {
  height: 120px;
  background: #fff;
  border: 1px dashed #ccc;
  border-radius: 4px;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  box-sizing: border-box;
}
.editable-zone:hover {
  border-color: #42b983;
  background: #fafffd;
  cursor: pointer;
}
.placeholder-mini { font-size: 1.5rem; opacity: 0.5; }
.svg-render { width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }
.svg-render :deep(svg) { max-width: 100%; max-height: 100%; object-fit: contain; }

.fields-column { display: flex; flex-direction: column; gap: 6px; }

.field-group { display: flex; flex-direction: column; }
.field-group label { font-size: 0.7rem; color: #777; margin-bottom: 1px; }
.field-group input { padding: 4px 6px; font-size: 0.85rem; border: 1px solid #ddd; border-radius: 4px; height: 28px; box-sizing: border-box; }

/* Группа для инпута SMILES и кнопки копирования */
.smiles-input-group {
  display: flex;
  width: 100%;
}
.smiles-compact-input {
  flex: 1;
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  border-right: none !important;
}
.btn-copy-smiles {
  background: #f4f6f7;
  border: 1px solid #ddd;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  cursor: pointer;
  padding: 0 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  height: 28px;
  box-sizing: border-box;
}
.btn-copy-smiles:hover {
  background: #e5e8e9;
}

/* Стилизация для disabled полей */
input:disabled {
  border-color: transparent !important;
  background: transparent !important;
  color: #333;
  font-weight: 500;
  cursor: default;
  padding-left: 2px !important;
}
input:disabled[value=""],
input:disabled:not([value]) {
  opacity: 0.3;
}
.readonly input { background: #f9f9f9; color: #666; }

/* Модалка Ketcher */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 2000; display: flex; align-items: center; justify-content: center; }
.modal-content { width: 80%; height: 80%; background: white; border-radius: 8px; display: flex; flex-direction: column; }
.ketcher-frame {
  flex: 1;
  border: none;
  min-height: 300px; /* Защита от схлопывания во flex-контексте */
  width: 100%;
}
.modal-header { padding: 10px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; }
.btn-apply { background: #42b983; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }
.btn-cancel { background: #999; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }
</style>