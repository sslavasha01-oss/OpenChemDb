<template>
  <div class="social-wrapper">
    <section class="social-section">
      <div class="section-header">
    <h4>User Evaluations & Feedback</h4>
    <button class="btn-add-eval" @click="emit('request-add-eval')">
      + Оценить {{ target === 'REACTIONS' ? 'реакцию' : 'объект' }}
    </button>
  </div>


      <div v-if="loading" class="loading-mini">Loading evaluations...</div>
      <div v-else class="eval-list">
        <div v-for="(ev, idx) in evaluations" :key="idx" class="eval-item" :class="ev.status.toLowerCase()">
          <div class="eval-meta">
            <strong>{{ ev.user }}</strong>
            <span class="status-tag">{{ getStatusIcon(ev.status) }} {{ ev.status }}</span>
            <small>{{ ev.date }}</small>
          </div>
          <p v-if="ev.comment" class="eval-comment">"{{ ev.comment }}"</p>
        </div>
        <div v-if="evaluations.length === 0" class="empty-text">No evaluations yet.</div>
      </div>
    </section>

    <section class="social-section">
      <h4>General Discussion ({{ totalComments }})</h4>
      <div class="comments-list">
        <div v-for="c in comments" :key="c.id" class="comment-row">
          <div class="comment-author">{{ c.user_nickname }} <small>{{ c.created_at }}</small></div>
          <div class="comment-text">{{ c.text }}</div>
        </div>
        <div v-if="comments.length === 0" class="empty-text">No comments yet.</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { apiRequest } from '@/api/client.js'

const props = defineProps({
  target: { type: String, required: true }, // 'REACTIONS' или 'BOOKS'
  entryId: { type: Number, required: true }
})

const emit = defineEmits(['request-add-eval'])
const evaluations = ref([])
const comments = ref([])
const totalComments = ref(0)
const loading = ref(false)

const getStatusIcon = (s) => ({ 'CHECK': '✅', 'POO': '💩', 'ERROR': '🛑' }[s] || '❓')

const loadData = async () => {
  if (!props.entryId) return
  loading.value = true
  try {
    const [resEval, resComm] = await Promise.all([
      apiRequest(`/evaluations/details?target=${props.target}&entry_id=${props.entryId}`),
      apiRequest(`/comments/list?target=${props.target}&entry_id=${props.entryId}`)
    ])

    if (resEval.ok) evaluations.value = await resEval.json()
    if (resComm.ok) {
      const data = await resComm.json()
      comments.value = data.items
      totalComments.value = data.total
    }
  } catch (e) {
    console.error("Social data load error:", e)
  } finally {
    loading.value = false
  }
}

watch(() => props.entryId, loadData)
onMounted(loadData)
defineExpose({ loadData })
</script>

<style scoped>
.social-section { margin-top: 25px; }
.eval-item { padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid #ccc; background: #fafafa; }
.eval-item.check { border-color: #42b983; background: #f0fff4; }
.eval-item.poo { border-color: #795548; background: #fdf5f2; }
.eval-item.error { border-color: #f44336; background: #fff5f5; }
.status-tag { font-weight: bold; margin-left: 10px; font-size: 0.8rem; }
.comment-row { padding: 10px 0; border-bottom: 1px solid #eee; }
.comment-author { font-weight: bold; font-size: 0.85rem; color: #555; }
.comment-text { margin-top: 4px; font-size: 0.95rem; }
.empty-text { color: #aaa; font-style: italic; padding: 10px 0; }
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}
.btn-add-eval {
  background: #42b983;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: bold;
  transition: 0.2s;
}
.btn-add-eval:hover { background: #3aa876; }
</style>