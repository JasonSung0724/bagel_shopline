/**
 * 分析無法識別的 Excel 檔案欄位
 */

import * as XLSX from 'xlsx';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 讀取 Excel 檔案
function readExcelFile(filePath) {
  const data = fs.readFileSync(filePath);
  const workbook = XLSX.read(data, { type: 'buffer' });
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  return XLSX.utils.sheet_to_json(worksheet, { raw: false });
}

// 要分析的檔案（無法自動識別的）
const filesToAnalyze = ['1223.xls', '1224.xls', 'A442庫存明細20251225_251225200052.xls'];

console.log('\n' + '='.repeat(70));
console.log('📊 無法識別檔案的欄位分析');
console.log('='.repeat(70));

const testDir = path.join(__dirname, '..', 'testexcel');

for (const file of filesToAnalyze) {
  const filePath = path.join(testDir, file);

  if (!fs.existsSync(filePath)) {
    console.log(`\n❌ 檔案不存在: ${file}`);
    continue;
  }

  console.log(`\n📁 檔案: ${file}`);
  console.log('-'.repeat(50));

  try {
    const data = readExcelFile(filePath);
    const columns = Object.keys(data[0]);

    console.log(`欄位數量: ${columns.length}`);
    console.log('\n所有欄位:');
    columns.forEach((col, i) => {
      const value = data[0][col];
      console.log(`  ${i + 1}. "${col}" = ${value ? String(value).substring(0, 50) : '(空)'}`);
    });
  } catch (error) {
    console.log(`❌ 錯誤: ${error.message}`);
  }
}

console.log('\n' + '='.repeat(70) + '\n');
