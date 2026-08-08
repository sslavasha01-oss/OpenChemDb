<template>
  <div class="results-section">
    <div class="header">
      <h3>Journal Records</h3>
      <span v-if="totalCount > 0" class="stat">
        Total: {{ totalCount }} (showing {{ offset + 1 }}-{{ Math.min(offset + limit, totalCount) }})
      </span>
    </div>

    <!-- Загрузка / Ошибка / Пусто (без изменений) -->
    <div v-if="loading" class="status-msg loading">
      <div class="spinner"></div>
      <p>Loading journal records...</p>
    </div>

    <div v-else-if="error" class="status-msg error">
      <span class="icon">⚠️</span>
      <p>{{ error }}</p>
    </div>

    <div v-else-if="records.length === 0" class="status-msg empty">
      <p>Your journal is empty. Create your first record in "Method" tab!</p>
    </div>

    <!-- Таблица -->
    <div v-else>
      <div class="table-container">
        <table class="reaction-table">
          <thead>
            <tr>
              <th v-if="isSelectionMode" class="col-check">
               <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll">
              </th>
              <th class="col-viz">Product</th>
              <th class="col-id">ID / Date</th>
              <th class="col-cond">Conditions</th>
              <th class="col-yield">Yield</th>
              <th class="col-procedure">Procedure</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rec in records" :key="rec.id" class="reaction-row" :class="{ 'selected-row': rec.id === props.selectedId }" @click="$emit('select-record', rec, true)">
             <td v-if="isSelectionMode" class="col-check" @click.stop>
                 <input type="checkbox" :value="rec.id" v-model="selectedIds">
             </td>
             <td class="col-viz">
  <div class="reaction-container">
    <!-- Состояние 1: SVG успешно создан -->
    <div v-if="rec.rendered_svg" v-html="rec.rendered_svg"></div>

    <!-- Состояние 2: SMILES есть, но SVG еще нет (идет рендер или ожидание либы) -->
    <div v-else-if="rec.product_smiles && rec.product_smiles.trim() !== ''" class="chem-loading">
      <div class="mini-spinner"></div>
      <span>Rendering...</span>
    </div>

    <!-- Состояние 3: SMILES реально пустой -->
    <div v-else class="no-viz">No Structure</div>
  </div>
</td>

  <td class="col-id" data-label="Entry">
    <div class="id-badge">#{{ rec.external_id }}</div>
    <div class="date-text">{{ formatDate(rec.date_added) }}</div>
  </td>

  <td class="col-cond" data-label="Conditions">
    <div class="cond-text">{{ rec.conditions || 'n/a' }}</div>
  </td>

  <td class="col-yield" data-label="Yield">
    <div v-if="rec.product_yield_calc" class="yield-badge">{{ rec.product_yield_calc }}%</div>
    <div v-else class="no-yield">—</div>
  </td>

  <td class="col-procedure" data-label="Procedure">
    <div class="procedure-preview">{{ rec.procedure || 'No description...' }}</div>
  </td>
</tr>
          </tbody>
        </table>
      </div>

      <!-- Пагинация (без изменений) -->
      <div class="pagination" v-if="totalPages > 1">
        <button :disabled="currentPage === 1" @click="changePage(1)" class="pag-btn" title="First Page">« First</button>
        <button :disabled="currentPage === 1" @click="changePage(currentPage - 1)" class="pag-btn">← Prev</button>

        <div class="page-numbers"><span class="current">{{ currentPage }}</span> / {{ totalPages }}</div>

        <button :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)" class="pag-btn">Next →</button>
        <button :disabled="currentPage === totalPages" @click="changePage(totalPages)" class="pag-btn" title="Last Page">Last »</button>
      </div>
    </div>
  </div>
</template>

