<template>
  <div class="journal-container">
    <!-- Навигация по вкладкам -->
    <nav class="tabs-nav">
      <button :class="{ active: activeTab === 'table' }" :disabled="isGuest" @click="activeTab = 'table'">Таблица</button>
      <button :class="{ active: activeTab === 'method' }" @click="activeTab = 'method'">Методика</button>
      <button :class="{ active: activeTab === 'search' }" :disabled="isGuest" @click="activeTab = 'search'">Поиск</button>
    </nav>

  <div class="header-controls">
      <div v-if="!isGuest && activeTab !== 'search'" class="global-record-nav">
        <button @click="navigateRecord(-1)" :disabled="isEditing" class="nav-arrow">←</button>
        <span class="selected-id-display">
          Запись: {{ journalData?.external_id ? '#' + journalData.external_id : '---' }}
        </span>
        <button @click="navigateRecord(1)" :disabled="isEditing" class="nav-arrow">→</button>
      </div>

      <template v-if="!isGuest">
        <button
          v-if="activeTab === 'table' || activeTab === 'method'"
          class="btn-add-main"
          @click="initNewEntryFromTable"
        >
          <span class="icon">+</span> Новая запись
        </button>

        <button
          v-if="activeTab === 'method'"
          :class="isEditing ? 'btn-cancel-main' : 'btn-edit-main'"
          @click="handleEditToggle"
        >
          {{ isEditing ? 'Отменить' : 'Редактировать' }}
        </button>

        <button
          v-if="activeTab === 'method' && isEditing"
          class="btn-save"
          @click="saveEntry"
          :disabled="loading"
        >
          {{ loading ? 'Сохранение...' : 'Сохранить' }}
        </button>

        <button
          v-if="activeTab === 'method' && journalData?.external_id"
          class="btn-delete-main"
          :disabled="isEditing || loading"
          @click="deleteEntry"
        >
          Удалить
        </button>
      </template>

      <template v-else>
        <button class="btn-cancel-main" @click="journalData = createEmptyEntry()">
          Очистить калькулятор
        </button>
      </template>
    </div>

    <main class="tab-content">
        <section v-show="activeTab === 'table' && !isGuest">
        <div class="table-actions">
          <button class="btn-add-main" @click="initNewEntryFromTable">
            <span class="icon">+</span> Добавить новую запись в журнал
          </button>
        </div>

        <JournalTable ref="tableRef" :selected-id="selectedRecordId"
         @select-record="handleTableSelect"
          />
      </section>

      <!-- Вкладка Методика -->
      <section v-show="activeTab === 'method'" class="method-page">

        <div v-if="isGuest" class="guest-alert-banner">
          <span class="banner-icon">⚗️</span>
          <p class="banner-text">
            <strong>Режим калькулятора:</strong> Здесь вы можете рассчитать стехиометрию химической реакции.
            Для полноценного ведения лаб-журнала, сохранения истории и поиска по структурам, пожалуйста,
            <router-link to="/login" class="banner-link">залогиньтесь в систему</router-link>.
          </p>
        </div>

        <div class="product-row">
          <ProductCard
            ref="productCardRef"
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
               :ref="el => { if (el) reagentCardRefs[i-1] = el }"
               v-model="journalData"
               :isEditing="isEditing"
               v-show="(isEditing && i <= visibleReagentsCount) || (!isEditing && journalData[`reagent${i}_smiles`]) || i === 1"
             />

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
    <iframe
      id="global-ketcher-iframe"
      ref="globalKetcherFrame"
      src="/standalone/index.html?hidden_controls=all"
      class="invisible-ketcher">
    </iframe>
  </div>

</template>

<script setup>
import { ref, watch, nextTick, onMounted, computed} from 'vue'
import axios from 'axios'
import ProductCard from '@/components/ProductCard.vue'
import ReagentCard from '@/components/ReagentCard.vue'
import JournalTable from '@/components/JournalTable.vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const isGuest = computed(() => !userStore.isLoggedIn)

const _isEditingInternal = ref(false)
const isEditing = computed({
  get: () => isGuest.value ? true : _isEditingInternal.value,
  set: (val) => { _isEditingInternal.value = val }
})

const activeTab = ref(isGuest.value ? 'method' : 'table')
const loading = ref(false) // Состояние загрузки
const visibleReagentsCount = ref(3)
const tableRef = ref(null)
const productCardRef = ref(null);
const reagentCardRefs = ref([]);
const selectedRecordId = ref(null);

