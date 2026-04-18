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

          <div class="comment-footer">
            <div class="comment-actions-right">
              <button class="btn-action" title="Полезно" @click="toggleReaction(c.id, 'USEFUL')">
                👍 {{ reactionsMap[c.id]?.USEFUL || 0 }}
              </button>

              <button class="btn-action" title="Не полезно" @click="toggleReaction(c.id, 'NOT_USEFUL')">
                👎 {{ reactionsMap[c.id]?.NOT_USEFUL || 0 }}
              </button>

              <button class="btn-action clickable-icon" title="Показать ответы" @click="toggleReplies(c.id)">
  💬             {{ repliesMap[c.id] || 0 }}
              </button>

              <button class="btn-reply" @click="toggleReplyForm(c.id)">
                ↩️ {{ replyingToId === c.id ? 'Отмена' : 'Ответить' }}
              </button>
            </div>
          </div>

          <div v-if="replyingToId === c.id" class="reply-input-block">
            <textarea
              v-model="replyText"
              placeholder="Напишите ваш ответ..."
              rows="2"
              :disabled="isSubmittingReply"
            ></textarea>
            <div class="reply-actions">
              <button
                @click="submitReply(c.id)"
                :disabled="isSubmittingReply || !replyText.trim()"
                class="btn-send-reply"
              >
                {{ isSubmittingReply ? 'Отправка...' : 'Ответить' }}
              </button>
            </div>
          </div>
            <div v-if="expandedReplies.has(c.id)" class="replies-list">
              <div v-for="r in (repliesData[c.id] || [])" :key="r.id" class="reply-item">
                <div class="comment-author">
                  {{ r.user_nickname }} <small>{{ r.created_at }}</small>
                </div>
                <div class="comment-text">{{ r.content }}</div>
                <div class="comment-footer">
                  <div class="comment-actions-right">
                    <button class="btn-action small" @click="toggleReaction(r.id, 'USEFUL', 'REPLY')">
                      👍 {{ replyReactionsMap[r.id]?.USEFUL || 0 }}
                    </button>
                    <button class="btn-action small" @click="toggleReaction(r.id, 'NOT_USEFUL', 'REPLY')">
                      👎 {{ replyReactionsMap[r.id]?.NOT_USEFUL || 0 }}
                    </button>
                    <button class="btn-reply small" @click="toggleReplyForm(r.id)">
                      ↩️ Ответить
                    </button>
                  </div>
                </div>
                <div v-if="replyingToId === r.id" class="reply-input-block nested">
                 <textarea
                     v-model="replyText"
                     placeholder="Напишите ваш ответ..."
                     rows="2"
                     :disabled="isSubmittingReply"
                   ></textarea>
                   <div class="reply-actions">
                     <button
                       @click="submitReply(c.id)"
                       :disabled="isSubmittingReply || !replyText.trim()"
                       class="btn-send-reply"
                     >
                       {{ isSubmittingReply ? 'Отправка...' : 'Ответить' }}
                     </button>
                   </div>
                 </div>
              </div>

              <div v-if="repliesData[c.id]?.length < (repliesMap[c.id] || 0)" class="pagination-wrapper-mini">
               <button class="btn-load-more-mini" @click="loadMoreReplies(c.id)">
                  Показать еще ответы
               </button>
              </div>

            </div>
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

const reactionsMap = ref({}) // { commentId: { USEFUL: 0, NOT_USEFUL: 0 } }
const repliesMap = ref({})   // { commentId: count }

const expandedReplies = ref(new Set()) // ID комментариев, у которых развернуты ответы
const repliesData = ref({})            // { commentId: [ответ1, ответ2...] }
const replyReactionsMap = ref({})      // { replyId: { USEFUL: 0, NOT_USEFUL: 0 } }

const replyingToId = ref(null)
const replyText = ref('')
const isSubmittingReply = ref(false)
const replyLimit = 5

const commentText = ref('')
const isSubmittingComment = ref(false)
const showCommentInput = ref(false)

const loadingMore = ref(false)
const limit = 10

