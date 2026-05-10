<template>
  <div class="journal-container">
    <!-- Навигация по вкладкам -->
    <nav class="tabs-nav">
      <button :class="{ active: activeTab === 'table' }" @click="activeTab = 'table'">Таблица</button>
      <button :class="{ active: activeTab === 'method' }" @click="activeTab = 'method'">Методика</button>
      <button :class="{ active: activeTab === 'search' }" @click="activeTab = 'search'">Поиск</button>
    </nav>

    <!-- Панель управления (только для методики) -->
    <div v-if="activeTab === 'method'" class="toolbar">
      <button @click="isEditing = true" :disabled="isEditing">Редактировать</button>
      <button @click="createNewEntry">Новая запись</button>
      <button @click="saveEntry" class="btn-save" :disabled="!isEditing">Сохранить</button>
    </div>

    <main class="tab-content">
      <!-- Вкладка Таблица -->
      <section v-if="activeTab === 'table'">
        <h2>Список записей</h2>
        <p>Здесь будет Table View...</p>
      </section>

      <!-- Вкладка Методика -->
      <section v-if="activeTab === 'method'" class="method-page">
        <div class="product-row">
          <ProductCard
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
               v-model="journalData"
               :isEditing="isEditing"
               v-show="(isEditing && i <= visibleReagentsCount) || (!isEditing && journalData[`reagent${i}_smiles`]) || i === 1"
             />

             <!-- Кнопка добавления реагента (только в режиме редактирования) -->
             <button
               v-if="isEditing && visibleReagentsCount < 5"
               class="add-reagent-card"
               @click="addReagent"
             >
               <span class="plus-icon">+</span>
               Добавить реагент
             </button>
           </div>
        </div>

        <div class="procedure-section">
          <h3>Методика</h3>
          <textarea
            v-model="journalData.procedure"
            :disabled="!isEditing"
            placeholder="Опишите ход синтеза..."
          ></textarea>
        </div>
      </section>

      <!-- Вкладка Поиск -->
      <section v-if="activeTab === 'search'">
        <h2>Поиск по структуре</h2>
      </section>
    </main>
  </div>
</template>

<script setup>
import {ref, watch} from 'vue'
import ProductCard from '@/components/ProductCard.vue'
import ReagentCard from '@/components/ReagentCard.vue'

const activeTab = ref('method')
const isEditing = ref(false)

const visibleReagentsCount = ref(3); // По умолчанию показываем 3

const addReagent = () => {
  if (visibleReagentsCount.value < 5) {
    visibleReagentsCount.value++;
  }
};

// Инициализация объекта по вашей схеме Pydantic
const createEmptyEntry = () => {
  const entry = {
    user_id: 1,
    product_smiles: '', product_preview_svg: '', product_molar_mass: null,
    product_moles: null, product_molar_ekv: 1.0,
    product_theoretical_mass: null, product_praktical_mass: null,
    product_yield_calc: null, procedure: '',
  };

  // Инициализируем все 5 реагентов
  for (let i = 1; i <= 5; i++) {
    entry[`reagent${i}_smiles`] = '';
    entry[`reagent${i}_svg`] = '';
    entry[`reagent${i}_molar_mass`] = null;
    entry[`reagent${i}_mass`] = null;
    entry[`reagent${i}_moles`] = null;
    entry[`reagent${i}_density`] = null;
    entry[`reagent${i}_concentration`] = 1.0; // По умолчанию 1
    entry[`reagent${i}_volume`] = null;
    entry[`reagent${i}_molar_ekv`] = i === 1 ? 1.0 : null; // Для первого ставим 1
  }
  return entry;
}

const journalData = ref(createEmptyEntry())

// При создании новой записи можно сбрасывать счетчик до 3
const createNewEntry = () => {
    journalData.value = createEmptyEntry();
    visibleReagentsCount.value = 3;
    isEditing.value = true;
};

