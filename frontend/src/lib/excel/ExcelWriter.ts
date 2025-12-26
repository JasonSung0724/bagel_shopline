import ExcelJS from 'exceljs';
import { OrderRow } from '../types/order';

async function loadTemplate(): Promise<ExcelJS.Workbook> {
  const response = await fetch('/report_template.xlsx');
  const arrayBuffer = await response.arrayBuffer();
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.load(arrayBuffer);
  return workbook;
}

export async function generateAndDownloadReport(rows: OrderRow[], fileName: string): Promise<void> {
  const workbook = await loadTemplate();
  const worksheet = workbook.worksheets[0];

  const templateColumns = worksheet.getRow(1).values as string[];

  // Start writing from row 2 (after header)
  let currentRowNumber = 2;

  for (const row of rows) {
    const excelRow = worksheet.getRow(currentRowNumber);

    for (let i = 1; i < templateColumns.length; i++) {
      const col = templateColumns[i];
      const cell = excelRow.getCell(i);
      const value = (row as Record<string, string>)[col] || '';
      cell.value = value;

      const isError = value.includes('ERROR') || value.toLowerCase() === 'nan';

      cell.font = {
        name: '微軟正黑體',
        size: 11,
        bold: isError,
        color: isError ? { argb: 'FFFF0000' } : { argb: 'FF000000' },
      };
      cell.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true };
    }

    // Calculate row height based on line breaks
    const lineCount = Math.max(
      ...Object.values(row).map(v => (String(v || '').match(/\n/g) || []).length + 1)
    );
    excelRow.height = Math.max(20, lineCount * 15);

    excelRow.commit();
    currentRowNumber++;
  }

  // Adjust column widths
  for (let i = 1; i < templateColumns.length; i++) {
    const column = worksheet.getColumn(i);
    let maxLength = column.width || 10;

    column.eachCell({ includeEmpty: false }, (cell, rowNumber) => {
      if (rowNumber > 1 && rowNumber <= currentRowNumber) {
        const cellLength = String(cell.value || '').length;
        if (cellLength > maxLength) {
          maxLength = Math.min(cellLength + 2, 50);
        }
      }
    });

    column.width = maxLength;
  }

  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName.endsWith('.xlsx') ? fileName : `${fileName}.xlsx`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