const globalKetcherFrame = ref(null);

const isKetcherInjected = ref(false);
const isKetcherReady = ref(false);

// Загружаем фрейм через секунду после входа на страницу
onMounted(() => {
  setTimeout(() => {
    isKetcherInjected.value = true;
  }, 1000);
});

const onKetcherLoad = () => {
  // Фрейм загрузился, но Indigo внутри может еще тупить
  const checkIndigo = setInterval(() => {
    const ketcher = globalKetcherFrame.value?.contentWindow?.ketcher;
    if (ketcher && ketcher.setMolecule) {
      isKetcherReady.value = true;
      console.log("Ketcher Engine Ready");
      clearInterval(checkIndigo);
    }
  }, 500);

  // Страховка от вечного цикла
  setTimeout(() => clearInterval(checkIndigo), 10000);
};

const addReagent = () => {
  if (visibleReagentsCount.value < 5) {
    visibleReagentsCount.value++;
  }
};

// Функция создания пустого объекта записи
const createEmptyEntry = () => {
  const entry = {
    user_id: null, // Установит бэкенд из токена, но для схемы нужно
    product_smiles: '',
    product_svg: '',
    product_preview_svg: '',
    product_molar_mass: null,
    product_moles: null,
    product_molar_ekv: 1.0,
    product_theoretical_mass: null,
    product_praktical_mass: null,
    product_yield_calc: null,
    procedure: '',
  };

  for (let i = 1; i <= 5; i++) {
    entry[`reagent${i}_smiles`] = '';
    entry[`reagent${i}_svg`] = '';
    entry[`reagent${i}_molar_mass`] = null;
    entry[`reagent${i}_mass`] = null;
    entry[`reagent${i}_moles`] = null;
    entry[`reagent${i}_density`] = null;
    entry[`reagent${i}_concentration`] = 1.0;
    entry[`reagent${i}_volume`] = null;
    entry[`reagent${i}_molar_ekv`] = i === 1 ? 1.0 : null;
  }
  return entry;
}

const journalData = ref(createEmptyEntry())

// Функция для кнопки над таблицей
const initNewEntryFromTable = () => {
  // Обнуляем данные
  selectedRecordId.value = null;
  journalData.value = createEmptyEntry();
  visibleReagentsCount.value = 3;

  // Переключаем вкладку и включаем режим редактирования
  activeTab.value = 'method';
  isEditing.value = true;
};

// 1. НАЖАТИЕ "НОВАЯ ЗАПИСЬ"
const createNewEntry = () => {
    if (confirm("Очистить форму и создать новую запись? Несохраненные данные будут потеряны.")) {
        journalData.value = createEmptyEntry();
        visibleReagentsCount.value = 3;
        isEditing.value = true;
    }
};

