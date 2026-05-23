import { ref } from 'vue'

export function useJournalKetcher(globalKetcherFrame, journalData) {
  const isKetcherInjected = ref(false)
  const isKetcherReady = ref(false)

  // Генератор SVG строки из SMILES строки через Кетчер
  const fastGenerateSVG = async (ketcher, smiles) => {
    try {
      await ketcher.setMolecule(smiles)
      const blob = await ketcher.generateImage(smiles, { outputFormat: 'svg' })
      return await blob.text()
    } catch (e) {
      console.error("SVG Gen Error:", e)
      return ''
    }
  }

  // Запуск фоновой перерисовки всех карточек структур на основе данных
  const triggerKetcherRedraw = (record) => {
    const waitForKetcherAndDraw = async () => {
      const ketcher = globalKetcherFrame.value?.contentWindow?.ketcher
      if (ketcher && typeof ketcher.setMolecule === 'function') {
        try {
          if (record.product_smiles) {
            journalData.value.product_preview_svg = await fastGenerateSVG(ketcher, record.product_smiles)
          }
          for (let i = 1; i <= 5; i++) {
            const smiles = record[`reagent${i}_smiles`]
            if (smiles) {
              journalData.value[`reagent${i}_svg`] = await fastGenerateSVG(ketcher, smiles)
            }
          }
        } catch (err) {
          console.error("Ошибка фоновой отрисовки Ketcher:", err)
        }
      } else {
        setTimeout(waitForKetcherAndDraw, 200)
      }
    }
    waitForKetcherAndDraw()
  }

  return {
    isKetcherInjected,
    isKetcherReady,
    triggerKetcherRedraw
  }
}