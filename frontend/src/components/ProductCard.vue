<template>
  <div class="card product-card">
    <div class="card-header">Продукт реакции</div>

    <div class="card-body">
      <!-- Зона структуры -->
      <div
        class="structure-zone"
        :class="{ 'editable-zone': isEditing }"
        @click="isEditing && openEditor()"
      >
        <div v-if="!modelValue.product_preview_svg" class="placeholder">
          <span class="icon">⚗️</span>
          <p>Нажмите, чтобы нарисовать</p>
        </div>
        <div v-else class="svg-render" v-html="modelValue.product_preview_svg"></div>
      </div>

      <!-- Поля данных -->
      <div class="fields-zone">
        <div class="field-group">
          <label>SMILES</label>
          <input
            type="text"
            :value="modelValue.product_smiles"
            @input="onSmilesInput"
            :disabled="!isEditing"
            placeholder="C1=CC=CC=C1..."
          >
        </div>

        <div class="metrics-grid">
          <div class="field-group readonly">
            <label>M.W. (г/моль)</label>
            <input type="number" :value="modelValue.product_molar_mass" disabled>
          </div>

          <div class="field-group">
            <label>Экв.</label>
            <input
              type="number"
              v-model.number="modelValue.product_molar_ekv"
              :disabled="!isEditing"
              step="0.01"
            >
          </div>

          <div class="field-group">
            <label>Практ. масса (г)</label>
            <input
              type="number"
              v-model.number="modelValue.product_praktical_mass"
              :disabled="!isEditing"
              step="0.001"
            >
          </div>

          <div class="field-group readonly">
            <label>Моли</label>
            <input type="number" :value="modelValue.product_moles" disabled>
          </div>

          <div class="field-group readonly">
            <label>Теор. масса (г)</label>
            <input type="number" :value="modelValue.product_theoretical_mass" disabled>
          </div>

          <div class="field-group yield">
            <label>Выход (%)</label>
            <input type="number" :value="modelValue.product_yield_calc" disabled class="yield-input">
          </div>
        </div>
      </div>
    </div>

    <!-- Скрытый iframe для фоновой генерации SVG из SMILES -->
    <iframe
      v-show="false"
      ref="hiddenKetcher"
      src="/standalone/index.html?hidden_controls=all"
    ></iframe>

    <!-- Модалка редактора (без изменений, вызывается только по клику) -->
    <div v-show="showKetcher" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Редактор структуры продукта</h3>
          <div class="modal-btns">
            <button @click="saveFromKetcher" class="btn-apply">Применить</button>
            <button @click="showKetcher = false" class="btn-cancel">Отмена</button>
          </div>
        </div>
        <iframe ref="ketcherFrame" src="/standalone/index.html?hidden_controls=help,settings,save&api_path=/&allow_reaction=false" class="ketcher-frame"></iframe>
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

const showKetcher = ref(false)
const ketcherFrame = ref(null) // ОСТАВЛЯЕМ ТОЛЬКО ОДИН РАЗ
const isKetcherReady = ref(false)

const drawSmiles = async (smiles) => {
  if (!smiles || smiles.trim() === "") {
    const ketcher = ketcherFrame.value?.contentWindow?.ketcher;
    if (ketcher) ketcher.setMolecule("");
    // Очищаем превью, если смайлс пустой
    const updated = { ...props.modelValue };
    updated.product_preview_svg = '';
    emit('update:modelValue', updated);
    return;
  }

  const tryDraw = (attempts = 0) => {
    const frame = ketcherFrame.value;
    const ketcher = frame?.contentWindow?.ketcher;

    if (ketcher && typeof ketcher.setMolecule === 'function') {
      (async () => {
        try {
          // 1. Рисуем молекулу в скрытом фрейме
          await ketcher.setMolecule(smiles);

          // 2. Генерируем SVG код из того, что только что нарисовали
          const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });
          const svgText = await blob.text();

          // 3. Обновляем модель, чтобы v-html в шаблоне увидел картинку
          const updated = { ...props.modelValue };

          // Для ProductCard:
          if (props.index === undefined) {
             updated.product_preview_svg = svgText;
          } else {
             // Для ReagentCard (используем индекс):
             updated[`reagent${props.index}_svg`] = svgText;
          }

          emit('update:modelValue', updated);

          // 4. Масштаб
          setTimeout(() => {
            try {
              if (ketcher.setZoom) ketcher.setZoom(1.0);
              else if (ketcher.editor?.setZoom) ketcher.editor.setZoom(1.0);
            } catch (e) {}
          }, 150);

          console.log("[Card Debug] Drawing & Preview Generation SUCCESS");
        } catch (err) {
          console.error("[Card Debug] Draw/Preview FAILED:", err);
        }
      })();
    } else if (attempts < 25) {
      setTimeout(() => tryDraw(attempts + 1), 200);
    }
  };

  tryDraw();
};

defineExpose({ drawSmiles });

// В обработчике открытия окна (клик на картинку)
const openKetcher = () => {
  showModal.value = true;
  // Если Ketcher уже загружен, просто рисуем текущий смайлс
  if (isKetcherReady.value) {
    drawSmiles(props.modelValue.product_smiles);
  }
};

