<template>
  <div class="results-section">
    <h3>Book Base Results</h3>
    <div v-if="loading" class="loading">Searching 18-core Xeon power...</div>
    <div v-else-if="results.length === 0" class="no-results">No reactions found in Journals.</div>
    <div v-else class="results-grid">
      <div v-for="res in results" :key="res.id" class="reaction-card">
         <div class="smiles-text">{{ res.smiles }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps(['smiles'])
const results = ref([])
const loading = ref(false)

// Функция запроса к бэкенду
const fetchResults = async () => {
  if (!props.smiles) return
  loading.value = true
  try {
    // Здесь будет твой fetch к FastAPI
    console.log(`Searching Journal Base for: ${props.smiles}`)
    // const resp = await fetch(`/api/search/journals?q=${props.smiles}`)
    // results.value = await resp.json()
  } finally {
    loading.value = false
  }
}

// Следим за изменением SMILES, чтобы обновить результаты
watch(() => props.smiles, fetchResults)
</script>

<style scoped>
.results-section { margin-top: 20px; padding: 15px; background: #fff; border-radius: 8px; border: 1px solid #eee; }
h3 { color: #2c3e50; border-bottom: 2px solid #42b983; display: inline-block; }
.results-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-top: 10px; }
.reaction-card { border: 1px solid #ddd; padding: 10px; border-radius: 4px; font-size: 0.8rem; }
</style>