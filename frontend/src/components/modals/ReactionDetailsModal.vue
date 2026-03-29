<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-card">
      <header class="modal-header">
        <h2>Детали реакции #{{ reaction.id }}</h2>
        <button class="close-btn" @click="emit('close')">&times;</button>
      </header>

      <div class="modal-body">
        <section class="detail-section viz-grid">
          <div class="viz-item">
            <h4>Raw Structure (Original)</h4>
            <div class="img-wrap">
              <ReactionVisualizer :smiles="reaction.reaction_raw_smiles"/>
            </div>
            <code class="smiles-debug">{{ reaction.reaction_raw_smiles }}</code>
          </div>

          <div class="viz-item" v-if="reaction.reaction_mapped_smiles">
            <h4>Mapped Structure (Atom-to-Atom)</h4>
            <div class="img-wrap mapped">
              <ReactionVisualizer :smiles="reaction.reaction_mapped_smiles"/>
            </div>
            <code class="smiles-debug">{{ reaction.reaction_mapped_smiles }}</code>
          </div>
        </section>

        <hr/>

        <section class="detail-section info-grid">
          <div class="info-group">
            <label>External ID:</label> <span>{{ reaction.external_id || 'N/A' }}</span>
          </div>
          <div class="info-group">
            <label>DOI:</label>
            <a v-if="reaction.doi" :href="'https://doi.org/' + reaction.doi" target="_blank">{{ reaction.doi }}</a>
            <span v-else>N/A</span>
          </div>
          <div class="info-group">
            <label>Yield:</label> <span class="yield-badge">{{ reaction.yield_text || '—' }}%</span>
          </div>
          <div class="info-group full-width">
            <label>Conditions:</label>
            <p class="text-content">{{ reaction.conditions || 'Standard conditions' }}</p>
          </div>
          <div class="info-group full-width">
            <label>Reference:</label>
            <p class="text-content italic">{{ reaction.references }}</p>
          </div>
        </section>

        <section class="detail-section" v-if="reaction.procedure">
          <h4>Experimental Procedure</h4>
          <div class="procedure-box">{{ reaction.procedure }}</div>
        </section>

        <hr/>

        <section class="detail-section">
          <h4>User Evaluations & Feedback</h4>
          <div v-if="loadingEvals" class="loading">Загрузка отзывов...</div>
          <div v-else class="eval-list">
            <div v-for="(ev, idx) in details" :key="idx" class="eval-item" :class="ev.status.toLowerCase()">
              <div class="eval-meta">
                <strong>{{ ev.user }}</strong>
                <span class="status-tag">{{ getStatusIcon(ev.status) }} {{ ev.status }}</span>
                <small>{{ ev.date }}</small>
              </div>
              <p v-if="ev.comment" class="eval-comment">"{{ ev.comment }}"</p>
            </div>
            <div v-if="details.length === 0" class="empty-text">Оценок пока нет. Будьте первым!</div>
          </div>
        </section>

        <section class="detail-section">
          <h4>General Discussion ({{ totalComments }})</h4>
          <div class="comments-list">
            <div v-for="c in comments" :key="c.id" class="comment-row">
              <div class="comment-author">{{ c.user_nickname }} <small>{{ c.created_at }}</small></div>
              <div class="comment-text">{{ c.text }}</div>
            </div>
            <div v-if="comments.length === 0" class="empty-text">Комментариев нет.</div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import {ref, watch} from 'vue'
import {apiRequest} from '@/api/client.js'
import ReactionVisualizer from '@/components/results/ReactionVisualizer.vue'

const props = defineProps({
  isOpen: Boolean,
  reaction: Object // Передаем весь объект из таблицы
})
const emit = defineEmits(['close'])

const details = ref([])
const comments = ref([])
const totalComments = ref(0)
const loadingEvals = ref(false)

const getStatusIcon = (status) => {
  if (status === 'CHECK') return '✅'
  if (status === 'POO') return '💩'
  return '🛑'
}

const loadExtraData = async () => {
  if (!props.reaction?.id) return

  loadingEvals.value = true
  try {
    // 1. Грузим детали оценок
    const resEval = await apiRequest(`/evaluations/details?target=REACTIONS&entry_id=${props.reaction.id}`)
    if (resEval.ok) {
      details.value = await resEval.json() // Распаковываем JSON
    }

    // 2. Грузим комментарии
    const resComm = await apiRequest(`/comments/list?target=REACTIONS&entry_id=${props.reaction.id}`)
    if (resComm.ok) {
      const commData = await resComm.json()
      comments.value = commData.items
      totalComments.value = commData.total
    }
  } catch (err) {
    console.error("Ошибка при загрузке деталей:", err)
  } finally {
    loadingEvals.value = false
  }
}

watch(() => props.isOpen, (newVal) => {
  if (newVal) loadExtraData()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.modal-card {
  background: white;
  width: 100%;
  max-width: 900px;
  max-height: 90vh;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  padding: 15px 25px;
  background: #f8f9fa;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-body {
  padding: 25px;
  overflow-y: auto;
  flex: 1;
}

/* Grid для картинок */
.viz-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.viz-item {
  background: #fff;
  border: 1px solid #f0f0f0;
  padding: 10px;
  border-radius: 8px;
}

.img-wrap {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #eee;
  margin-bottom: 8px;
}

.smiles-debug {
  font-size: 0.7rem;
  color: #999;
  word-break: break-all;
  display: block;
  max-height: 40px;
  overflow-y: auto;
}

/* Поля данных */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 15px;
  margin: 20px 0;
}

.info-group label {
  font-weight: bold;
  color: #666;
  font-size: 0.85rem;
  display: block;
  margin-bottom: 4px;
}

.full-width {
  grid-column: span 3;
}

.yield-badge {
  background: #42b983;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: bold;
}

.text-content {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.4;
}

.italic {
  font-style: italic;
  color: #555;
}

.procedure-box {
  background: #f4f7f6;
  padding: 15px;
  border-left: 4px solid #42b983;
  font-family: monospace;
  white-space: pre-wrap;
  margin-top: 10px;
}

/* Оценки */
.eval-item {
  padding: 10px;
  border-radius: 6px;
  margin-bottom: 10px;
  border-left: 5px solid #ccc;
  background: #fafafa;
}

.eval-item.check {
  border-color: #42b983;
}

.eval-item.poo {
  border-color: #795548;
}

.eval-item.error {
  border-color: #f44336;
}

.status-tag {
  font-weight: bold;
  margin-left: 10px;
  font-size: 0.8rem;
  text-transform: uppercase;
}

.comment-row {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.comment-author {
  font-weight: bold;
  font-size: 0.85rem;
}

.empty-text {
  color: #aaa;
  font-style: italic;
}

@media (max-width: 768px) {
  .viz-grid, .info-grid {
    grid-template-columns: 1fr;
  }

  .full-width {
    grid-column: span 1;
  }
}
</style>