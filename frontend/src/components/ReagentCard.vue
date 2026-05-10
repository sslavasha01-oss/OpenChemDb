<template>
  <div class="card reagent-card" :class="{ 'limiting-reagent': index === 1 }">
    <div class="card-header">
      Реагент {{ index }} {{ index === 1 ? '(Лимитирующий)' : '' }}
    </div>

    <div class="card-body">
      <!-- Структура (маленькая, так как карточка вертикальная) -->
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

      <!-- Поля ввода (вертикальный список) -->
      <div class="fields-column">
        <div class="field-group">
          <label>SMILES</label>
          <input
            type="text"
            :value="modelValue[`reagent${index}_smiles`]"
            @input="onSmilesInput"
            :disabled="!isEditing"
          >
        </div>

        <div class="field-group readonly">
          <label>M.W.</label>
          <input type="number" :value="modelValue[`reagent${index}_molar_mass`]" disabled>
        </div>

        <!-- Масса: для 1-го редактируемая, для остальных - расчетная -->
        <div class="field-group" :class="{ readonly: index !== 1 }">
          <label>Масса (г)</label>
          <input
            type="number"
            v-model.number="modelValue[`reagent${index}_mass`]"
            :disabled="!isEditing || index !== 1"
            @input="$emit('update:modelValue', modelValue)"
            step="0.001"
          >
        </div>

        <div class="field-group readonly">
          <label>Моли</label>
          <input type="number" :value="modelValue[`reagent${index}_moles`]" disabled>
        </div>

        <div class="field-group">
          <label>Плотность (г/мл)</label>
          <input
            type="number"
            v-model.number="modelValue[`reagent${index}_density`]"
            :disabled="!isEditing"
            @input="$emit('update:modelValue', modelValue)"
            step="0.001"
          >
        </div>

        <div class="field-group">
          <label>Конц. (доля)</label>
          <input
            type="number"
            v-model.number="modelValue[`reagent${index}_concentration`]"
            :disabled="!isEditing"
            step="0.01"
            @input="$emit('update:modelValue', modelValue)"
          >
        </div>

        <div class="field-group readonly">
          <label>Объем (мл)</label>
          <input type="number" :value="modelValue[`reagent${index}_volume`]" disabled>
        </div>

        <div class="field-group">
          <label>Экв.</label>
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

    <!-- Модалка (используем тот же подход, что в продукте) -->
    <div v-show="showKetcher" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Редактор реагента {{ index }}</h3>
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
  index: Number, // 1, 2, 3, 4, 5
  isEditing: Boolean
})

const emit = defineEmits(['update:modelValue'])

const showKetcher = ref(false)
const ketcherFrame = ref(null)

const onSmilesInput = (e) => {
  const newSmiles = e.target.value
  const updated = { ...props.modelValue }
  updated[`reagent${props.index}_smiles`] = newSmiles
  emit('update:modelValue', updated)
}

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

