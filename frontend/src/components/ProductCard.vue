<template>

<div class="card product-card">

<div class="card-header">Продукт реакции</div>



<div class="card-body">

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

<label>M.W. (г/моль)</label>

<input type="number" :value="modelValue.product_molar_mass" disabled>

</div>



<div class="field-group">

<label>Практ. mass (г)</label>

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



<div class="field-group">

<label>Экв.</label>

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

<div class="field-group conditions-field">

<label>Условия реакции (Conditions)</label>

<input

type="text"

v-model="modelValue.conditions"

:disabled="!isEditing"

placeholder="EtOH, r.t., 2h, или Pd(PPh3)4, 80°C..."

>

</div>



<div class="field-group yield-field">

<label>Выход (%)</label>

<input type="number" :value="modelValue.product_yield_calc" disabled class="yield-input">

</div>

</div>



<iframe

v-show="false"

ref="hiddenKetcher"

src="/standalone/index.html?hidden_controls=all"

></iframe>



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



const emit = defineEmits(['update:modelValue', 'calculate'])



const showKetcher = ref(false)

const ketcherFrame = ref(null)

const hiddenKetcher = ref(null)



const onSmilesInput = (e) => {

const newSmiles = e.target.value



// Обновляем модель в родителе, чтобы данные не потерялись

const updatedValue = { ...props.modelValue, product_smiles: newSmiles };

emit('update:modelValue', updatedValue);



// Пингуем Ketcher, чтобы он перерисовал структуру и посчитал массу в фоне

drawSmiles(newSmiles);

}



const drawSmiles = async (smiles) => {

if (!smiles || smiles.trim() === "") {

const ketcher = ketcherFrame.value?.contentWindow?.ketcher;

if (ketcher) ketcher.setMolecule("");

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

await ketcher.setMolecule(smiles);

const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });

const svgText = await blob.text();



const updated = { ...props.modelValue };

updated.product_preview_svg = svgText;

emit('update:modelValue', updated);



setTimeout(() => {

try {

if (ketcher.setZoom) ketcher.setZoom(1.0);

else if (ketcher.editor?.setZoom) ketcher.editor.setZoom(1.0);

} catch (e) {}

}, 150);

} catch (err) {

console.error("[Product Draw Error]:", err);

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

try {

const ketcher = ketcherFrame.value?.contentWindow?.ketcher;

if (!ketcher) return;



const smiles = await ketcher.getSmiles();

const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });

const svgText = await blob.text();

const molfile = await ketcher.getMolfile();



let massVal = null;



if (ketcher.structService) {

const result = await ketcher.structService.calculate({

struct: molfile,

properties: ['molecular-weight']

});

massVal = result?.['molecular-weight'];

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

} catch (err) {

console.error("Error saving product:", err);

} finally {

showKetcher.value = false;

}

};



const openEditor = async () => {

showKetcher.value = true;

await nextTick();



const checkAndSet = async () => {

const ketcher = ketcherFrame.value?.contentWindow?.ketcher;

if (ketcher && ketcher.editor) {

const smiles = props.modelValue.product_smiles;

await ketcher.setMolecule(smiles || "");

ketcher.editor.setZoom(1.0);

if (ketcher.editor.centerXy) ketcher.editor.centerXy();

} else {

setTimeout(checkAndSet, 50);

}

};

checkAndSet();

};

</script>



<style scoped>

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

padding: 15px 15px 5px 15px; /* Уменьшили нижний отступ тела */

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

border-color: transparent !important;

background: transparent !important;

color: #333;

font-weight: 500;

cursor: default;

padding-left: 2px !important;

}

.readonly input { background: #f9f9f9; color: #666; }

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

</style>

