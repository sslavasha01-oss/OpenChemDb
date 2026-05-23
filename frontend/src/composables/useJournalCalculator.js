import { ref, watch } from 'vue'

export function useJournalCalculator() {
  // Исходная структура пустой записи
  const createEmptyEntry = () => {
    const entry = {
      user_id: null,
      product_smiles: '',
      product_svg: '',
      product_preview_svg: '',
      product_molar_mass: null,
      product_moles: null,
      product_molar_ekv: 1.0,
      product_theoretical_mass: null,
      product_praktical_mass: null,
      product_yield_calc: null,
      procedure: '',
    }

    for (let i = 1; i <= 5; i++) {
      entry[`reagent${i}_smiles`] = ''
      entry[`reagent${i}_svg`] = ''
      entry[`reagent${i}_molar_mass`] = null
      entry[`reagent${i}_mass`] = null
      entry[`reagent${i}_moles`] = null
      entry[`reagent${i}_density`] = null
      entry[`reagent${i}_concentration`] = 1.0
      entry[`reagent${i}_volume`] = null
      entry[`reagent${i}_molar_ekv`] = i === 1 ? 1.0 : null
    }
    return entry
  }

  const journalData = ref(createEmptyEntry())

  // Функция автоматического пересчета стехиометрии
  const calculateJournal = () => {
    const d = journalData.value
    if (!d) return

    // --- 1. РАСЧЕТ РЕАГЕНТА 1 (Лимитирующий) ---
    const r1_mw = parseFloat(d.reagent1_molar_mass)
    const r1_mass = parseFloat(d.reagent1_mass)
    const r1_dens = parseFloat(d.reagent1_density)
    const r1_conc = parseFloat(d.reagent1_concentration) || 1.0

    if (r1_mass > 0 && r1_mw > 0) {
      d.reagent1_moles = (r1_mass / r1_mw).toFixed(4)
    } else {
      d.reagent1_moles = null
    }

    if (r1_mass > 0 && r1_dens > 0) {
      d.reagent1_volume = (r1_mass / (r1_dens * r1_conc)).toFixed(2)
    }

    // --- 2. БАЗОВЫЕ МОЛИ ---
    const r1_moles = parseFloat(d.reagent1_moles)
    const r1_ekv = parseFloat(d.reagent1_molar_ekv) || 1.0

    if (r1_moles > 0 && r1_ekv > 0) {
      const baseMoles = r1_moles / r1_ekv

      // --- 3. РАСЧЕТ РЕАГЕНТОВ 2-5 ---
      for (let i = 2; i <= 5; i++) {
        const ekv = parseFloat(d[`reagent${i}_molar_ekv`])
        const mw = parseFloat(d[`reagent${i}_molar_mass`])
        const dens = parseFloat(d[`reagent${i}_density`])
        const conc = parseFloat(d[`reagent${i}_concentration`]) || 1.0

        if (ekv > 0) {
          d[`reagent${i}_moles`] = (baseMoles * ekv).toFixed(4)
          if (mw > 0) {
            const massNetto = parseFloat(d[`reagent${i}_moles`]) * mw
            d[`reagent${i}_mass`] = massNetto.toFixed(3)
            if (dens > 0) {
              d[`reagent${i}_volume`] = (massNetto / (dens * conc)).toFixed(2)
            }
          }
        } else {
          d[`reagent${i}_moles`] = null
          d[`reagent${i}_mass`] = null
          d[`reagent${i}_volume`] = null
        }
      }

      // --- 4. РАСЧЕТ ПРОДУКТА (Теоретическая масса) ---
      const prod_mw = parseFloat(d.product_molar_mass)
      const prod_ekv = parseFloat(d.product_molar_ekv) || 1.0

      if (prod_mw > 0) {
        d.product_theoretical_mass = (baseMoles * prod_ekv * prod_mw).toFixed(3)
      } else {
        d.product_theoretical_mass = null
      }
    } else {
      d.product_theoretical_mass = null
    }

    // --- 5. РАСЧЕТ ПРОДУКТА (Практические моли и Выход) ---
    const prod_mw_final = parseFloat(d.product_molar_mass)
    const prac_mass = parseFloat(d.product_praktical_mass)
    const theor_mass = parseFloat(d.product_theoretical_mass)

    if (prac_mass > 0 && prod_mw_final > 0) {
      d.product_moles = (prac_mass / prod_mw_final).toFixed(4)
    } else {
      d.product_moles = null
    }

    if (prac_mass > 0 && theor_mass > 0) {
      d.product_yield_calc = ((prac_mass / theor_mass) * 100).toFixed(1)
    } else {
      d.product_yield_calc = null
    }
  }

  // Очистка полей до числовых типов перед отправкой на бэкенд
  const getCleanDataForApi = () => {
    const source = journalData.value
    const cleanData = {}
    const excludeKeys = ['product_svg', 'product_preview_svg', 'id', 'user_id', 'date_added', 'date_modified']

    Object.keys(source).forEach(key => {
      if (excludeKeys.includes(key) || key.endsWith('_svg')) return

      const val = source[key]
      const isNumeric = key.includes('mass') || key.includes('moles') ||
                        key.includes('ekv') || key.includes('density') ||
                        key.includes('concentration') || key.includes('volume') ||
                        key.includes('yield_calc')

      if (isNumeric) {
        cleanData[key] = (val === '' || val === null || val === undefined) ? null : parseFloat(val)
      } else {
        cleanData[key] = (val === '') ? null : val
      }
    })
    return cleanData
  }

  // Следим за изменениями реактивов
  watch(journalData, () => {
    calculateJournal()
  }, { deep: true })

  return {
    journalData,
    createEmptyEntry,
    calculateJournal,
    getCleanDataForApi
  }
}