const saveFromKetcher = async () => {
  console.log(`--- Debug Start: Reagent ${props.index} ---`);
  try {
    const ketcher = ketcherFrame.value?.contentWindow?.ketcher;
    if (!ketcher) {
      console.error("Ketcher instance not found in iframe");
      return;
    }

    // 1. Извлекаем SMILES
    const smiles = await ketcher.getSmiles();

    // 2. Генерируем превью SVG
    const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });
    const svgText = await blob.text();

    // 3. Пытаемся получить Molfile для точного расчета веса
    const molfile = await ketcher.getMolfile();

    let massVal = null;

    if (ketcher.structService) {
      console.log("Calling structService.calculate...");
      try {
        // Пробуем передать именно Molfile, так как в нем четко разделены фрагменты
        const result = await ketcher.structService.calculate({
          struct: molfile,
          properties: ['molecular-weight']
        });

        console.log("Full calculation result object:", result);
        massVal = result?.['molecular-weight'];
        console.log("Extracted M.W.:", massVal);
      } catch (calcError) {
        console.error("StructService calculation failed:", calcError);
      }
    } else {
      console.warn("Ketcher structService is not available");
    }

    // 4. Подготовка объекта для обновления
    const updated = { ...props.modelValue };

    // Используем пока старые ключи, как ты и просил
    updated[`reagent${props.index}_smiles`] = smiles;
    updated[`reagent${props.index}_svg`] = svgText;

    if (massVal) {
      // Если в строке несколько масс (через ';'), разбиваем их и суммируем
      const totalMass = String(massVal)
        .split(';')
        .reduce((sum, part) => {
          const num = parseFloat(part.trim());
          return sum + (isNaN(num) ? 0 : num);
        }, 0);

      const parsedMass = totalMass.toFixed(2);
      updated[`reagent${props.index}_molar_mass`] = parsedMass;
      console.log("Calculated Total M.W. (Sum):", parsedMass);
    } else {
      console.warn("Molar mass is null, field will not be updated");
    }

    console.log("Final object to emit:", updated);
    emit('update:modelValue', updated);

  } catch (err) {
    console.error("Global saveFromKetcher error:", err);
  } finally {
    console.log(`--- Debug End: Reagent ${props.index} ---`);
    showKetcher.value = false;
  }
}

const openEditor = async () => {
  showKetcher.value = true
  await nextTick()
  const ketcher = ketcherFrame.value?.contentWindow?.ketcher
  const currentSmiles = props.modelValue[`reagent${props.index}_smiles`]
  if (ketcher && currentSmiles) {
    setTimeout(() => ketcher.setMolecule(currentSmiles), 200)
  }
}
</script>

<style scoped>
.reagent-card {
  width: 100%; /* Теперь ширину контролирует сетка родителя */
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  transition: transform 0.2s;
}
.limiting-reagent { border: 2px solid #42b983; }
.limiting-reagent .card-header { background: #42b983; }

/* Убираем рамку в режиме чтения, оставляем только легкую тень */
.reagent-card:not(.limiting-reagent) {
  border: 1px solid #eee;
}

.card-header {
  padding: 8px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #eee;
  border-radius: 8px 8px 0 0;
  font-weight: bold;
  font-size: 0.9rem;
  text-align: center;
}

.structure-zone-mini {
  height: 140px; /* Чуть увеличим для наглядности */
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  margin-bottom: 5px;
}

.field-group input {
  padding: 6px;
  border: 1px solid #ececec;
  background: #fff;
}

/* Скрываем границы инпутов в режиме чтения, чтобы выглядело как текст */
input:disabled {
  border-color: transparent !important;
  background: transparent !important;
  color: #333;
  font-weight: 500;
  cursor: default;
}

/* Если поле пустое и мы не редактируем — можно его вообще притушить */
input:disabled[value=""],
input:disabled:not([value]) {
  opacity: 0.3;
}

.card-body { padding: 10px; display: flex; flex-direction: column; gap: 10px; }

.structure-zone-mini {
  height: 120px;
  background: #fff;
  border: 1px dashed #ccc;
  border-radius: 4px;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.fields-column { display: flex; flex-direction: column; gap: 6px; }

.field-group { display: flex; flex-direction: column; }
.field-group label { font-size: 0.7rem; color: #777; }
.field-group input { padding: 4px; font-size: 0.85rem; border: 1px solid #ddd; border-radius: 4px; }

.readonly input { background: #f9f9f9; color: #666; }

.svg-render { width: 100%; height: 100%; }
.svg-render :deep(svg) { width: 100%; height: 100%; }

/* Копируем стили модалки из ProductCard или выносим в общий CSS */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 2000; display: flex; align-items: center; justify-content: center; }
.modal-content { width: 80%; height: 80%; background: white; border-radius: 8px; display: flex; flex-direction: column; }
.ketcher-frame { flex: 1; border: none; }
.modal-header { padding: 10px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; }
.btn-apply { background: #42b983; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }
.btn-cancel { background: #999; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }
</style>