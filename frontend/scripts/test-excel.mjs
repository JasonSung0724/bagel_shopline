/**
 * Excel 處理測試腳本
 * 用於驗證各廠商 Excel 檔案的讀取、平台識別和訂單生成
 */

import * as XLSX from 'xlsx';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 從 fieldConfig 複製的配置
const fieldConfig = {
  c2c: {
    identifyBy: ["平台訂單編號", "商品編號", "商品樣式"],
    columns: [
      "填單日期", "建立時間", "平台訂單編號", "交易序號", "收件者姓名",
      "收件者手機", "收件者地址", "商品編號", "商品樣式", "小計數量",
      "交易金額", "出貨備註", "廠商發貨日期", "配送編號-已出貨", "狀態回填-已送達"
    ],
    order_id: "平台訂單編號",
    receiver_name: "收件者姓名",
    product_code: "商品編號",
    product_name: "商品樣式",
    receiver_address: "收件者地址",
    receiver_phone: "收件者手機",
    product_quantity: "小計數量",
    order_mark: "出貨備註",
    order_date: "建立時間"
  },
  shopline: {
    identifyBy: ["訂單號碼", "送貨方式", "收件人電話號碼"],
    columns: [
      "訂單號碼", "訂單日期", "訂單狀態", "付款狀態", "訂單備註",
      "送貨方式", "送貨狀態", "收件人", "收件人電話號碼", "門市名稱",
      "商品貨號", "商品名稱", "選項", "數量", "完整地址",
      "管理員備註", "出貨備註", "到貨時間"
    ],
    order_id: "訂單號碼",
    receiver_name: "收件人",
    product_code: "商品貨號",
    receiver_phone: "收件人電話號碼",
    product_name: "商品名稱",
    delivery_method: "送貨方式",
    store_name: "門市名稱",
    product_quantity: "數量",
    order_date: "訂單日期"
  },
  mixx: {
    identifyBy: ["*銷售單號", "品名/規格", "採購數量"],
    columns: [
      "*銷售單號", "收件人", "收件人手機", "收件地址", "品名/規格",
      "採購數量", "單價", "進價小計", "銷售單價", "銷售小計",
      "運費", "備註", "配送物流", "寄件查詢編號"
    ],
    order_id: "*銷售單號",
    receiver_name: "收件人",
    receiver_address: "收件地址",
    receiver_phone: "收件人手機",
    product_name: "品名/規格",
    product_quantity: "採購數量"
  },
  aoshi: {
    identifyBy: ["團購名稱", "訂單日期(年月日)", "商品代碼"],
    columns: [
      "團購名稱", "訂單號碼", "訂單日期(年月日)", "訂單狀態", "付款方式",
      "付款狀態", "訂單總計(含運費)", "已付金額", "運費(總金額)", "訂購人姓名",
      "收件人姓名", "收件人地址", "收件人電話", "收件人Email", "客戶備註",
      "商品代碼", "國際條碼", "商品名稱", "商品數量", "商品金額小計"
    ],
    order_id: "訂單號碼",
    receiver_name: "收件人姓名",
    receiver_address: "收件人地址",
    receiver_phone: "收件人電話",
    product_code: "商品代碼",
    product_name: "商品名稱",
    product_quantity: "商品數量",
    order_date: "訂單日期(年月日)",
    order_mark: "客戶備註"
  }
};

const platformNames = {
  c2c: '快電商 C2C',
  shopline: 'SHOPLINE',
  mixx: 'MIXX 團購',
  aoshi: '奧世國際',
};

// 讀取 Excel 檔案
function readExcelFile(filePath) {
  const data = fs.readFileSync(filePath);
  const workbook = XLSX.read(data, { type: 'buffer' });
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  return XLSX.utils.sheet_to_json(worksheet, { raw: false });
}

// 平台識別
function detectPlatform(data) {
  if (data.length === 0) {
    return { detected: null, confidence: 0, matchedColumns: [], allPlatformScores: [] };
  }

  const actualColumns = Object.keys(data[0]).filter(col => !col.startsWith('Unnamed'));
  const platforms = Object.keys(fieldConfig);

  const scores = platforms.map(platform => {
    const config = fieldConfig[platform];
    const identifyColumns = config.identifyBy;
    const matched = identifyColumns.filter(col => actualColumns.includes(col));
    const score = (matched.length / identifyColumns.length) * 100;

    return { platform, score, matched };
  });

  scores.sort((a, b) => b.score - a.score);
  const best = scores[0];
  const isFullMatch = best.score === 100;

  return {
    detected: isFullMatch ? best.platform : null,
    confidence: best.score,
    matchedColumns: best.matched,
    allPlatformScores: scores,
  };
}