// НАЖАТИЕ "СОХРАНИТЬ" (Создание или Обновление записи)
const saveEntry = async () => {
  loading.value = true;
  try {
    const token = localStorage.getItem('token');
    const source = journalData.value;
    const cleanData = {};

    // Исключаем SVG и системные поля, которые бэк в PUT/POST не ждет в body
    const excludeKeys = ['product_svg', 'product_preview_svg', 'id', 'user_id', 'date_added', 'date_modified'];

    Object.keys(source).forEach(key => {
      if (excludeKeys.includes(key) || key.endsWith('_svg')) return;

      let val = source[key];

      const isNumeric = key.includes('mass') || key.includes('moles') ||
                        key.includes('ekv') || key.includes('density') ||
                        key.includes('concentration') || key.includes('volume') ||
                        key.includes('yield_calc');

      if (isNumeric) {
        cleanData[key] = (val === '' || val === null || val === undefined) ? null : parseFloat(val);
      } else {
        cleanData[key] = (val === '') ? null : val;
      }
    });

    let response;
    const hasExternalId = source.external_id != null;

    if (hasExternalId) {
      // Если запись уже существует — отправляем PUT на /update/{external_id}
      response = await axios.put(`/api/my-journal/update/${source.external_id}`, cleanData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
    } else {
      // Если это новая запись — отправляем POST на /add
      response = await axios.post('/api/my-journal/add', cleanData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
    }

    journalData.value = response.data;
    isEditing.value = false;

    // Сразу же принудительно пинаем Ketcher, чтобы он перерисовал SVG из свежих SMILES
    triggerKetcherRedraw(response.data);
    alert(hasExternalId ? "Запись успешно обновлена!" : "Запись успешно сохранена!");

    if (tableRef.value) {
      tableRef.value.refreshData();
    }

  } catch (err) {
    console.error("Ошибка при сохранении:", err.response?.data || err);
    alert("Ошибка! Проверьте консоль.");
  } finally {
    loading.value = false;
  }
}

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

    // --- 4. РАСЧЕТ ПРОДУКТА (Теоретическая масса) ---
    const prod_mw = parseFloat(d.product_molar_mass);
    const prod_ekv = parseFloat(d.product_molar_ekv) || 1.0;

    if (prod_mw > 0) {
      // Теор. масса: n(base) * eq(prod) * MW(prod)
      d.product_theoretical_mass = (baseMoles * prod_ekv * prod_mw).toFixed(3);
    } else {
      d.product_theoretical_mass = null;
    }
  } else {
    d.product_theoretical_mass = null;
  }

  // --- 5. РАСЧЕТ ПРОДУКТА (Практические моли и Выход) ---
  const prod_mw = parseFloat(d.product_molar_mass);
  const prac_mass = parseFloat(d.product_praktical_mass);
  const theor_mass = parseFloat(d.product_theoretical_mass);

  // Практические моли: m(практ) / MW
  if (prac_mass > 0 && prod_mw > 0) {
    d.product_moles = (prac_mass / prod_mw).toFixed(4);
  } else {
    d.product_moles = null;
  }

  // Выход в %
  if (prac_mass > 0 && theor_mass > 0) {
    d.product_yield_calc = ((prac_mass / theor_mass) * 100).toFixed(1);
  } else {
    d.product_yield_calc = null;
  }
}

const loadRecordIntoForm = (record) => {
  // 1. Сразу переключаем интерфейс и данные
  journalData.value = { ...record };
  activeTab.value = 'method';
  isEditing.value = false;

  selectedRecordId.value = record.id;

  // Определяем количество видимых реагентов
  let count = 0;
  for (let i = 1; i <= 5; i++) {
    if (record[`reagent${i}_smiles`]) count = i;
  }
  visibleReagentsCount.value = Math.max(count, 1);

  // 2. Запускаем умное ожидание Ketcher
  const waitForKetcherAndDraw = async () => {
    const ketcher = globalKetcherFrame.value?.contentWindow?.ketcher;

    // Проверяем наличие ketcher и метода setMolecule
    if (ketcher && typeof ketcher.setMolecule === 'function') {
      console.time("Global Drawing");

      try {
        // Продукт
        if (record.product_smiles) {
          journalData.value.product_preview_svg = await fastGenerateSVG(ketcher, record.product_smiles);
        }

        // Реагенты
        for (let i = 1; i <= 5; i++) {
          const smiles = record[`reagent${i}_smiles`];
          if (smiles) {
            journalData.value[`reagent${i}_svg`] = await fastGenerateSVG(ketcher, smiles);
          }
        }
      } catch (err) {
        console.error("Drawing process failed:", err);
      }

      console.timeEnd("Global Drawing");
    } else {
      // Если Ketcher еще не загрузился (первый запуск), пробуем через 200мс снова
      console.log("Global Ketcher not ready, retrying...");
      setTimeout(waitForKetcherAndDraw, 200);
    }
  };

  waitForKetcherAndDraw();
};

// Вспомогательная функция (уже есть в твоем коде, проверь наличие)
const fastGenerateSVG = async (ketcher, smiles) => {
  try {
    await ketcher.setMolecule(smiles);
    const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' });
    const svg = await blob.text();
    return svg;
  } catch (e) {
    console.error("SVG Gen Error:", e);
    return '';
  }
};

