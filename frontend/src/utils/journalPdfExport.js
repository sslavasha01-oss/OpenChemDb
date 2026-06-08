import { jsPDF } from 'jspdf';
import { robotoBase64 } from './fonts';

const svgToPngInfo = (svgString) => {
  return new Promise((resolve) => {
    if (!svgString) return resolve(null);
    const img = new Image();
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const scale = 2;
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/png');
      const ratio = img.width / img.height;
      URL.revokeObjectURL(url);
      resolve({ dataUrl, ratio });
    };
    img.src = url;
  });
};

export const generateJournalPdf = async (data) => {
  const doc = new jsPDF();
  const fontName = "Roboto";
  doc.addFileToVFS("Roboto-Regular.ttf", robotoBase64);
  doc.addFont("Roboto-Regular.ttf", fontName, "normal");
  doc.setFont(fontName, "normal");

  const margin = 15;
  const pageWidth = doc.internal.pageSize.getWidth();
  let currentY = 20;

  // 1. HEADER
  doc.setFontSize(18);
  doc.text(`Journal Record #${data.external_id || 'Draft'}`, margin, currentY);

  doc.setFontSize(9);
  doc.setTextColor(150);
  // Используем дату добавления или изменения
  const rawDate = data.date_modified || data.date_added || new Date().toISOString();
  const displayDate = new Date(rawDate).toLocaleDateString();
  doc.text(`Date: ${displayDate}`, pageWidth - margin - 35, currentY);

  currentY += 15;
  doc.setTextColor(0);

  // 2. PRODUCT SECTION
  const pInfo = await svgToPngInfo(data.product_preview_svg || data.product_svg);
  if (pInfo) {
    const imgW = 65;
    const imgH = imgW / pInfo.ratio;
    doc.addImage(pInfo.dataUrl, 'PNG', margin, currentY, imgW, imgH);

    doc.setFontSize(10);
    let tableY = currentY + 5;

    // Точный маппинг по вашему JSON
    const pData = [
      ['M.W. (g/mol)', data.product_molar_mass],
      ['Prac. mass (g)', data.product_praktical_mass],
      ['Theor. mass (g)', data.product_theoretical_mass],
      ['Moles', data.product_moles],
      ['Yield (%)', data.product_yield_calc ? `${data.product_yield_calc}%` : '---'],
      ['Eq.', data.product_molar_ekv]
    ];

    pData.forEach(([label, val]) => {
      doc.setTextColor(100);
      doc.text(label, margin + imgW + 10, tableY);
      doc.setTextColor(0);
      doc.text(String(val || '---'), margin + imgW + 45, tableY);
      tableY += 7;
    });

    currentY += Math.max(imgH, 45) + 10;
  }

  // Conditions
  if (data.conditions) {
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text('Conditions:', margin, currentY);
    doc.setTextColor(0);
    doc.text(String(data.conditions), margin + 25, currentY);
    currentY += 15;
  }

  // ... (предыдущий код до начала блока реагентов)

  // 3. REAGENTS SECTION
  doc.setFontSize(14);
  doc.setTextColor(66, 185, 131);
  doc.text('Starting Materials / Reagents', margin, currentY);
  currentY += 10;

  const colW = (pageWidth - (margin * 2)) / 5;
  const reagents = [];
  for(let i=1; i<=5; i++) {
    if(data[`reagent${i}_smiles`]) {
      reagents.push({
        mw: data[`reagent${i}_molar_mass`],
        mass: data[`reagent${i}_mass`],
        moles: data[`reagent${i}_moles`],
        density: data[`reagent${i}_density`],
        conc: data[`reagent${i}_concentration`],
        vol: data[`reagent${i}_volume`],
        ekv: data[`reagent${i}_molar_ekv`],
        svg: data[`reagent${i}_svg`]
      });
    }
  }

  // Определяем фиксированный набор полей для выравнивания
  const fieldList = [
    { label: 'MW', key: 'mw' },
    { label: 'Mass', key: 'mass' },
    { label: 'Mol', key: 'moles' },
    { label: 'Dens', key: 'density' },
    { label: 'Conc', key: 'conc' },
    { label: 'Vol', key: 'vol' },
    { label: 'Eq', key: 'ekv' }
  ];

  let maxImageHeight = 0;
  // Сначала найдем максимальную высоту картинки в ряду, чтобы текст под ними пошел ровно
  const reagentInfos = [];
  for (const r of reagents) {
    const info = await svgToPngInfo(r.svg);
    reagentInfos.push(info);
    if (info) {
      const rH = (colW - 5) / info.ratio;
      if (rH > maxImageHeight) maxImageHeight = rH;
    }
  }

  // Рисуем картинки и данные
  for (let i = 0; i < reagents.length; i++) {
    const r = reagents[i];
    const x = margin + (i * colW);
    const info = reagentInfos[i];

    if (info) {
      const rW = colW - 5;
      const rH = rW / info.ratio;
      doc.addImage(info.dataUrl, 'PNG', x, currentY, rW, rH);
    }

    doc.setFontSize(7.5);
    doc.setTextColor(0);

    // Текст начинаем рисовать на фиксированном расстоянии от начала блока картинок
    // maxImageHeight гарантирует, что даже если картинка маленькая, текст будет на одном уровне с соседями
    let rowY = currentY + maxImageHeight + 5;

    fieldList.forEach((field) => {
      const value = r[field.key];
      // Всегда рисуем строку, даже если значения нет
      doc.text(`${field.label}: ${value || '-'}`, x, rowY);
      rowY += 4; // Строгий шаг 4 единицы для выравнивания по горизонтали
    });
  }

  // Рассчитываем отступ для следующего блока (Method)
  currentY += maxImageHeight + (fieldList.length * 4) + 15;

  // 4. METHOD / PROCEDURE
  if (data.procedure) {
    if (currentY > 230) { doc.addPage(); currentY = 20; doc.setFont(fontName, "normal"); }
    doc.setFontSize(14);
    doc.setTextColor(66, 185, 131);
    doc.text('Method / Procedure', margin, currentY);
    currentY += 8;

    doc.setFontSize(10);
    doc.setTextColor(0);
    doc.setFont(fontName, "normal");

    const splitText = doc.splitTextToSize(data.procedure, pageWidth - (margin * 2));
    doc.text(splitText, margin, currentY);
    currentY += (splitText.length * 5) + 15;
  }

  // 5. REFERENCES
  if (data.references || data.doi) {
    if (currentY > 260) { doc.addPage(); currentY = 20; doc.setFont(fontName, "normal"); }
    doc.setDrawColor(230);
    doc.line(margin, currentY, pageWidth - margin, currentY);
    currentY += 10;
    doc.setFontSize(9);
    if(data.references) doc.text(`References: ${data.references}`, margin, currentY);
    if(data.doi) doc.text(`DOI: ${data.doi}`, margin, currentY + 6);
  }

  doc.save(`Journal_Record_${data.external_id || 'export'}.pdf`);
};