const submitComment = async () => {
  if (!commentText.value.trim()) return
  isSubmittingComment.value = true
  try {
    const response = await apiRequest(
      `/comments/add?target=${props.target}&entry_id=${props.entryId}&content=${encodeURIComponent(commentText.value)}`,
      { method: 'POST' }
    )
    if (response.ok) {
      commentText.value = ''
      showCommentInput.value = false
      await loadData()
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

const submitReply = async (commentId) => {
  if (!replyText.value.trim()) return
  isSubmittingReply.value = true
  try {
    const response = await apiRequest(
      `/comments/reply/add?comment_id=${commentId}&content=${encodeURIComponent(replyText.value)}`,
      { method: 'POST' }
    )
    if (response.ok) {
      replyText.value = ''
      replyingToId.value = null // Закрываем форму
      repliesMap.value[commentId] = (repliesMap.value[commentId] || 0) + 1

      // Если ветка уже была развернута, подгружаем свежие данные в конец
      if (expandedReplies.value.has(commentId)) {
        await fetchReplies(commentId, 0) // Перезагружаем или можно просто догрузить последний
      }
    } else {
      const errorData = await response.json()
      alert(errorData.detail || "Ошибка при добавлении ответа")
    }
  } catch (e) {
    console.error("Reply submit error:", e)
  } finally {
    isSubmittingReply.value = false
  }
}

const toggleReplyForm = (id) => {
  replyingToId.value = replyingToId.value === id ? null : id
  replyText.value = ''
}

const loadSocialCounts = async (commentIds) => {
  if (!commentIds || commentIds.length === 0) return
  try {
    const reactionParams = new URLSearchParams()
    reactionParams.append('target_type', 'COMMENT')
    commentIds.forEach(id => reactionParams.append('target_ids', id))

    const replyParams = new URLSearchParams()
    commentIds.forEach(id => replyParams.append('comment_ids', id))

    const [resReactions, resReplies] = await Promise.all([
      apiRequest(`/comment_reaction/count?${reactionParams.toString()}`, { method: 'GET' }),
      apiRequest(`/comments/replies-batch-count?${replyParams.toString()}`, { method: 'GET' })
    ])
    if (resReactions.ok) {
      const data = await resReactions.json()
      reactionsMap.value = { ...reactionsMap.value, ...data }
    }
    if (resReplies.ok) {
      const data = await resReplies.json()
      repliesMap.value = { ...repliesMap.value, ...data }
    }
  } catch (e) {
    console.error("Error loading social counts:", e)
  }
}

const getStatusIcon = (s) => ({ 'CHECK': '✅', 'POO': '💩', 'ERROR': '🛑' }[s] || '❓')

const loadData = async () => {
  if (!props.entryId) return
  loading.value = true
  try {
    const [resEval, resComm] = await Promise.all([
      apiRequest(`/evaluations/details?target=${props.target}&entry_id=${props.entryId}`),
      apiRequest(`/comments/list?target=${props.target}&entry_id=${props.entryId}&limit=${limit}&offset=0`)
    ])
    if (resEval.ok) evaluations.value = await resEval.json()
    if (resComm.ok) {
      const data = await resComm.json()
      comments.value = data.items
      loadSocialCounts(data.items.map(c => c.id))
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
      comments.value = [...comments.value, ...data.items]
      loadSocialCounts(data.items.map(c => c.id))
      totalComments.value = data.total
    }
  } catch (e) {
    console.error("Load more error:", e)
  } finally {
    loadingMore.value = false
  }
}

const toggleReaction = async (id, type, targetType = 'COMMENT') => {
  try {
    const response = await apiRequest(
      `/comment_reaction/add?target_type=${targetType}&target_id=${id}&reaction=${type}`,
      { method: 'POST' }
    )
    if (response.ok) {
      const map = targetType === 'COMMENT' ? reactionsMap : replyReactionsMap
      if (!map.value[id]) map.value[id] = { USEFUL: 0, NOT_USEFUL: 0 }
      map.value[id][type]++
    }
  } catch (e) { console.error("Reaction error:", e) }
}

const toggleReplies = async (commentId) => {
  if (expandedReplies.value.has(commentId)) {
    expandedReplies.value.delete(commentId)
  } else {
    expandedReplies.value.add(commentId)
    // Загружаем только если данных еще нет
    if (!repliesData.value[commentId]) {
      await fetchReplies(commentId, 0)
    }
  }
}

const fetchReplies = async (commentId, offset) => {
  try {
    const res = await apiRequest(`/comments/replies/${commentId}?limit=${replyLimit}&offset=${offset}`)
    if (res.ok) {
      const newData = await res.json()

      // Если это первая загрузка — заменяем, если дозагрузка — склеиваем
      if (offset === 0) {
        repliesData.value[commentId] = newData
      } else {
        repliesData.value[commentId] = [...repliesData.value[commentId], ...newData]
      }

      if (newData.length > 0) {
        const replyIds = newData.map(r => r.id)
        const params = new URLSearchParams()
        params.append('target_type', 'REPLY')
        replyIds.forEach(id => params.append('target_ids', id))

        const resReact = await apiRequest(`/comment_reaction/count?${params.toString()}`)
        if (resReact.ok) {
          replyReactionsMap.value = { ...replyReactionsMap.value, ...(await resReact.json()) }
        }
      }
    }
  } catch (e) { console.error("Error loading replies:", e) }
}

const loadMoreReplies = async (commentId) => {
  const currentOffset = repliesData.value[commentId]?.length || 0
  await fetchReplies(commentId, currentOffset)
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
  background: #42b983; color: white; border: none; padding: 6px 12px;
  border-radius: 4px; cursor: pointer; font-size: 0.8rem; font-weight: bold;
}
.btn-comment-toggle {
  background: none; border: 1px solid #3498db; color: #3498db;
  padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem;
}

.add-comment-block {
  margin-bottom: 20px; background: #f9f9f9; padding: 10px; border-radius: 8px; border: 1px solid #eee;
}
.add-comment-block textarea {
  width: 100%; border: 1px solid #ddd; border-radius: 4px; padding: 8px; resize: vertical; box-sizing: border-box;
}
.btn-send-comment {
  background: #3498db; color: white; border: none; padding: 6px 15px; border-radius: 4px; cursor: pointer; font-weight: bold;
}

.comment-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
.comment-actions-right {
  display: flex;
  align-items: center;
  gap: 15px;
  font-size: 0.85rem;
  color: #666;
}

.btn-action {
  background: none; border: 1px solid transparent; border-radius: 4px;
  cursor: pointer; color: #666; font-size: 0.85rem; padding: 2px 6px;
  display: flex; align-items: center; gap: 4px;
}
.btn-action:hover { background: #f0f2f5; border-color: #ddd; }

.btn-reply {
  background: none; border: none; color: #3498db; cursor: pointer; font-size: 0.85rem;
}

/* ИСПРАВЛЕННЫЕ СТИЛИ ОТВЕТА */
.reply-input-block {
  display: block;
  margin-top: 10px;
  margin-left: 30px; /* Отступ для визуальной вложенности */
  padding: 12px;
  background: #f8fbff;
  border-radius: 8px;
  border: 1px solid #d0e3ff;
  border-left: 4px solid #3498db;
  box-sizing: border-box;
}
.reply-input-block textarea {
  width: 100%;
  border: 1px solid #ccd6e0;
  border-radius: 4px;
  padding: 8px;
  font-size: 0.9rem;
  resize: none;
  box-sizing: border-box;
  display: block;
  margin-bottom: 8px;
}
.reply-actions {
  display: flex;
  justify-content: flex-end;
}
.btn-send-reply {
  background: #3498db; color: white; border: none; padding: 5px 15px;
  border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 0.85rem;
}
.btn-send-reply:disabled { background: #ccc; }

.pagination-wrapper { display: flex; justify-content: center; margin-top: 15px; }
.btn-load-more {
  background: #f0f2f5; border: 1px solid #ddd; color: #555;
  padding: 8px 20px; border-radius: 20px; cursor: pointer;
}

.replies-list {
  margin-left: 40px;
  border-left: 2px solid #eee;
  padding-left: 15px;
  margin-top: 10px;
}
.reply-item {
  padding: 8px 0;
  border-bottom: 1px solid #f9f9f9;
}
.btn-action.small { font-size: 0.75rem; padding: 1px 4px; }
.clickable-icon { cursor: pointer !important; color: #3498db; }

.pagination-wrapper-mini {
  display: flex;
  justify-content: flex-start;
  padding: 5px 0;
}
.btn-load-more-mini {
  background: none;
  border: none;
  color: #3498db;
  font-size: 0.75rem;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
}
.btn-load-more-mini:hover {
  color: #2980b9;
}

.btn-reply.small {
  font-size: 0.75rem;
  margin-left: 10px;
}

.reply-input-block.nested {
  max-width: 90%; /* Чтобы форма была чуть уже самого ответа */
  margin-left: auto; /* Сдвинет её немного вправо для красоты */
}

.reply-item .comment-footer {
  justify-content: flex-start; /* У ответов лучше прижать кнопки к левому краю */
}
</style>