<script setup>
// ... (Весь JS код остается точно таким же, как в твоем рабочем примере) ...
import { ref, watch, onMounted, computed, nextTick } from 'vue'
import axios from 'axios'
import OCL from 'openchemlib'
import { renderStructure } from '@/utils/chemUtils'
const emit = defineEmits(['select-record', 'update:selected-export-ids'])
const records = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const limit = 10
const loading = ref(false)
const error = ref(null)
const pagesCache = ref({})

const isSearchMode = ref(false);

const isChemReady = ref(false);

const checkChemLib = () => {
  try {
    const lib = window.OCL || OCL;
    // Проверяем не просто наличие, а работоспособность
    if (lib && lib.Molecule && typeof lib.Molecule.fromSmiles === 'function') {
      // Пробный рендер, чтобы убедиться, что библиотека "прогрета"
      const test = lib.Molecule.fromSmiles('C');
      if (test && test.getAllAtoms() > 0) {
        isChemReady.value = true;
        return true;
      }
    }
  } catch (e) {
    return false;
  }
  return false;
};


const renderAllVisibleRecords = () => {
  if (!isChemReady.value || records.value.length === 0) return;

  let hasChanges = false;
  records.value.forEach(rec => {
    if (rec.product_smiles && !rec.rendered_svg) {
      const svg = prepareSvgForTable(rec.product_smiles, rec.id);
      if (svg) {
        rec.rendered_svg = svg;
        hasChanges = true;
      }
    }
  });

  // Если мы что-то отрисовали, обновляем кэш текущей страницы
  if (hasChanges) {
    pagesCache.value[currentPage.value] = JSON.parse(JSON.stringify(records.value));
  }
};

// Функция ожидания загрузки OCL (ретрай)
const ensureOCLReady = async (maxAttempts = 5) => {
  for (let i = 0; i < maxAttempts; i++) {
    if (window.OCL || (typeof renderStructure === 'function' && renderStructure('C'))) {
      return true;
    }
    console.log(`Waiting for OCL... attempt ${i + 1}`);
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  return false;
};

// Функция подготовки SVG с уникальными ID
const prepareSvgForTable = (smiles, recordId) => {
  const rawSvg = renderStructure(smiles, 160, 120);
  if (!rawSvg) return null;
  const prefix = `table-rec-${recordId}`;
  return rawSvg
    .replace(/id=["']([^"']+)["']/g, (match, id) => `id="${prefix}-${id}"`)
    .replace(/href=["']#([^"']+)["']/g, (match, href) => `href="#${prefix}-${href}"`)
    .replace(/url\(#([^)]+)\)/g, (match, url) => `url(#${prefix}-${url})`);
};

// Хранилище ID для активного поиска
const searchResultsIds = ref([])
const isSearchActive = computed(() => searchResultsIds.value.length > 0)
const isSearchPending = ref(false) // Новый флаг-блокиратор дефолтной загрузки

const selectedIds = ref([])

const props = defineProps({
  selectedId: [Number, String],
  isSelectionMode: Boolean
})

const offset = computed(() => (currentPage.value - 1) * limit)
const totalPages = computed(() => Math.ceil(totalCount.value / limit))


const isAllSelected = computed(() => {
  return records.value.length > 0 && records.value.every(r => selectedIds.value.includes(r.id))
})

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    // Убираем только те ID, которые есть на текущей странице
    const currentPageIds = records.value.map(r => r.id)
    selectedIds.value = selectedIds.value.filter(id => !currentPageIds.includes(id))
  } else {
    // Добавляем только те, которых еще нет в списке
    records.value.forEach(r => {
      if (!selectedIds.value.includes(r.id)) {
        selectedIds.value.push(r.id)
      }
    })
  }
}

// Следим за изменениями, чтобы передать родителю
watch(selectedIds, (newVal) => {
  emit('update:selected-export-ids', newVal)
}, { deep: true })


const fetchCount = async () => {
  if (!localStorage.getItem('token')) {
    return;
  }
  // Если активирован поиск, количество — это ВСЕГДА актуальная длина массива найденных ID
  if (isSearchMode.value) {
    totalCount.value = searchResultsIds.value.length;
    return;
  }
  if (totalCount.value > 0) return;
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/my-journal/count', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    totalCount.value = response.data.total
  } catch (err) { console.error(err) }
}

