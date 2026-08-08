// src/utils/chemRenderer.js
import OCL from 'openchemlib';

/**
 * Рендерит SMILES в SVG строку с помощью OpenChemLib
 * @param {string} smiles - SMILES строка структуры
 * @param {number} width - Ширина итогового SVG
 * @param {number} height - Высота итогового SVG
 * @returns {string|null} - Строка SVG или null в случае ошибки
 */
export const renderStructure = (smiles, width = 160, height = 120) => {
  if (!smiles) return null;

  if (!OCL || typeof OCL.Molecule === 'undefined') {
    console.error("OCL is not initialized yet");
    return null;
  }

  try {
    const mol = OCL.Molecule.fromSmiles(smiles);

    return mol.toSVG(width, height, null, {
      noMatter: true,            // Вписать в размеры
      suppressChiralText: true,  // Убрать надписи типа (R)/(S) для компактности
      suppressESR: true,         // Убрать технические метки
      fontWeight: 'normal',
    });
  } catch (e) {
    console.error("OCL Render Error for SMILES:", smiles, e);
    return null;
  }
};

/**
 * Расчитывает молярную массу (MW) из SMILES.
 * Использует "неубиваемый" алгоритм поиска метода.
 */
export const calculateMW = (smiles) => {
  if (!smiles || smiles.trim() === "") return '';

  try {
    const mol = OCL.Molecule.fromSmiles(smiles);
    if (mol.getAllAtoms() === 0) return '';

    const formula = mol.getMolecularFormula();

    // 1. Пытаемся вызвать нормальное имя
    if (typeof formula.getRelativeWeight === 'function') {
      return formula.getRelativeWeight().toFixed(2);
    }

    // 2. УМНЫЙ ПОИСК (на случай обфускации xd, wd, td...)
    const proto = Object.getPrototypeOf(formula);
    const methodNames = Object.getOwnPropertyNames(proto);

    for (const name of methodNames) {
      if (name === 'constructor') continue;
      try {
        if (typeof formula[name] === 'function') {
          const result = formula[name]();
          // Молярная масса — это всегда число и всегда > 1
          if (typeof result === 'number' && result > 1) {
            return result.toFixed(2);
          }
        }
      } catch (e) {
        // Пропускаем методы, требующие аргументов
      }
    }
    return '';
  } catch (e) {
    console.error("[MW Calc Error]:", e);
    return '';
  }
};