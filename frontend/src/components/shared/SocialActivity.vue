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
  <div class="section-header">
    <h4>General Discussion ({{ totalComments }})</h4>
    <button class="btn-comment-toggle" @click="showCommentInput = !showCommentInput">
      {{ showCommentInput ? 'Отмена' : 'Комментировать' }}
    </button>
  </div>

  <div v-if="showCommentInput" class="add-comment-block">
    <textarea
      v-model="commentText"
      placeholder="Напишите ваш комментарий..."
      rows="3"
      :disabled="isSubmittingComment"
    ></textarea>
    <div class="comment-actions">
      <button
        @click="submitComment"
        :disabled="isSubmittingComment || !commentText.trim()"
        class="btn-send-comment"
      >
        {{ isSubmittingComment ? 'Отправка...' : 'Отправить' }}
      </button>
    </div>
  </div>

  <div class="comments-list">
    <div v-for="c in comments" :key="c.id" class="comment-row">
      <div class="comment-author">
        {{ c.user_nickname }} <small>{{ c.created_at }}</small>
      </div>
      <div class="comment-text">{{ c.content }}</div>
    </div>

    <div v-if="comments.length === 0" class="empty-text">
      No comments yet.
    </div>
    <div v-if="comments.length < totalComments" class="pagination-wrapper">
      <button
        class="btn-load-more"
        @click="loadMoreComments"
        :disabled="loadingMore"
      >
        {{ loadingMore ? 'Загрузка...' : 'Показать еще' }}
      </button>
    </div>
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

const commentText = ref('')
const isSubmittingComment = ref(false)
const showCommentInput = ref(false)

const loadingMore = ref(false)
const limit = 10 // Количество за раз комментарии

const submitComment = async () => {
  if (!commentText.value.trim()) return

  isSubmittingComment.value = true
  try {
    // В FastAPI эндпоинте параметры target, entry_id и content
    // судя по всему принимаются как query-params (так как нет Body-модели)
    const response = await apiRequest(
      `/comments/add?target=${props.target}&entry_id=${props.entryId}&content=${encodeURIComponent(commentText.value)}`,
      { method: 'POST' }
    )

    if (response.ok) {
      commentText.value = ''
      showCommentInput.value = false
      await loadData() // Перезагружаем данные (и оценки, и комменты)
    } else {
      const errorData = await response.json()
      alert(errorData.detail || "Ошибка при добавлении комментария")
    }
  } catch (e) {
    console.error("Comment submit error:", e)
    alert("Не удалось отправить комментарий")
  } finally {
    isSubmittingComment.value = false
  }
}


const getStatusIcon = (s) => ({ 'CHECK': '✅', 'POO': '💩', 'ERROR': '🛑' }[s] || '❓')

const loadData = async () => {
  if (!props.entryId) return
  loading.value = true
  try {
    // При первичной загрузке сбрасываем offset на 0
    const [resEval, resComm] = await Promise.all([
      apiRequest(`/evaluations/details?target=${props.target}&entry_id=${props.entryId}`),
      apiRequest(`/comments/list?target=${props.target}&entry_id=${props.entryId}&limit=${limit}&offset=0`)
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

const loadMoreComments = async () => {
  if (loadingMore.value || comments.value.length >= totalComments.value) return

  loadingMore.value = true
  try {
    const currentOffset = comments.value.length
    const res = await apiRequest(`/comments/list?target=${props.target}&entry_id=${props.entryId}&limit=${limit}&offset=${currentOffset}`)

    if (res.ok) {
      const data = await res.json()
      // Добавляем новые комменты в конец существующего массива
      comments.value = [...comments.value, ...data.items]
      totalComments.value = data.total
    }
  } catch (e) {
    console.error("Load more error:", e)
  } finally {
    loadingMore.value = false
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

.btn-comment-toggle {
  background: none;
  border: 1px solid #3498db;
  color: #3498db;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-comment-toggle:hover {
  background: #f0f7ff;
}

/* Блок ввода */
.add-comment-block {
  margin-bottom: 20px;
  background: #f9f9f9;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #eee;
}

.add-comment-block textarea {
  width: 100%;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 8px;
  resize: vertical;
  box-sizing: border-box;
  font-family: inherit;
}

.comment-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.btn-send-comment {
  background: #3498db;
  color: white;
  border: none;
  padding: 6px 15px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-send-comment:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* Небольшой отступ для списка, если форма открыта */
.comments-list {
  margin-top: 10px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 15px;
  padding-bottom: 10px;
}

.btn-load-more {
  background: #f0f2f5;
  border: 1px solid #ddd;
  color: #555;
  padding: 8px 20px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.btn-load-more:hover:not(:disabled) {
  background: #e4e6e9;
  border-color: #ccc;
}

.btn-load-more:disabled {
  opacity: 0.6;
  cursor: wait;
}
</style>