const calculateJournal = () => {
  const d = journalData.value;
  if (!d) return;

  // --- 1. РАСЧЕТ РЕАГЕНТА 1 (Лимитирующий) ---
  const r1_mw = parseFloat(d.reagent1_molar_mass);
  const r1_mass = parseFloat(d.reagent1_mass);
  const r1_dens = parseFloat(d.reagent1_density);
  const r1_conc = parseFloat(d.reagent1_concentration) || 1.0;

  if (r1_mass > 0 && r1_mw > 0) {
    // Моли R1 считаем строго по массе: n = m / MW
    d.reagent1_moles = (r1_mass / r1_mw).toFixed(4);
  } else {
    d.reagent1_moles = null;
  }

  // Объем R1: V = m / (density * concentration)
  // Если концентрация 1.0 (100%), то просто m/density
  if (r1_mass > 0 && r1_dens > 0) {
    d.reagent1_volume = (r1_mass / (r1_dens * r1_conc)).toFixed(2);
  }

  // --- 2. БАЗОВЫЕ МОЛИ (n на 1 эквивалент) ---
  const r1_moles = parseFloat(d.reagent1_moles);
  const r1_ekv = parseFloat(d.reagent1_molar_ekv) || 1.0;

  if (r1_moles > 0 && r1_ekv > 0) {
    const baseMoles = r1_moles / r1_ekv;

    // --- 3. РАСЧЕТ РЕАГЕНТОВ 2-5 ---
    for (let i = 2; i <= 5; i++) {
      const ekv = parseFloat(d[`reagent${i}_molar_ekv`]);
      const mw = parseFloat(d[`reagent${i}_molar_mass`]);
      const dens = parseFloat(d[`reagent${i}_density`]);
      const conc = parseFloat(d[`reagent${i}_concentration`]) || 1.0;

      if (ekv > 0) {
        // n(Ri) = n(base) * eq(Ri)
        d[`reagent${i}_moles`] = (baseMoles * ekv).toFixed(4);

        if (mw > 0) {
          // Масса чистого вещества: m = n * MW
          const massNetto = parseFloat(d[`reagent${i}_moles`]) * mw;
          d[`reagent${i}_mass`] = massNetto.toFixed(3);

          if (dens > 0) {
            // Объем раствора/жидкости с учетом концентрации
            d[`reagent${i}_volume`] = (massNetto / (dens * conc)).toFixed(2);
          }
        }
      } else {
        d[`reagent${i}_moles`] = null;
        d[`reagent${i}_mass`] = null;
        d[`reagent${i}_volume`] = null;
      }
    }

    // --- 4. РАСЧЕТ ПРОДУКТА (Теоретический) ---
    const prod_mw = parseFloat(d.product_molar_mass);
    const prod_ekv = parseFloat(d.product_molar_ekv) || 1.0;

    if (prod_mw > 0) {
      // Теор. моли продукта: n(prod) = n(base) * eq(prod)
      const theoProdMoles = baseMoles * prod_ekv;
      d.product_moles = theoProdMoles.toFixed(4);

      // Теор. масса: m = n * MW
      d.product_theoretical_mass = (theoProdMoles * prod_mw).toFixed(3);
    }
  }

  // Выход (%)
  const prac_mass = parseFloat(d.product_praktical_mass);
  const theor_mass = parseFloat(d.product_theoretical_mass);
  if (prac_mass > 0 && theor_mass > 0) {
    d.product_yield_calc = ((prac_mass / theor_mass) * 100).toFixed(1);
  }
}

watch(journalData, () => {
  calculateJournal();
}, { deep: true });


</script>

<style scoped>
.journal-container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.tabs-nav { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #eee; }
.tabs-nav button { padding: 10px 20px; cursor: pointer; border: none; background: none; font-size: 1.1rem; }
.tabs-nav button.active { border-bottom: 3px solid #42b983; font-weight: bold; }

.toolbar { margin-bottom: 20px; display: flex; gap: 10px; background: #f9f9f9; padding: 10px; border-radius: 8px; }
.btn-save { background: #42b983; color: white; border-radius: 4px; border: none; padding: 5px 15px; cursor: pointer; }
.btn-save:disabled { background: #ccc; }

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
</style>