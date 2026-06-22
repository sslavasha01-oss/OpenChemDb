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
        <div v-else class="svg-render" v-html="isolatedSvg"></div>
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

        <div class="field-group mass-highlight" :class="{ readonly: index !== 1 }">
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

        <div class="field-group readonly volume-highlight">
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
import { ref, nextTick, computed} from 'vue'

let debounceTimer = null

const props = defineProps({
  modelValue: Object,
  index: Number,
  isEditing: Boolean
})

// Вычисляемое свойство, которое гарантирует уникальность ID
// при ЛЮБОМ изменении данных (из базы, из Кетчера, откуда угодно)
const isolatedSvg = computed(() => {
  const rawSvg = props.modelValue?.[`reagent${props.index}_svg`];
  if (!rawSvg) return '';

  const prefix = `reagent-card-${props.index}`;

  // Изолируем ID, href и url() "на лету" прямо перед рендером в DOM
  return rawSvg
    .replace(/id=["']([^"']+)["']/g, (match, id) => `id="${prefix}-${id}"`)
    .replace(/href=["']#([^"']+)["']/g, (match, href) => `href="#${prefix}-${href}"`)
    .replace(/url\(#([^)]+)\)/g, (match, url) => `url(#${prefix}-${url})`);
});

const emit = defineEmits(['update:modelValue', 'calculate'])

const showKetcher = ref(false)

const ketcherToBackground = () => {
  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  if (globalFrame) {
    globalFrame.style.cssText = "position: fixed; top: -5000px; left: -5000px; width: 1000px; height: 800px; visibility: visible; border: none; pointer-events: none;";
  }
}

const onSmilesInput = (e) => {
  const newSmiles = e.target.value
  const updatedValue = { ...props.modelValue };
  updatedValue[`reagent${props.index}_smiles`] = newSmiles;
  emit('update:modelValue', updatedValue);

  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    console.log(`[ReagentCard #${props.index}] Ввод затих, запускаем drawSmiles для: ${newSmiles}`);
    drawSmiles(newSmiles);
  }, 400);
}

const copyToClipboard = (text) => {
  if (navigator && navigator.clipboard) {
    navigator.clipboard.writeText(text);
    alert('SMILES copied to clipboard!');
  }
}

let lastRenderedSmiles = '';

// 2. Фоновая отрисовка с детальным логированием шагов
const drawSmiles = async (smiles) => {
  const timestamp = Date.now();
  console.time(`[Draw Performance #${props.index}-${timestamp}]`);

  const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe')
  if (smiles === lastRenderedSmiles && smiles !== '') return;
  lastRenderedSmiles = smiles;

  if (!smiles || smiles.trim() === "") {
    console.log(`[ReagentCard #${props.index}] Пустой SMILES, очищаем поле.`);
    const ketcher = window.ketcherSingleton ||
                    globalFrame?.contentWindow?.ketcher ||
                    document.getElementById('global-ketcher-iframe')?.contentWindow?.ketcher;
    if (ketcher && typeof ketcher.setMolecule === 'function') ketcher.setMolecule("");

    const updated = { ...props.modelValue };
    updated[`reagent${props.index}_svg`] = '';
    updated[`reagent${props.index}_molar_mass`] = '';
    emit('update:modelValue', updated);
    emit('calculate');
    console.timeEnd(`[Draw Performance #${props.index}-${timestamp}]`);
    return;
  }

  const tryDraw = (attempts = 0) => {
    const ketcher = window.ketcherSingleton ||
                    globalFrame?.contentWindow?.ketcher ||
                    document.getElementById('global-ketcher-iframe')?.contentWindow?.ketcher;

    if (window.ketcherIsBusy) {
      if (attempts < 10) {
        setTimeout(() => tryDraw(attempts + 1), 200);
      }
      return;
    }

    if (ketcher && typeof ketcher.setMolecule === 'function') {
      if (!window.ketcherSingleton) window.ketcherSingleton = ketcher;

      // Занимаем Кетчер
      window.ketcherIsBusy = true;
      console.log(`[Lock Acquired] Реагент #${props.index} монополизировал Кетчер.`);

      (async () => {
        try {
          console.log(`[Ketcher API] Передаем SMILES в setMolecule для #${props.index}`);
          await ketcher.setMolecule("");
          await ketcher.setMolecule(smiles);

          console.log(`[Ketcher API] Запрашиваем generateImage SVG для #${props.index}`);
          const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });
          const rawSvgText = await blob.text();

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
          updated[`reagent${props.index}_svg`] = rawSvgText;

          if (massVal) {
            const totalMass = String(massVal)
              .split(';')
              .reduce((sum, part) => {
                const num = parseFloat(part.trim());
                return sum + (isNaN(num) ? 0 : num);
              }, 0);
            updated[`reagent${props.index}_molar_mass`] = totalMass.toFixed(2);
          }

          console.log(`[Vue Lifecycle] Эмитим обновленный SVG наверх для #${props.index}`);
          emit('update:modelValue', updated);

          nextTick(() => {
            emit('calculate');
          });

          setTimeout(() => {
            try {
              if (typeof ketcher.setZoom === 'function') ketcher.setZoom(1.0);
              else if (ketcher.editor?.setZoom) ketcher.editor.setZoom(1.0);
            } catch (e) {}
          }, 50);

        } catch (err) {
          console.error(`[Fatal Draw Error] Ошибка в карточке реагента #${props.index}:`, err);
        } finally {
          // Освобождаем Кетчер
          window.ketcherIsBusy = false;
          console.log(`[Lock Released] Реагент #${props.index} освободил Кетчер.`);
          console.timeEnd(`[Draw Performance #${props.index}-${timestamp}]`);
        }
      })();
    } else if (attempts < 15) {
      setTimeout(() => tryDraw(attempts + 1), 100);
    } else {
      console.error(`[Timeout] Не удалось дождаться инициализации Кетчера для реагента #${props.index}`);
      console.timeEnd(`[Draw Performance #${props.index}-${timestamp}]`);
    }
  };
  tryDraw();
};