const navigateRecord = async (direction) => {
  if (!tableRef.value || loading.value) return;

  // 1. Получаем текущие записи и ищем индекс
  const currentRecords = tableRef.value.records || [];
  const currentIndex = currentRecords.findIndex(r => r.id === selectedRecordId.value);

  console.log(`[Nav] Направление: ${direction}, Текущий индекс: ${currentIndex}, ID: ${selectedRecordId.value}`);

  let nextIndex = currentIndex + direction;

  // --- ЛОГИКА ПЕРЕХОДА МЕЖДУ СТРАНИЦАМИ ---

  // А. ВПЕРЕД (Уходим за пределы текущей страницы вниз)
  if (nextIndex >= currentRecords.length) {
    if (tableRef.value.currentPage < tableRef.value.totalPages) {
      console.log("[Nav] Переход на следующую страницу...");
      loading.value = true;
      const newPageRecords = await tableRef.value.changePage(tableRef.value.currentPage + 1);
      loading.value = false;

      if (newPageRecords && newPageRecords.length > 0) {
        await nextTick();
        // Выбираем первую запись новой страницы
        handleTableSelect(newPageRecords[0], false);
      }
    } else {
      console.log("[Nav] Это последняя страница, дальше нельзя.");
    }
    return;
  }

  // Б. НАЗАД (Уходим за пределы текущей страницы вверх)
  if (nextIndex < 0) {
    if (tableRef.value.currentPage > 1) {
      console.log("[Nav] Переход на предыдущую страницу...");
      loading.value = true;
      const newPageRecords = await tableRef.value.changePage(tableRef.value.currentPage - 1);
      loading.value = false;

      if (newPageRecords && newPageRecords.length > 0) {
        await nextTick();
        // Выбираем ПОСЛЕДНЮЮ запись предыдущей страницы
        const lastRecord = newPageRecords[newPageRecords.length - 1];
        console.log("[Nav] Выбираем последнюю запись:", lastRecord.id);
        handleTableSelect(lastRecord, false);
      }
    } else {
      console.log("[Nav] Это первая страница, назад нельзя.");
    }
    return;
  }

  // В. ОБЫЧНЫЙ ШАГ ВНУТРИ СТРАНИЦЫ
  const nextRecord = currentRecords[nextIndex];
  if (nextRecord) {
    console.log("[Nav] Переход внутри страницы к ID:", nextRecord.id);
    handleTableSelect(nextRecord, false);
  }
};

// 1. Эта функция ТОЛЬКО подгружает данные в форму (без переключения вкладок)
const updateFormDataOnly = (record) => {
  journalData.value = { ...record };
  selectedRecordId.value = record.id;
  isEditing.value = false;

  let count = 0;
  for (let i = 1; i <= 5; i++) {
    if (record[`reagent${i}_smiles`]) count = i;
  }
  visibleReagentsCount.value = Math.max(count, 1);

  // Запуск отрисовки Ketcher (вынесем в отдельный вызов ниже)
  triggerKetcherRedraw(record);
};

// 2. Эта функция используется для клика ПО ТАБЛИЦЕ (данные + переход)
const handleTableSelect = (record, forceTabChange = true) => {
  updateFormDataOnly(record);

  if (forceTabChange) {
    activeTab.value = 'method';
  }
};

// 3. Выносим отрисовку в отдельный метод (просто скопируйте логику из старой loadRecordIntoForm)
const triggerKetcherRedraw = (record) => {
  const waitForKetcherAndDraw = async () => {
    const ketcher = globalKetcherFrame.value?.contentWindow?.ketcher;
    if (ketcher && typeof ketcher.setMolecule === 'function') {
      try {
        if (record.product_smiles) {
          journalData.value.product_preview_svg = await fastGenerateSVG(ketcher, record.product_smiles);
        }
        for (let i = 1; i <= 5; i++) {
          const smiles = record[`reagent${i}_smiles`];
          if (smiles) {
            journalData.value[`reagent${i}_svg`] = await fastGenerateSVG(ketcher, smiles);
          }
        }
      } catch (err) { console.error(err); }
    } else {
      setTimeout(waitForKetcherAndDraw, 200);
    }
  };
  waitForKetcherAndDraw();
};

// Хранилище для копии данных на случай отмены редактирования
const journalDataBackup = ref(null);

// Логика кнопки Редактировать / Отменить
const handleEditToggle = () => {
  if (!isEditing.value) {
    // Включаем редактирование: делаем глубокую копию текущего состояния
    journalDataBackup.value = JSON.parse(JSON.stringify(journalData.value));
    isEditing.value = true;
  } else {
    // Отменяем редактирование: восстанавливаем данные из бэкапа
    if (journalDataBackup.value) {
      journalData.value = JSON.parse(JSON.stringify(journalDataBackup.value));
      triggerKetcherRedraw(journalData.value); // Возвращаем старые картинки в Кетчер
    }
    isEditing.value = false;
    journalDataBackup.value = null;
  }
};

