<template>
  <div v-if="isOpen && item" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-card">
      <header class="modal-header">
        <h2>Book Entry Details #{{ item?.id }}</h2>
        <button class="close-btn" @click="emit('close')">&times;</button>
      </header>

      <div class="modal-body">
        <section class="viz-container">
          <div class="viz-block">
            <div class="viz-header"><h4>Structure</h4></div>
            <div class="full-img-wrap" v-html="item?.svg_content || ''"></div>
          </div>

          <div class="text-data-block">
            <div class="viz-header"><h4>SMILES</h4></div>
            <div class="smiles-display-box">
              <code>{{ item?.smiles }}</code>
            </div>
          </div>
        </section>

        <div class="main-info-grid">
          <div class="meta-full">
            <strong>Name / Substance:</strong>
            <p class="name-text">{{ item?.name || 'N/A' }}</p>
          </div>

          <div class="meta-full">
            <strong>References:</strong>
            <p class="pre-wrap italic">{{ formatText(item?.references) }}</p>
          </div>

          <div class="meta-item">
            <strong>Source Book:</strong>
            <div>
              <a href="#" class="book-link-modal" @click.prevent="emit('open-book-files', item.book_name)">
                {{ getShortName(item.book_name) }}
              </a>
            </div>
          </div>

          <div class="meta-item">
            <strong>Pages:</strong>
            <div class="pages-links-container">
              <a
                v-for="(page, idx) in parsePages(item.pages)"
                :key="idx"
                :href="'/api/files/view?file_path=' + encodeURIComponent(page.fullPath)"
                target="_blank"
                class="page-link-modal"
              >
                {{ page.fileName }}
              </a>
              <span v-if="!item.pages">—</span>
            </div>
          </div>

          <div class="meta-item">
            <strong>Added Date:</strong>
            <div class="date-text">{{ formatDate(item?.created_at) }}</div>
          </div>
        </div>

        <hr />

        <SocialActivity
          ref="socialRef"
          target="BOOKS"
          :entryId="item?.external_id"
          @request-add-eval="isEvalModalOpen = true"
        />
      </div>
    </div>

    <EvaluationModal
      :isOpen="isEvalModalOpen"
      :entryId="item?.external_id"
      target="BOOKS"
      @close="isEvalModalOpen = false"
      @success="onEvalSuccess"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SocialActivity from '@/components/shared/SocialActivity.vue'
import EvaluationModal from '@/components/modals/EvaluationModal.vue'

const props = defineProps({
  isOpen: Boolean,
  item: Object
})
const emit = defineEmits(['close', 'open-book-files'])

const isEvalModalOpen = ref(false)
const socialRef = ref(null)

// Хелперы
const formatText = (text) => text ? text.replace(/<NL>/g, '\n') : ''

const getShortName = (path) => {
  if (!path) return '—'
  return path.split(/[\\/]/).pop()
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString('en-US') + ' ' + new Date(dateStr).toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})
}

const parsePages = (pagesRaw) => {
  if (!pagesRaw) return []
  return pagesRaw.toString().replace(/<NL>/g, '\n').split(/\r?\n/)
    .filter(p => p.trim() !== '')
    .map(path => ({
      fullPath: path.trim(),
      fileName: path.trim().split(/[\\/]/).pop()
    }))
}

const onEvalSuccess = () => {
  if (socialRef.value) socialRef.value.loadData()
}
</script>

<style scoped>
/* Используем твои базовые стили с небольшими правками */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center; z-index: 9999; padding: 20px; }
.modal-card { background: white; width: 100%; max-width: 900px; max-height: 95vh; border-radius: 12px; display: flex; flex-direction: column; box-shadow: 0 10px 50px rgba(0,0,0,0.5); }
.modal-body { padding: 25px; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 15px 25px; border-bottom: 1px solid #eee; }
.close-btn { background: none; border: none; font-size: 2rem; cursor: pointer; color: #999; }

.viz-block, .text-data-block { margin-bottom: 15px; border: 1px solid #eee; border-radius: 8px; background: white; }
.viz-header { background: #fcfcfc; padding: 8px 15px; border-bottom: 1px solid #eee; }
.viz-header h4 { margin: 0; color: #666; font-size: 0.75rem; text-transform: uppercase; }

.full-img-wrap { width: 100%; display: flex; justify-content: center; padding: 15px; background: #fff; }
.full-img-wrap :deep(svg) { max-width: 100%; height: auto; max-height: 350px; }

.smiles-display-box { padding: 12px; background: #f8f9fa; word-break: break-all; font-family: monospace; font-size: 0.85rem; }

.main-info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 20px; background: #f9f9f9; padding: 20px; border-radius: 8px; }
.meta-full { grid-column: span 3; }
.meta-item { display: flex; flex-direction: column; gap: 5px; }

.name-text { font-size: 1.1rem; font-weight: bold; color: #2c3e50; margin: 5px 0; }
.pre-wrap { white-space: pre-line; margin-top: 5px; }
.italic { font-style: italic; color: #555; }

/* Стили ссылок */
.book-link-modal { color: #42b983; font-weight: bold; text-decoration: none; border-bottom: 1px dashed #42b983; }
.pages-links-container { display: flex; flex-wrap: wrap; gap: 8px; }
.page-link-modal { background: #ebf5f0; color: #2c3e50; padding: 2px 8px; border-radius: 4px; text-decoration: none; font-size: 0.85rem; border: 1px solid #d1eadd; }
.page-link-modal:hover { background: #42b983; color: white; }

.date-text { color: #888; font-size: 0.9rem; }
hr { border: 0; border-top: 1px solid #eee; margin: 25px 0; }
</style>