defineExpose({ drawSmiles });

const openEditor = async () => {
  showKetcher.value = true;
  await nextTick();

  setTimeout(async () => {
    const globalFrame = window.ketcherIframeElement || document.getElementById('global-ketcher-iframe');
    const marker = document.getElementById(`reagent-ketcher-placeholder-${props.index}`);

    if (globalFrame && marker) {
      let rect = marker.getBoundingClientRect();
      if (rect.height < 100) {
        const modalContent = marker.closest('.modal-content');
        if (modalContent) {
          const modalRect = modalContent.getBoundingClientRect();
          rect = {
            top: modalRect.top + 55,
            left: modalRect.left + 2,
            width: modalRect.width - 4,
            height: modalRect.height - 60
          };
        }
      }

      globalFrame.style.cssText = `
        position: fixed;
        top: ${rect.top}px;
        left: ${rect.left}px;
        width: ${rect.width}px;
        height: ${rect.height}px;
        border: none;
        visibility: visible;
        display: block;
        pointer-events: auto;
        z-index: 2100;
      `;
    }

    const checkAndSet = async () => {
      const ketcher = window.ketcherSingleton ||
                    globalFrame?.contentWindow?.ketcher ||
                    document.getElementById('global-ketcher-iframe')?.contentWindow?.ketcher;
      if (ketcher && typeof ketcher.setMolecule === 'function') {
        if (!window.ketcherSingleton) window.ketcherSingleton = ketcher;
        const smiles = props.modelValue[`reagent${props.index}_smiles`];
        try { await ketcher.setMolecule(""); } catch (e) {}
        if (smiles && smiles.trim() !== "") { await ketcher.setMolecule(smiles); }
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
  }, 30);
};

const saveFromKetcher = async () => {
  try {
    const ketcher = window.ketcherSingleton
    if (!ketcher) return;

    const smiles = await ketcher.getSmiles();
    const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });
    const rawSvgText = await blob.text();

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
    updated[`reagent${props.index}_svg`] = rawSvgText;

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
    nextTick(() => { emit('calculate'); });
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

/* Стилизация для disabled полей (возвращаем полноценный вид инпута) */
input:disabled {
  border-color: #ddd !important;
  background: #fff !important;
  color: #333;
  font-weight: 500;
  cursor: default;
}
input:disabled[value=""],
input:disabled:not([value]) {
  opacity: 1; /* Убираем прозрачность для пустых полей */
}
.readonly input { background: #f9f9f9; color: #333; }

/* Выделение критических параметров загрузки реактора */
.mass-highlight input,
.volume-highlight input {
  background: #fffdf0 !important; /* Мягкий янтарный фон */
  border-color: #f39c12 !important; /* Четкая золотая рамка */
  font-weight: bold;
  color: #333;
}

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