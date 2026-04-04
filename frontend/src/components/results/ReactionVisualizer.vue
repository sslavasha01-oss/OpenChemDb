<template>
  <div class="reaction-render" v-html="svgContent || 'Loading...'"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  smiles: String
})

const svgContent = ref('')

const renderReaction = async () => {
  if (!props.smiles) return

  try {
    const ketcher = window.parent?.ketcher || document.querySelector('iframe')?.contentWindow?.ketcher

    if (ketcher) {
      // Попробуйте добавить проверку на наличие '>>'
      // Некоторые версии Ketcher требуют явного указания, что это реакция
      const options = {
        outputFormat: 'svg',
        // Добавляем специфические настройки отображения, если Ketcher их поддерживает
        displayStereoFlags: false,
        ignoreChiralFlag: true
      }

      // Если это реакция, Ketcher должен использовать специфический парсер
      const blob = await ketcher.generateImage(props.smiles, options)
      const text = await blob.text()

      // Маленький хак: если SVG пришел пустой или странный,
      // проверьте, не "проглотил" ли Ketcher символы
      svgContent.value = text
    }
  } catch (e) {
    console.error("Render error:", e)
    svgContent.value = `<small style="color:red">Ошибка отрисовки</small>`
  }
}

onMounted(renderReaction)
watch(() => props.smiles, renderReaction)
</script>

<style scoped>
.reaction-render {
  width: 100%;
  display: flex;
  justify-content: center;
  background: white;
}
:deep(svg) {
  max-width: 100%;
  height: auto;
  max-height: 150px;
}
</style>