// Ровная функция удаления записи с умным переходом по страницам
const deleteEntry = async () => {
  const extId = journalData.value?.external_id;
  if (!extId) return;

  if (confirm(`Вы уверены, что хотите полностью удалить запись #${extId}?`)) {
    loading.value = true;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`/api/my-journal/delete/${extId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      alert(`Запись #${extId} успешно удалена.`);

      if (!tableRef.value) {
        throw new Error("Компонент таблицы (tableRef) не найден");
      }

      const currentRecords = tableRef.value.records || [];
      const currentIndex = currentRecords.findIndex(r => r.id === selectedRecordId.value);

      let nextRecordToLoad = null;
      let needPageChange = false;
      let targetPage = tableRef.value.currentPage;

      // 1. Пытаемся найти следующую запись на ТЕКУЩЕЙ странице
      if (currentIndex !== -1 && currentIndex < currentRecords.length - 1) {
        nextRecordToLoad = currentRecords[currentIndex + 1];
      }
      // 2. Если следующей на этой странице нет — значит, мы удалили последнюю запись в списке страницы
      else {
        // Если есть следующая страница — целимся на её первую запись
        if (tableRef.value.currentPage < tableRef.value.totalPages) {
          targetPage = tableRef.value.currentPage + 1;
          needPageChange = true;
        }
        // Если следующей страницы нет, но есть предыдущая (мы были на самом конце журнала)
        else if (tableRef.value.currentPage > 1) {
          targetPage = tableRef.value.currentPage - 1;
          needPageChange = true;
        }
      }

      // 3. Обновляем/переключаем страницы и загружаем данные
      if (needPageChange) {
        console.log(`[Delete Nav] Переходим на страницу: ${targetPage}`);
        // Вызываем метод смены страницы, который возвращает новые записи
        const newPageRecords = await tableRef.value.changePage(targetPage);

        if (newPageRecords && newPageRecords.length > 0) {
          await nextTick();
          // Если ушли вперед — берем первую запись новой страницы, если назад — последнюю
          const isMovingForward = targetPage > tableRef.value.currentPage;
          nextRecordToLoad = isMovingForward ? newPageRecords[0] : newPageRecords[newPageRecords.length - 1];
        }
      } else {
        // Если остались в пределах текущей страницы, просто рефрешим её данные в фоне
        await tableRef.value.refreshData();
        // На случай, если после refreshData индексы съехали, перепроверяем запись
        const freshRecords = tableRef.value.records || [];
        // Если наша намеченная запись всё ещё существует в массиве — отлично, берем её
        if (nextRecordToLoad) {
          nextRecordToLoad = freshRecords.find(r => r.id === nextRecordToLoad.id) || freshRecords[currentIndex] || null;
        }
      }

      // 4. Загружаем финальный результат в форму без прыжков по вкладкам
      if (nextRecordToLoad) {
        updateFormDataOnly(nextRecordToLoad);
      } else {
        // Если в журнале вообще шаром покати (ноль записей во всей базе)
        selectedRecordId.value = null;
        journalData.value = createEmptyEntry();
        visibleReagentsCount.value = 3;
        isEditing.value = false;
      }

    } catch (err) {
      console.error("Ошибка при удалении:", err.response?.data || err);
      alert("Не удалось удалить запись. Проверьте консоль.");
    } finally {
      loading.value = false;
    }
  }
};

watch(journalData, () => {
  calculateJournal();
}, { deep: true });

watch(isGuest, (newIsGuest) => {
  if (newIsGuest) {
    activeTab.value = 'method';
    // Очищаем форму от остатков данных предыдущего пользователя
    journalData.value = createEmptyEntry();
    visibleReagentsCount.value = 3;
  }
});

// Отслеживаем смену аккаунта (когда переключили в навбаре)
watch(() => userStore.currentAccountIndex, async (newIndex) => {
  // 1. Обновляем токен в localStorage для аксиоса/запросов формы
  const currentAcc = userStore.currentUser;
  if (currentAcc && currentAcc.token) {
    localStorage.setItem('token', currentAcc.token);
  } else {
    localStorage.removeItem('token');
  }

  // 2. Сбрасываем форму метода, чтобы не висели данные предыдущего юзера
  journalData.value = createEmptyEntry();
  selectedRecordId.value = null;

  // 3. Если мы находимся на вкладке таблицы — принудительно обновляем её данные под нового юзера
  await nextTick();
  if (tableRef.value && activeTab.value === 'table' && !isGuest.value) {
    tableRef.value.refreshData();
  }
});