const emit = defineEmits(['update:modelValue', 'calculate'])

const hiddenKetcher = ref(null)

// 1. Обработка ручного ввода SMILES
const onSmilesInput = (e) => {
  const newSmiles = e.target.value
  // Правильный способ обновления v-model:
  const updatedValue = { ...props.modelValue, product_smiles: newSmiles };
  emit('update:modelValue', updatedValue);

  updateVisualsFromSmiles(newSmiles)
  // emit('calculate') уже не нужен, так как сработает watch в родителе
}

// 2. Универсальная функция обновления SVG и Массы
const updateVisualsFromSmiles = async (smiles) => {
  if (!smiles || smiles.trim() === '') {
    props.modelValue.product_preview_svg = ''
    props.modelValue.product_molar_mass = null
    return
  }

  // ИСПРАВЛЕНО: .value вместо .ref
  const frame = showKetcher.value ? ketcherFrame.value : hiddenKetcher.value
  const ketcher = frame?.contentWindow?.ketcher

  if (ketcher) {
    try {
      // 1. Устанавливаем молекулу в скрытый редактор
      await ketcher.setMolecule(smiles)

      // 2. Генерируем картинку
      const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' })
      props.modelValue.product_preview_svg = await blob.text()

      // 3. Получаем массу.
      // В Ketcher это обычно делается через getStructureInfo() или анализ Mol-файла
      const info = await ketcher.getStructureInfo()
      if (info && info.mass) {
        props.modelValue.product_molar_mass = parseFloat(info.mass).toFixed(2)
      }
    } catch (e) {
      console.warn("Ketcher Error:", e)
    }
  }
}

// 3. Сохранение из редактора
const saveFromKetcher = async () => {
  console.log("--- Debug Start: Product ---");
  try {
    const ketcher = ketcherFrame.value?.contentWindow?.ketcher;
    if (!ketcher) return;

    // 1. Получаем данные из редактора
    const smiles = await ketcher.getSmiles();
    const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });
    const svgText = await blob.text();
    const molfile = await ketcher.getMolfile();

    let massVal = null;

    // 2. Расчет массы через сервис
    if (ketcher.structService) {
      const result = await ketcher.structService.calculate({
        struct: molfile,
        properties: ['molecular-weight']
      });
      console.log("Product calculation result:", result);
      massVal = result?.['molecular-weight'];
    }

    // 3. Формируем обновленный объект
    const updatedValue = { ...props.modelValue };
    updatedValue.product_smiles = smiles;
    updatedValue.product_preview_svg = svgText; // Возвращаемся к стандартному полю

    if (massVal) {
      // Суммируем фрагменты, если их несколько (через ';')
      const totalMass = String(massVal)
        .split(';')
        .reduce((sum, part) => {
          const num = parseFloat(part.trim());
          return sum + (isNaN(num) ? 0 : num);
        }, 0);

      updatedValue.product_molar_mass = totalMass.toFixed(2);
      console.log("Calculated Total Product M.W.:", updatedValue.product_molar_mass);
    }

    // 4. Отправляем наверх
    emit('update:modelValue', updatedValue);

  } catch (err) {
    console.error("Error saving product from Ketcher:", err);
  } finally {
    console.log("--- Debug End: Product ---");
    showKetcher.value = false;
  }
};

const openEditor = async () => {
  showKetcher.value = true;
  await nextTick();

  // Даем Ketcher время "увидеть" размеры открывшейся модалки
  setTimeout(async () => {
    const ketcher = ketcherFrame.value?.contentWindow?.ketcher;
    if (ketcher && props.modelValue.product_smiles) {
      await ketcher.setMolecule(props.modelValue.product_smiles);
      // Вот здесь жестко ставим 100%
      if (ketcher.setZoom) ketcher.setZoom(1.0);
    }
  }, 200);
};
</script>

<style scoped>
.structure-zone {
  width: 300px;
  height: 250px;
  border: 1px solid #eee;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.2s;
}
.editable-zone:hover {
  border-color: #42b983;
  background: #fafffd;
  cursor: pointer;
}
.svg-render { width: 100%; height: 100%; padding: 10px; }
.svg-render :deep(svg) { width: 100%; height: 100%; }

.readonly input {
  background: #f0f0f0;
  border-color: #eee;
  color: #555;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.card {
  border: 1px solid #ccc;
  border-radius: 12px;
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
  padding: 15px;
}

.structure-zone {
  width: 250px;
  height: 200px;
  border: 1px dashed #bbb;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #fcfcfc;
}

.fields-zone { flex: 1; }
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 15px;
}

.field-group { display: flex; flex-direction: column; }
.field-group label { font-size: 0.8rem; color: #666; margin-bottom: 2px; }
.field-group input {
  padding: 6px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.yield-input { background: #e8f5e9; font-weight: bold; color: #2e7d32; }

/* Модалка Ketcher */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { width: 90%; height: 90%; background: white; display: flex; flex-direction: column; border-radius: 8px; }
.ketcher-frame { flex: 1; border: none; }

@media (max-width: 768px) {
  .card-body { flex-direction: column; }
  .structure-zone { width: 100%; }
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>