// 欄位驗證
function validateColumns(data, platform) {
  if (data.length === 0) {
    return { isValid: false, missingColumns: ['檔案為空'], extraColumns: [] };
  }

  const expectedColumns = [...fieldConfig[platform].columns];
  const actualColumns = Object.keys(data[0]).filter(col => !col.startsWith('Unnamed'));

  const missingColumns = expectedColumns.filter(col => !actualColumns.includes(col));
  const extraColumns = actualColumns.filter(col => !expectedColumns.includes(col));

  return {
    isValid: missingColumns.length === 0,
    missingColumns,
    extraColumns,
  };
}

// 顯示資料範例
function showSampleData(data, platform) {
  const config = fieldConfig[platform];
  const sample = data[0];

  console.log('\n  📋 資料欄位範例:');

  const fieldsToShow = ['order_id', 'receiver_name', 'product_code', 'product_name', 'product_quantity'];
  fieldsToShow.forEach(fieldKey => {
    if (config[fieldKey]) {
      const fieldName = config[fieldKey];
      const value = sample[fieldName] || '(空)';
      console.log(`     ${fieldKey}: "${fieldName}" = ${value}`);
    }
  });
}

// 主測試函數
async function runTests() {
  const testDir = path.join(__dirname, '..', 'testexcel');
  const files = fs.readdirSync(testDir).filter(f => f.endsWith('.xlsx') || f.endsWith('.xls'));

  console.log('\n' + '='.repeat(70));
  console.log('📊 Excel 處理測試報告');
  console.log('='.repeat(70));
  console.log(`\n測試檔案數量: ${files.length}\n`);

  const results = [];

  for (const file of files) {
    const filePath = path.join(testDir, file);
    console.log('-'.repeat(70));
    console.log(`\n📁 檔案: ${file}`);

    try {
      // 1. 讀取檔案
      const data = readExcelFile(filePath);
      console.log(`   ✓ 讀取成功，共 ${data.length} 筆資料`);

      // 2. 自動識別平台
      const detection = detectPlatform(data);

      if (detection.detected) {
        console.log(`   ✓ 自動識別: ${platformNames[detection.detected]} (${detection.confidence}%)`);
        console.log(`     匹配欄位: ${detection.matchedColumns.join(', ')}`);
      } else {
        console.log(`   ⚠ 無法自動識別 (最高匹配: ${detection.allPlatformScores[0]?.platform} ${detection.confidence}%)`);
        console.log('     各平台分數:');
        detection.allPlatformScores.forEach(s => {
          console.log(`       - ${platformNames[s.platform]}: ${s.score.toFixed(0)}% (${s.matched.join(', ')})`);
        });
      }

      // 3. 欄位驗證 (使用識別到的平台或最佳匹配)
      const platformToUse = detection.detected || detection.allPlatformScores[0]?.platform;
      if (platformToUse) {
        const validation = validateColumns(data, platformToUse);

        if (validation.isValid) {
          console.log(`   ✓ 欄位驗證通過`);
        } else {
          console.log(`   ⚠ 欄位驗證警告:`);
          if (validation.missingColumns.length > 0) {
            console.log(`     缺少欄位: ${validation.missingColumns.join(', ')}`);
          }
        }

        // 4. 顯示資料範例
        showSampleData(data, platformToUse);

        // 5. 檢查關鍵資料
        const config = fieldConfig[platformToUse];
        const orderId = data[0][config.order_id];
        const productName = data[0][config.product_name];

        if (!orderId) {
          console.log(`   ❌ 錯誤: 訂單編號為空`);
        }
        if (!productName) {
          console.log(`   ❌ 錯誤: 商品名稱為空`);
        }
      }

      results.push({
        file,
        success: true,
        platform: detection.detected,
        rows: data.length,
        confidence: detection.confidence
      });

    } catch (error) {
      console.log(`   ❌ 錯誤: ${error.message}`);
      results.push({
        file,
        success: false,
        error: error.message
      });
    }
  }

  // 總結
  console.log('\n' + '='.repeat(70));
  console.log('📈 測試總結');
  console.log('='.repeat(70));

  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  const autoDetected = results.filter(r => r.platform);

  console.log(`\n總檔案數: ${results.length}`);
  console.log(`成功讀取: ${successful.length}`);
  console.log(`讀取失敗: ${failed.length}`);
  console.log(`自動識別成功: ${autoDetected.length}`);

  console.log('\n按平台分類:');
  const byPlatform = {};
  autoDetected.forEach(r => {
    byPlatform[r.platform] = (byPlatform[r.platform] || 0) + 1;
  });
  Object.entries(byPlatform).forEach(([platform, count]) => {
    console.log(`  - ${platformNames[platform]}: ${count} 個檔案`);
  });

  if (failed.length > 0) {
    console.log('\n❌ 失敗的檔案:');
    failed.forEach(r => {
      console.log(`  - ${r.file}: ${r.error}`);
    });
  }

  console.log('\n' + '='.repeat(70) + '\n');
}

runTests().catch(console.error);