</script>

<style scoped>
.journal-container { max-width: 1200px; margin: 0 auto; padding: 10px; }
.tabs-nav { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #eee; }
.tabs-nav button { padding: 10px 20px; cursor: pointer; border: none; background: none; font-size: 1.1rem; }
.tabs-nav button.active { border-bottom: 3px solid #42b983; font-weight: bold; }

.toolbar { margin-bottom: 20px; display: flex; gap: 10px; background: #f9f9f9; padding: 10px; border-radius: 8px; }
.btn-save {
  height: 42px;
  border-radius: 8px;
  padding: 8px 16px;
  font-weight: bold;
}
.btn-save:disabled { background: #ccc; }

.btn-edit-main {
  background-color: #34495e;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  height: 42px;
  transition: background 0.2s;
}
.btn-edit-main:hover:not(:disabled) { background-color: #2c3e50; }

/* Кнопка "Отменить" */
.btn-cancel-main {
  background-color: #e67e22;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  height: 42px;
  transition: background 0.2s;
}
.btn-cancel-main:hover { background-color: #d35400; }

/* Кнопка "Удалить" */
.btn-delete-main {
  background-color: #e74c3c;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  height: 42px;
  transition: background 0.2s;
}
.btn-delete-main:hover:not(:disabled) { background-color: #c0392b; }
.btn-delete-main:disabled {
  background-color: #ccc;
  color: #666;
  cursor: not-allowed;
}

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

.invisible-ketcher {
  position: fixed;
  /* Даем реальные размеры, чтобы Ketcher не паниковал! */
  width: 800px;
  height: 600px;
  /* Уносим в космос */
  left: -5000px;
  top: -5000px;
  /* Но оставляем его "видимым" для системы рендеринга */
  visibility: visible;
  z-index: -1000;
  border: none;
  pointer-events: none;
}

.btn-add-main {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: background 0.2s;
}

.btn-add-main:hover {
  background-color: #3aa876;
}

.btn-add-main .icon {
  font-size: 1.2rem;
}

.global-record-nav {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
  background: #fff;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #eee;
  width: fit-content;
}
.nav-arrow {
  background: #42b983;
  color: white;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  font-weight: bold;
}
.nav-arrow:disabled { background: #ccc; cursor: not-allowed; }
.selected-id-display {
  font-weight: bold;
  color: #2c3e50;
  min-width: 100px;
  text-align: center;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 15px; /* Уменьшили отступ */
  flex-wrap: wrap;     /* Чтобы на мобилках не ломалось */
}

/* Корректируем навигацию, убираем лишний margin-bottom */
.global-record-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  padding: 5px 10px; /* Ужали по вертикали */
  border-radius: 8px;
  border: 1px solid #eee;
  width: fit-content;
  margin-bottom: 0; /* Убрали старый отступ */
}

/* Компактная кнопка добавления */
.btn-add-main {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 8px 16px; /* Уменьшили паддинги */
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.2s;
  height: 42px; /* Выравниваем высоту со стрелками */
}

/* Уменьшаем отступ у основной навигации вкладок */
.tabs-nav {
  margin-bottom: 15px;
}

/* Убираем лишние отступы в контенте таблицы */
.table-actions {
  display: none; /* Мы ее перенесли выше */
}

/* Стили для гостевого режима */
.tabs-nav button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  border-bottom: none;
}
.tabs-nav button:disabled:hover {
  color: inherit;
  background: none;
}

.guest-alert-banner {
  display: flex;
  align-items: center;
  gap: 15px;
  background-color: #e8f4fd;
  border-left: 4px solid #3498db;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 20px;
}
.banner-icon {
  font-size: 1.5rem;
}
.banner-text {
  margin: 0;
  color: #2c3e50;
  font-size: 0.95rem;
  line-height: 1.4;
}
.banner-link {
  color: #3498db;
  text-decoration: underline;
  font-weight: bold;
}
.banner-link:hover {
  color: #2980b9;
}

</style>