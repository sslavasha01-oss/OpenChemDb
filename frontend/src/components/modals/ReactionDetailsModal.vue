<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-card">
      <header class="modal-header">
        <h2>Reaction Details #{{ reaction.id }}</h2>
        <button class="close-btn" @click="emit('close')">&times;</button>
      </header>

      <div class="modal-body">
        <section class="viz-container">
          <div class="viz-block">
            <div class="viz-header">
              <h4>Raw Structure (Original)</h4>
              <code class="smiles-copy">{{ reaction.reaction_raw_smiles }}</code>
            </div>
            <div class="full-img-wrap">
              <ReactionVisualizer :smiles="reaction.reaction_raw_smiles" />
            </div>
          </div>

          <div class="viz-block" v-if="reaction.reaction_mapped_smiles">
            <div class="viz-header">
              <h4>Mapped Structure (Atom-to-Atom)</h4>
              <code class="smiles-copy">{{ reaction.reaction_mapped_smiles }}</code>
            </div>
            <div class="full-img-wrap mapped">
              <ReactionVisualizer :smiles="reaction.reaction_mapped_smiles" />
            </div>
          </div>
        </section>

        <div class="main-info-grid">
          <div class="meta-item"><strong>External ID:</strong> {{ reaction.external_id || 'N/A' }}</div>
          <div class="meta-item">
            <strong>DOI:</strong>
            <a v-if="reaction.doi" :href="'https://doi.org/' + reaction.doi" target="_blank">{{ reaction.doi }}</a>
            <span v-else>N/A</span>
          </div>
          <div class="meta-item"><strong>Yield:</strong> <span class="yield">{{ reaction.yield_text || '—' }}%</span></div>

          <div class="meta-full">
            <strong>Conditions:</strong>
            <p>{{ reaction.conditions || 'Standard conditions' }}</p>
          </div>

          <div class="meta-full">
            <strong>Reference:</strong>
            <p class="italic">{{ reaction.references }}</p>
          </div>
        </div>

        <section class="procedure-section" v-if="reaction.procedure">
          <h4>Experimental Procedure</h4>
          <div class="procedure-box">{{ reaction.procedure }}</div>
        </section>

        <hr />

        <SocialActivity target="REACTIONS" :entryId="reaction.id" />
      </div>
    </div>
  </div>
</template>

<script setup>
import ReactionVisualizer from '@/components/results/ReactionVisualizer.vue'
import SocialActivity from '@/components/shared/SocialActivity.vue'

const props = defineProps({ isOpen: Boolean, reaction: Object })
const emit = defineEmits(['close'])
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 2000; padding: 20px; }
.modal-card { background: white; width: 100%; max-width: 1000px; max-height: 95vh; border-radius: 12px; display: flex; flex-direction: column; }
.modal-body { padding: 30px; overflow-y: auto; }

/* Картинки на всю ширину */
.viz-block { margin-bottom: 30px; border: 1px solid #eee; border-radius: 8px; overflow: hidden; }
.viz-header { display: flex; justify-content: space-between; align-items: center; background: #fcfcfc; padding: 8px 15px; border-bottom: 1px solid #eee; }
.viz-header h4 { margin: 0; color: #444; }
.full-img-wrap { width: 100%; min-height: 350px; background: white; display: flex; align-items: center; justify-content: center; padding: 20px; }
.smiles-copy { font-size: 0.7rem; background: #eee; padding: 2px 6px; border-radius: 4px; max-width: 50%; overflow: hidden; text-overflow: ellipsis; }

/* Сетка инфо */
.main-info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 25px 0; background: #f9f9f9; padding: 20px; border-radius: 8px; }
.meta-full { grid-column: span 3; }
.yield { color: #42b983; font-weight: bold; font-size: 1.1rem; }
.procedure-box { background: #2c3e50; color: #ecf0f1; padding: 20px; border-radius: 8px; font-family: 'Courier New', monospace; white-space: pre-wrap; line-height: 1.5; margin-top: 10px; }
</style>