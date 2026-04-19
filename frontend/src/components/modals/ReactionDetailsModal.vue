<template>
  <div v-if="isOpen && reaction" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-card">
      <header class="modal-header">
        <h2>Reaction Details #{{ reaction?.id }}</h2>
        <button class="close-btn" @click="emit('close')">&times;</button>
      </header>

      <div class="modal-body">
        <section class="viz-container">
          <div class="viz-block">
            <div class="viz-header">
              <h4>Reaction Structure</h4>
            </div>
            <div class="full-img-wrap" v-html="reaction?.svg_content || ''"></div>
          </div>

          <div class="text-data-block">
            <div class="viz-header">
              <h4>Reaction SMILES</h4>
            </div>
            <div class="smiles-display-box">
              <code>{{ reaction?.reaction_raw_smiles }}</code>
            </div>
          </div>

          <div class="text-data-block" v-if="reaction?.reaction_mapped_smiles">
            <div class="viz-header">
              <h4>Mapped SMILES</h4>
            </div>
            <div class="smiles-display-box">
              <code>{{ reaction?.reaction_mapped_smiles }}</code>
            </div>
          </div>
        </section>

        <div class="main-info-grid">
          <div class="meta-item"><strong>External ID:</strong> {{ reaction?.external_id || 'N/A' }}</div>
          <div class="meta-item">
            <div class="doi-list" v-if="reaction?.doi">
                <a
                  v-for="doi in parseDois(reaction.doi)"
                  :key="doi"
                  :href="'https://doi.org/' + doi"
                  target="_blank"
                  class="doi-link-item"
                >
                  {{ doi }}
                </a>
              </div>
              <span v-else>N/A</span>
          </div>
          <div class="meta-item"><strong>Yield:</strong> <span class="yield">{{ reaction?.yield_text || '—' }}%</span></div>

          <div class="meta-full">
            <strong>Conditions:</strong>
            <p class="pre-wrap">{{ formatText(reaction?.conditions) || 'Standard conditions' }}</p>
          </div>

          <div class="meta-full">
            <strong>Reference:</strong>
            <p class="italic pre-wrap">{{ formatText(reaction?.references) }}</p>
          </div>
        </div>

        <section class="procedure-section" v-if="reaction?.procedure">
          <h4>Experimental Procedure</h4>
          <div class="procedure-box">{{ formatText(reaction?.procedure) }}</div>
        </section>

        <hr />

        <SocialActivity
          ref="socialRef"
          target="REACTIONS"
          :entryId="reaction?.id"
          @request-add-eval="isEvalModalOpen = true"
        />
      </div>
    </div>

    <EvaluationModal
      :isOpen="isEvalModalOpen"
      :entryId="reaction?.id"
      target="REACTIONS"
      @close="isEvalModalOpen = false"
      @success="onEvalSuccess"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SocialActivity from '@/components/shared/SocialActivity.vue'
import EvaluationModal from '@/components/modals/EvaluationModal.vue'

const isEvalModalOpen = ref(false)
const socialRef = ref(null)

const props = defineProps({ isOpen: Boolean, reaction: Object })
const emit = defineEmits(['close'])

// Функция для замены <NL> на переносы строк
const formatText = (text) => {
  if (!text) return ''
  return text.replace(/<NL>/g, '\n')
}

// Функция для извлечения массива DOI
const parseDois = (doiString) => {
  if (!doiString) return []
  return doiString
    .split(/<NL>|\s|\n/)
    .map(d => d.trim())
    .filter(d => d.length > 0)
}

const onEvalSuccess = () => {
  // Вызываем метод loadData внутри SocialActivity, чтобы список обновился
  if (socialRef.value) {
    socialRef.value.loadData()
  }
}
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 2000; padding: 20px; }
.modal-card { background: white; width: 100%; max-width: 1000px; max-height: 95vh; border-radius: 12px; display: flex; flex-direction: column; box-shadow: 0 10px 40px rgba(0,0,0,0.3); }
.modal-body { padding: 30px; overflow-y: auto; }

.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; border-bottom: 1px solid #eee; }
.close-btn { background: none; border: none; font-size: 2rem; cursor: pointer; color: #999; }

/* Универсальный стиль для блоков с заголовками */
.viz-block, .text-data-block {
  margin-bottom: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.viz-header {
  background: #fcfcfc;
  padding: 10px 15px;
  border-bottom: 1px solid #eee;
}

.viz-header h4 {
  margin: 0;
  color: #444;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Контейнер для SVG */
.full-img-wrap {
  width: 100%;
  min-height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.full-img-wrap :deep(svg) {
  width: 100%;
  height: auto;
  max-height: 400px;
}

/* Стили для текстовых боксов SMILES */
.smiles-display-box {
  padding: 15px;
  background: #f8f9fa;
  word-break: break-all;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  color: #333;
}

/* Сетка инфо */
.main-info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 25px 0; background: #f9f9f9; padding: 20px; border-radius: 8px; }
.meta-full { grid-column: span 3; }
.yield { color: #42b983; font-weight: bold; font-size: 1.1rem; }
.italic { font-style: italic; color: #666; }

/* Процедура */
.procedure-box {
  background: #2c3e50;
  color: #ecf0f1;
  padding: 20px;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  line-height: 1.5;
  margin-top: 10px;
  border-left: 5px solid #42b983;
}

hr { border: 0; border-top: 1px solid #eee; margin: 30px 0; }

.pre-wrap {
  white-space: pre-line; /* Заставляет браузер уважать перенос строки \n */
  margin-top: 5px;
}

.doi-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 5px;
}

.doi-link-item {
  color: #3498db;
  text-decoration: none;
  font-size: 0.9rem;
  word-break: break-all;
}

.doi-link-item:hover {
  text-decoration: underline;
}

/* Уточнение для процедуры (там уже есть white-space: pre-wrap,
   но formatText уберет <NL>, чтобы они не дублировались) */
.procedure-box {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>