const fetchRecords = async (forceRefresh = false) => {
  if (!forceRefresh && pagesCache.value[currentPage.value]) {
    records.value = pagesCache.value[currentPage.value];

    // Передаем текущие записи по ссылке
    forceRenderMissing(records.value, currentPage.value);
    return records.value;
  }

  loading.value = true;
  error.value = null;

  try {
    const token = localStorage.getItem('token');
    if (!token) return;

    let responseData;
    if (isSearchMode.value) {
      const pageIds = searchResultsIds.value.slice(offset.value, offset.value + limit);
      if (pageIds.length === 0) responseData = [];
      else {
        const params = new URLSearchParams();
        pageIds.forEach(id => params.append('ids', id));
        const res = await axios.get('/api/my-journal/search/by-ids', { params, headers: { 'Authorization': `Bearer ${token}` } });
        responseData = res.data;
      }
    } else {
      const res = await axios.get('/api/my-journal/list', { params: { limit, offset: offset.value }, headers: { 'Authorization': `Bearer ${token}` } });
      responseData = res.data;
    }

    records.value = responseData;

    // СРАЗУ кешируем базовые данные (без SVG), чтобы они не потерялись при быстром клике
    pagesCache.value[currentPage.value] = JSON.parse(JSON.stringify(responseData));

    // Вызываем рендер, жестко привязывая его к текущему списку и текущей странице
    forceRenderMissing(records.value, currentPage.value);

    if (!props.selectedId && responseData.length > 0 && currentPage.value === 1) {
       emit('select-record', responseData[0], false);
    }
    return responseData;
  } catch (err) {
    console.error(err);
    error.value = "Load failed";
  } finally {
    loading.value = false;
  }
}

// Эта функция будет «дорисовывать» то, что не отрисовалось сразу
// 3. Пуленепробиваемый рендер: мутирует объекты напрямую!
// Принимает массив и номер страницы, чтобы избежать бага при быстром переключении
const forceRenderMissing = async (targetRecords, targetPage) => {
  const ready = await waitForOCL();
  if (!ready) {
    console.error("Chemical library failed to load");
    return;
  }

  let hasChanges = false;

  // Важно: мы НЕ используем .map() и НЕ переназначаем records.value
  // Мы мутируем реактивные свойства напрямую. Vue 3 отрендерит их моментально.
  targetRecords.forEach(rec => {
    if (rec.product_smiles && !rec.rendered_svg) {
      const svg = prepareSvgForTable(rec.product_smiles, rec.id);
      if (svg) {
        rec.rendered_svg = svg;
        hasChanges = true;
      }
    }
  });

  // Обновляем кэш безопасно: только если мы все еще на той же странице
  if (hasChanges && targetPage) {
    pagesCache.value[targetPage] = JSON.parse(JSON.stringify(targetRecords));
  }
};

const refreshData = async (keepSearch = false) => {
  // Очищаем кэш страниц в любом случае, так как данные в БД изменились
  pagesCache.value = {};

  // Если мы хотим сохранить результаты поиска, то НЕ сбрасываем режим поиска и ID
  if (keepSearch && isSearchMode.value) {
    console.log("[Journal Debug Table] Обновление данных с СОХРАНЕНИЕМ режима поиска");
    // Пересчитываем totalCount на основе имеющихся ID (так как fetchCount для поиска завязан на них)
    await fetchCount();
  } else {
    console.log("[Journal Debug Table] Полный сброс таблицы к дефолтному списку /list");
    isSearchMode.value = false;
    totalCount.value = 0;
    currentPage.value = 1;
    searchResultsIds.value = [];
    await fetchCount();
  }

  // Запрашиваем свежие данные для текущей страницы
  await fetchRecords(true);
}

