<template>
  <div class="social-wrapper">
    <section class="social-section">
      <div class="section-header">
        <h4>User Evaluations & Feedback</h4>
        <button class="btn-add-eval" @click="emit('request-add-eval')">
          + Rate {{ target === 'REACTIONS' ? 'reaction' : 'record' }}
        </button>
      </div>
      <div v-if="loading" class="loading-mini">Loading evaluations...</div>
      <div v-else class="eval-list">
        <div v-for="(ev, idx) in evaluations" :key="idx" class="eval-item" :class="ev.status.toLowerCase()">
          <div class="eval-meta">
            <div>
              <strong>{{ ev.user }}</strong>
              <span class="status-tag">{{ getStatusIcon(ev.status) }} {{ ev.status }}</span>
              <small class="eval-date">{{ ev.date }}</small>
            </div>

            <div v-if="ev.user_id === currentUserId" class="eval-owner-actions">
              <button class="btn-icon-action" title="Edit comment" @click="startEditEval(ev)">✏️</button>
              <button class="btn-icon-action btn-delete" title="Delete evaluation" @click="deleteEval(ev)">❌</button>
            </div>
          </div>

          <div v-if="editingEvalId === ev.user_id" class="eval-edit-block">
            <textarea
              v-model="editCommentText"
              rows="2"
              placeholder="Edit your comment..."
              :disabled="isSubmittingEvalEdit"
            ></textarea>
            <div class="eval-edit-buttons">
              <button class="btn-save-mini" @click="saveEditEval(ev)" :disabled="isSubmittingEvalEdit">Save</button>
              <button class="btn-cancel-mini" @click="cancelEditEval" :disabled="isSubmittingEvalEdit">Cancel</button>
            </div>
          </div>

          <p v-else-if="ev.comment" class="eval-comment">"{{ ev.comment }}"</p>
        </div>
        <div v-if="evaluations.length === 0" class="empty-text">No evaluations yet.</div>
      </div>
    </section>

    <section class="social-section">
      <div class="section-header">
        <h4>General Discussion ({{ totalComments }})</h4>
        <button class="btn-comment-toggle" @click="showCommentInput = !showCommentInput">
          {{ showCommentInput ? 'Cancel' : 'Comment' }}
        </button>
      </div>

      <div v-if="showCommentInput" class="add-comment-block">
        <textarea
          v-model="commentText"
          placeholder="Write your comment..."
          rows="3"
          :disabled="isSubmittingComment"
        ></textarea>
        <div class="comment-actions">
          <button
            @click="submitComment"
            :disabled="isSubmittingComment || !commentText.trim()"
            class="btn-send-comment"
          >
            {{ isSubmittingComment ? 'Sending...' : 'Post' }}
          </button>
        </div>
      </div>

      <div class="comments-list">
        <div v-for="c in comments" :key="c.id" class="comment-row">
          <div class="comment-author-wrapper">
            <div class="comment-author">
              {{ c.user_nickname }} <small>{{ c.created_at }}</small>
            </div>
            <div v-if="c.user_id === currentUserId" class="comment-owner-actions">
              <button class="btn-icon-action" title="Edit" @click="startEditComment(c)">✏️</button>
              <button class="btn-icon-action btn-delete" title="Delete" @click="deleteComment(c)">❌</button>
            </div>
          </div>

          <div v-if="editingCommentId === c.id" class="eval-edit-block" style="margin-bottom: 10px;">
            <textarea v-model="editCommentTextGlobal" rows="2" :disabled="isSubmittingCommentEdit"></textarea>
            <div class="eval-edit-buttons">
              <button class="btn-save-mini" @click="saveEditComment(c)" :disabled="isSubmittingCommentEdit">Save</button>
              <button class="btn-cancel-mini" @click="cancelEditComment" :disabled="isSubmittingCommentEdit">Cancel</button>
            </div>
          </div>
          <div class="comment-text">{{ c.content }}</div>

          <div class="comment-footer">
            <div class="comment-actions-right">
              <button class="btn-action" title="Helpful" @click="toggleReaction(c.id, 'USEFUL')">
                👍 {{ reactionsMap[c.id]?.USEFUL || 0 }}
              </button>

              <button class="btn-action" title="Not helpful" @click="toggleReaction(c.id, 'NOT_USEFUL')">
                👎 {{ reactionsMap[c.id]?.NOT_USEFUL || 0 }}
              </button>

              <button class="btn-action clickable-icon" title="Show replies" @click="toggleReplies(c.id)">
  💬             {{ repliesMap[c.id] || 0 }}
              </button>

              <button class="btn-reply" @click="toggleReplyForm(c.id)">
                ↩️ {{ replyingToId === c.id ? 'Cancel' : 'Reply' }}
              </button>
            </div>
          </div>

          <div v-if="replyingToId === c.id" class="reply-input-block">
            <textarea
              v-model="replyText"
              placeholder="Write your reply..."
              rows="2"
              :disabled="isSubmittingReply"
            ></textarea>
            <div class="reply-actions">
              <button
                @click="submitReply(c.id)"
                :disabled="isSubmittingReply || !replyText.trim()"
                class="btn-send-reply"
              >
                {{ isSubmittingReply ? 'Sending...' : 'Reply' }}
              </button>
            </div>
          </div>
            <div v-if="expandedReplies.has(c.id)" class="replies-list">
              <div v-for="r in (repliesData[c.id] || [])" :key="r.id" class="reply-item">
                <div class="comment-author-wrapper">
                  <div class="comment-author">
                    {{ r.user_nickname }} <small>{{ r.created_at }}</small>
                  </div>
                  <div v-if="r.user_id === currentUserId" class="comment-owner-actions">
                    <button class="btn-icon-action" title="Edit" @click="startEditReply(r)">✏️</button>
                    <button class="btn-icon-action btn-delete" title="Delete" @click="deleteReply(c.id, r)">❌</button>
                  </div>
                </div>

                <div v-if="editingReplyId === r.id" class="eval-edit-block" style="margin-bottom: 10px;">
                  <textarea v-model="editReplyTextGlobal" rows="2" :disabled="isSubmittingReplyEdit"></textarea>
                  <div class="eval-edit-buttons">
                    <button class="btn-save-mini" @click="saveEditReply(c.id, r)" :disabled="isSubmittingReplyEdit">Save</button>
                    <button class="btn-cancel-mini" @click="cancelEditReply" :disabled="isSubmittingReplyEdit">Cancel</button>
                  </div>
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
                    <button class="btn-reply small" @click="toggleReplyForm(r.id, r.user_nickname)">
                     ↩️ Reply
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
                  Show more replies
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
            {{ loadingMore ? 'Loading...' : 'Show more' }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { apiRequest } from '@/api/client.js'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  target: { type: String, required: true }, // 'REACTIONS' или 'BOOKS'
  entryId: { type: Number, required: true }
})

