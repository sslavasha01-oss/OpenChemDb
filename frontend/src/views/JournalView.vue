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

        <div class="reagents-grid">
          <!-- Сюда добавим карточки реагентов позже -->
          <p style="color: #666">Место для карточек реагентов (1-5)</p>
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

const activeTab = ref('method')
const isEditing = ref(false)

// Инициализация объекта по вашей схеме Pydantic
const createEmptyEntry = () => ({
  user_id: 1,
  product_smiles: '',
  product_svg: '', // Обязательно добавляем поле здесь
  product_molar_mass: null,
  product_moles: null,
  product_molar_ekv: 1.0,
  product_theoretical_mass: null,
  product_praktical_mass: null,
  product_yield_calc: null,
  procedure: '',
})

const journalData = ref(createEmptyEntry())

const createNewEntry = () => {
    // ИСПРАВЛЕНО: .value вместо .ref
    journalData.value = createEmptyEntry()
    isEditing.value = true
}

const calculateJournal = () => {
  const data = journalData.value;
  if (!data) return;

  // Расчет молей продукта: Масса / Молярная масса
  if (data.product_praktical_mass && data.product_molar_mass && data.product_molar_mass > 0) {
    data.product_moles = (parseFloat(data.product_praktical_mass) / parseFloat(data.product_molar_mass)).toFixed(4);
  } else {
    data.product_moles = null;
  }

  // Расчет выхода (Yield)
  if (data.product_theoretical_mass && data.product_praktical_mass && data.product_theoretical_mass > 0) {
    const y = (parseFloat(data.product_praktical_mass) / parseFloat(data.product_theoretical_mass)) * 100;
    data.product_yield_calc = y.toFixed(1);
  } else {
    data.product_yield_calc = null;
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
</style>