const runSubstructureSearch = async (reagentSmiles, productSmiles, exact) => {
  console.log("[Journal Debug Table] Внутри runSubstructureSearch. Smiles:", { reagentSmiles, productSmiles });
  loading.value = true;
  error.value = null;
  pagesCache.value = {};
  currentPage.value = 1;
  searchResultsIds.value = [];

  // ХАРДКОДНЫЙ ФЛАГ: МЫ В РЕЖИМЕ ПОИСКА
  isSearchMode.value = true;

  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/my-journal/search/ids', {
      params: {
        reagent_smiles: reagentSmiles || undefined,
        product_smiles: productSmiles || undefined,
        exact: exact ? true : undefined
      },
      headers: { 'Authorization': `Bearer ${token}` }
    });

    const newIds = response.data.ids || [];
    console.log("[Journal Debug Table] Сервер вернул ID совпадений:", newIds);

    searchResultsIds.value = newIds;

    await fetchCount();
    await fetchRecords(true);
  } catch (err) {
    console.error("Substructure search error:", err);
    error.value = "Search failed";
    isSearchMode.value = false; // Если упало, сбрасываем режим
  } finally {
    loading.value = false;
  }
}

const changePage = async (newPage) => {
  if (newPage < 1 || newPage > totalPages.value) return;
  currentPage.value = newPage;
  return await fetchRecords();
}

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-US', {
    day: '2-digit', month: '2-digit'
  })
}

const waitForOCL = async () => {
  if (isChemReady.value) return true;

  for (let i = 0; i < 50; i++) { // 50 попыток по 200мс = 10 секунд
    if (checkChemLib()) {
      isChemReady.value = true;
      return true;
    }
    await new Promise(r => setTimeout(r, 200));
  }
  return false;
};

watch([isChemReady, () => records.value.length], ([ready, count]) => {
  if (ready && count > 0) {
    console.log("[Table Debug] Chem ready or records updated. Rendering...");
    renderAllVisibleRecords();
  }
}, { immediate: true });


onMounted(async () => {
  // 1. Запускаем опрос готовности библиотеки (фоново)
  waitForOCL();

  // 2. Если мы не в режиме ожидания поиска, грузим данные
  if (!isSearchPending.value && !isSearchActive.value) {
    await fetchCount();
    await fetchRecords(); // Когда это закончится, сработает Watcher из п.1
  }
});

defineExpose({
  refreshData,
  runSubstructureSearch,
  isSearchPending, // Обязательно экспонируем флаг для родителя
  records,
  changePage,
  currentPage,
  totalPages,
  isSearchMode,
  searchResultsIds,
  selectedIds
})
</script>

<style scoped>
.results-section.results-section {
  background: white;
  border-radius: 8px;
  padding: 5px 15px 15px 15px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  width: 100%;
  box-sizing: border-box;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center; /* Центрируем по вертикали */
  border-bottom: 2px solid #42b983;
  margin-bottom: 8px;   /* Поджимаем к таблице */
  padding-bottom: 2px;
}

.header h3 {
  margin: 0; /* Убираем гигантские стандартные отступы браузера */
  font-size: 1.2rem;
}

.stat {
  font-size: 0.85rem;
  color: #666;
}

.table-container {
  width: 100%;
  /* На мобилках разрешаем горизонтальный скролл, если что-то пойдет не так,
     но основной упор делаем на перестроение в карточки */
  overflow-x: auto;
}
.reaction-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.reaction-table th {
  background: #f8f9fa;
  padding: 12px 10px;
  text-align: left;
  font-size: 0.75rem;
  color: #7f8c8d;
  text-transform: uppercase;
}
.reaction-table td {
  padding: 10px;
  border-bottom: 1px solid #eee;
  vertical-align: middle;
  /* Защита от раздувания: если текст без пробелов, он не сломает таблицу */
  word-wrap: break-word;
  overflow: hidden;
}