const userStore = useUserStore()
const currentUserId = computed(() => userStore.currentUser?.id || null)

// Состояние для редактирования комментария оценки
const editingEvalId = ref(null) // Хранит user_id редактируемой оценки
const editCommentText = ref('')
const isSubmittingEvalEdit = ref(false)

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

const editingCommentId = ref(null)
const editCommentTextGlobal = ref('')
const isSubmittingCommentEdit = ref(false)

const editingReplyId = ref(null)
const editReplyTextGlobal = ref('')
const isSubmittingReplyEdit = ref(false)

const loadingMore = ref(false)
const limit = 10
const startEditEval = (ev) => {
  editingEvalId.value = ev.user_id
  editCommentText.value = ev.comment || ''
}

const cancelEditEval = () => {
  editingEvalId.value = null
  editCommentText.value = ''
}

const saveEditEval = async (ev) => {
  isSubmittingEvalEdit.value = true
  try {
    const response = await apiRequest(
      `/evaluations/update-comment?target=${props.target}&entry_id=${props.entryId}&comment=${encodeURIComponent(editCommentText.value)}`,
      { method: 'PATCH' }
    )
    if (response.ok) {
      ev.comment = editCommentText.value
      cancelEditEval()
    } else {
      const errorData = await response.json()
      alert(errorData.detail || "Error updating comment")
    }
  } catch (e) {
    console.error("Eval edit error:", e)
    alert("Failed to update comment")
  } finally {
    isSubmittingEvalEdit.value = false
  }
}

const deleteEval = async (ev) => {
  if (!confirm("Are you sure you want to delete your evaluation?")) return
  try {
    const response = await apiRequest(
      `/evaluations/delete?target=${props.target}&entry_id=${props.entryId}`,
      { method: 'DELETE' }
    )
    if (response.ok) {
      evaluations.value = evaluations.value.filter(item => item.user_id !== ev.user_id)
    } else {
      const errorData = await response.json()
      alert(errorData.detail || "Error deleting evaluation")
    }
  } catch (e) {
    console.error("Eval delete error:", e)
    alert("Failed to delete evaluation")
  }
}

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
      alert(errorData.detail || "Error adding comment")
    }
  } catch (e) {
    console.error("Comment submit error:", e)
    alert("Failed to send comment")
  } finally {
    isSubmittingComment.value = false
  }
}

