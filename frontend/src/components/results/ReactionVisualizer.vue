<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'

const props = defineProps({
  smiles: { type: String, required: true }
})

const canvasRef = ref(null)
const error = ref(false)
const canvasId = `rxn-${Math.random().toString(36).slice(2, 11)}`

const parseSmiles = (sd, smiles) => {
  return new Promise((resolve, reject) => {
    try {
      sd.parse(smiles, (tree) => resolve(tree), (err) => reject(err));
    } catch (e) {
      reject(e);
    }
  });
};

const render = async () => {
  if (!props.smiles) return;

  await nextTick();

  try {
    const sd = window.SmilesDrawer;
    if (!sd || !canvasRef.value) return;

    const mainCtx = canvasRef.value.getContext('2d');

    const cleanSmiles = props.smiles.replace(/[\r\n\s]/g, '');
    const reactionParts = cleanSmiles.split('>>');

    // Если это не реакция
    if (reactionParts.length !== 2) {
      canvasRef.value.width = 400;
      canvasRef.value.height = 150;
      const drawer = new sd.Drawer({ width: 400, height: 150, bondThickness: 1.5, compactDrawing: true });
      const tree = await parseSmiles(sd, cleanSmiles);
      drawer.draw(tree, canvasRef.value, 'light');
      error.value = false;
      return;
    }

    const reactants = reactionParts[0].split('.').filter(p => p.trim());
    const products = reactionParts[1].split('.').filter(p => p.trim());

    // Динамически считаем ширину: чем больше компонентов, тем шире буфер
    const leftWidth = Math.max(300, reactants.length * 180);
    const rightWidth = Math.max(300, products.length * 180);
    const totalWidth = leftWidth + rightWidth + 100; // +100 для стрелки

    canvasRef.value.width = totalWidth;
    canvasRef.value.height = 200;
    mainCtx.clearRect(0, 0, totalWidth, 200);

    // Настройки отрисовки (делаем жирнее и крупнее)
    const getOptions = (w) => ({
      width: w,
      height: 200,
      bondThickness: 1.6,
      bondLength: 25,
      padding: 5, // Минимум пустого места по краям
      compactDrawing: true
    });

    const canvasL = document.createElement('canvas');
    canvasL.width = leftWidth; canvasL.height = 200;
    const drawerL = new sd.Drawer(getOptions(leftWidth));

    const canvasR = document.createElement('canvas');
    canvasR.width = rightWidth; canvasR.height = 200;
    const drawerR = new sd.Drawer(getOptions(rightWidth));

    // Отрисовка
    const treeL = await parseSmiles(sd, reactants.join('.'));
    drawerL.draw(treeL, canvasL, 'light');

    const treeR = await parseSmiles(sd, products.join('.'));
    drawerR.draw(treeR, canvasR, 'light');

    await new Promise(r => setTimeout(r, 20));

    // Сборка на основном холсте
    mainCtx.drawImage(canvasL, 0, 0);

    mainCtx.font = "bold 32px Arial";
    mainCtx.fillStyle = "#333";
    mainCtx.textAlign = "center";
    mainCtx.fillText("→", leftWidth + 50, 110);

    mainCtx.drawImage(canvasR, leftWidth + 100, 0);

    error.value = false;
    console.log("DEBUG: Реакция отрисована с динамической шириной");

  } catch (e) {
    console.error("Render Error:", e);
    error.value = true;
  }
}

onMounted(render);
watch(() => props.smiles, render);
</script>

<template>
  <div class="chem-container">
    <canvas ref="canvasRef" :id="canvasId" class="reaction-canvas"></canvas>
    <div v-if="error" class="smiles-fallback"><code>{{ smiles }}</code></div>
  </div>
</template>

<style scoped>
.chem-container {
  width: 100%;
  display: flex;
  justify-content: center;
  background: white;
  padding: 5px 0;
  overflow-x: auto; /* Если реакция ОЧЕНЬ длинная, появится скролл */
}

.reaction-canvas {
  max-width: 100%;
  height: auto;
  image-rendering: -webkit-optimize-contrast;
}

canvas {
  max-width: 100%;
  height: auto;
}

.smiles-fallback {
  font-size: 10px;
  color: #999;
  white-space: pre-wrap;
  word-break: break-all;
  padding: 10px;
}
</style>