.col-viz { width: 180px; }
.col-id { width: 100px; }
.col-cond { width: 150px; }
.col-yield { width: 80px; }
.col-procedure { width: auto; }

.reaction-container {
  display: flex;
  justify-content: center;
  background: #fff;
  border-radius: 4px;
  min-height: 120px; /* Резервируем место под картинку */
  min-width: 120px;
  width: 100%;
}

.reaction-container :deep(svg) {
  display: block;
  width: 100%;
  height: auto;
  max-height: 120px;
}

.id-badge { background: #42b983; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.85rem; }
.date-text { font-size: 0.7rem; color: #999; margin-top: 4px; }

.yield-badge {
  background: #e6f7ef; color: #2d8a5d; font-weight: bold;
  padding: 4px 8px; border-radius: 6px; display: inline-block;
  border: 1px solid #c2eadd;
}
.no-yield { color: #ccc; font-size: 0.9rem; }

.cond-text { font-size: 0.85rem; color: #666; font-style: italic; }

.procedure-preview, .cond-text {
  font-size: 0.85rem;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.procedure-preview { -webkit-line-clamp: 3; } /* Максимум 3 строки */
.cond-text { -webkit-line-clamp: 2; }          /* Максимум 2 строки */

.reaction-row { cursor: pointer; transition: background 0.2s; }
.reaction-row:hover { background: #f9fdfb; }

/* Пагинация и спиннер без изменений */
.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px; /* Уменьшили с 15 до 8 */
  flex-wrap: wrap; /* Чтобы кнопки не вылезали за экран на узких телефонах */
}
.pag-btn { padding: 6px 14px; border: 1px solid #42b983; background: white; color: #42b983; border-radius: 20px; cursor: pointer; }
.pag-btn:disabled { opacity: 0.3; }
.status-msg { text-align: center; padding: 40px; color: #7f8c8d; }
.spinner { width: 30px; height: 30px; border: 3px solid #f3f3f3; border-top: 3px solid #42b983; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

/* --- МОБИЛЬНАЯ АДАПТАЦИЯ --- */
@media (max-width: 768px) {
  /* Скрываем заголовки таблицы */
  .reaction-table thead {
    display: none;
  }

  /* Превращаем каждую строку в отдельную "карточку" */
  .reaction-table tr {
    display: block;
    border: 1px solid #eee;
    border-radius: 10px;
    margin-bottom: 20px;
    padding: 10px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.02);
  }

  /* Превращаем каждую ячейку в блок */
  .reaction-table td {
    display: block;
    width: 100% !important; /* Сбрасываем десктопную ширину */
    box-sizing: border-box;
    border-bottom: none;
    padding: 8px 5px;
  }

  /* Картинка продукта по центру вверху карточки */
  .col-viz {
    border-bottom: 1px solid #f5f5f5 !important;
    margin-bottom: 10px;
  }

  /* Добавляем текстовые метки перед данными через псевдоэлементы */
  .reaction-table td::before {
    content: attr(data-label); /* Берет текст из атрибута data-label */
    font-weight: bold;
    font-size: 0.7rem;
    color: #999;
    text-transform: uppercase;
    display: block;
    margin-bottom: 2px;
  }

  /* Для картинки метка не нужна */
  .col-viz::before { display: none; }

  /* Улучшаем отображение бейджей на мобилках */
  .id-badge, .yield-badge {
    display: inline-block;
  }
}

.reaction-row.selected-row {
  background-color: #e6f7ef; /* Светло-зеленый фон */
  border-left: 4px solid #42b983; /* Акцентная полоса слева */
}
/* Чтобы ховер не перекрывал выделение слишком сильно */
.reaction-row.selected-row:hover {
  background-color: #d8f3e5;
}

.col-check { width: 40px; text-align: center; }
.col-check input { width: 18px; height: 18px; cursor: pointer; }

.chem-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: #999;
  font-size: 0.7rem;
}

.mini-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #42b983;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
</style>