const startEditComment = (c) => { editingCommentId.value = c.id; editCommentTextGlobal.value = c.content || ''; }
const cancelEditComment = () => { editingCommentId.value = null; editCommentTextGlobal.value = ''; }
const saveEditComment = async (c) => {
  if (!editCommentTextGlobal.value.trim()) return
  isSubmittingCommentEdit.value = true
  try {
    const res = await apiRequest(`/comments/${c.id}/edit?content=${encodeURIComponent(editCommentTextGlobal.value)}`, { method: 'PUT' })
    if (res.ok) { c.content = editCommentTextGlobal.value; cancelEditComment(); }
  } catch (e) { console.error(e) } finally { isSubmittingCommentEdit.value = false }
}
const deleteComment = async (c) => {
  if (!confirm("Delete comment?")) return
  try {
    const res = await apiRequest(`/comments/${c.id}/delete`, { method: 'DELETE' })
    if (res.ok) { comments.value = comments.value.filter(item => item.id !== c.id); totalComments.value = Math.max(0, totalComments.value - 1); }
  } catch (e) { console.error(e) }
}

const startEditReply = (r) => { editingReplyId.value = r.id; editReplyTextGlobal.value = r.content || ''; }
const cancelEditReply = () => { editingReplyId.value = null; editReplyTextGlobal.value = ''; }
const saveEditReply = async (commentId, r) => {
  if (!editReplyTextGlobal.value.trim()) return
  isSubmittingReplyEdit.value = true
  try {
    const res = await apiRequest(`/comments/reply/${r.id}/edit?content=${encodeURIComponent(editReplyTextGlobal.value)}`, { method: 'PUT' })
    if (res.ok) { r.content = editReplyTextGlobal.value; cancelEditReply(); }
  } catch (e) { console.error(e) } finally { isSubmittingReplyEdit.value = false }
}
const deleteReply = async (commentId, r) => {
  if (!confirm("Delete reply?")) return
  try {
    const res = await apiRequest(`/comments/reply/${r.id}/delete`, { method: 'DELETE' })
    if (res.ok) {
      if (repliesData.value[commentId]) repliesData.value[commentId] = repliesData.value[commentId].filter(item => item.id !== r.id)
      if (repliesMap.value[commentId] !== undefined) repliesMap.value[commentId] = Math.max(0, repliesMap.value[commentId] - 1)
    }
  } catch (e) { console.error(e) }
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
      alert(errorData.detail || "Error adding reply")
    }
  } catch (e) {
    console.error("Reply submit error:", e)
  } finally {
    isSubmittingReply.value = false
  }
}

const toggleReplyForm = (id, nickname = null) => {
  if (replyingToId.value === id) {
    replyingToId.value = null
    replyText.value = ''
  } else {
    replyingToId.value = id
    // Если передан никнейм, вставляем его в начало текста
    replyText.value = nickname ? `@${nickname}, ` : ''
  }
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
    if (resEval.ok) {
      evaluations.value = await resEval.json()
      console.log("EVALUATIONS DATA:", evaluations.value) // <-- Дебаг в консоль браузера
      console.log("CURRENT USER ID FROM STORE:", currentUserId.value)
    }
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
.eval-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.eval-date {
  margin-left: 10px;
  color: #888;
}

/* Кнопки действий над своей оценкой */
.eval-owner-actions {
  display: flex;
  gap: 8px;
}
.btn-icon-action {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 2px;
  opacity: 0.6;
  transition: opacity 0.2s;
}
.btn-icon-action:hover {
  opacity: 1;
}
.btn-delete:hover {
  filter: drop-shadow(0 0 2px rgba(244, 67, 54, 0.4));
}

/* Блок инлайнового редактирования текста */
.eval-edit-block {
  margin-top: 8px;
}
.eval-edit-block textarea {
  width: 100%;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 6px;
  resize: vertical;
  box-sizing: border-box;
  font-size: 0.9rem;
}
.eval-edit-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}
.btn-save-mini {
  background: #42b983; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; font-weight: bold;
}
.btn-cancel-mini {
  background: none; border: 1px solid #bbb; color: #666; padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem;
}
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

.comment-author-wrapper { display: flex; justify-content: space-between; align-items: center; }
.comment-owner-actions { display: flex; gap: 6px; }
</style>