/**
 * 訂單生成端對端測試
 * 測試完整的訂單處理流程，包含自動識別、資料轉換、錯誤收集
 */

import * as XLSX from 'xlsx';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ==================== 配置區 ====================

const fieldConfig = {
  c2c: {
    identifyBy: ["平台訂單編號", "商品編號", "商品樣式"],
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
    order_id: "*銷售單號",
    receiver_name: "收件人",
    receiver_address: "收件地址",
    receiver_phone: "收件人手機",
    product_name: "品名/規格",
    product_quantity: "採購數量"
  }
};

// 簡化的產品配置用於測試
const productConfig = {
  "bagel101-1PK-999": { qty: 14, mixx_name: ["減醣貝果14天體驗組 (14入)"], c2c_code: ["L2503F00048"], c2c_name: ["減醣市集 減醣貝果14天體驗組-F"] },
  "bagel007-2EA": { qty: 2, mixx_name: ["法式AOP極致奶油貝果 (2入)", "減醣市集｜法式AOP極致奶油貝果 (2入)"], c2c_code: ["L2503F00172"], c2c_name: ["鹹香奶油-2入組"] },
  "bagel001-2EA": { qty: 2, mixx_name: ["低糖草莓乳酪貝果 (2入)"], c2c_code: ["L2503F00172"], c2c_name: ["草莓乳酪-2入組"] },
  "bagel002-2EA": { qty: 2, mixx_name: ["日式香醇芝麻乳酪貝果 (2入)"], c2c_code: ["L2503F00172"], c2c_name: ["芝麻乳酪-2入組"] },
  "bagel005-2EA": { qty: 2, mixx_name: ["經典輕盈原味貝果 (2入)"], c2c_code: ["L2503F00172"], c2c_name: ["經典原味-2入組"] },
};

const platformNames = {
  c2c: '快電商 C2C',
  shopline: 'SHOPLINE',
  mixx: 'MIXX 團購',
};

// ==================== 工具函數 ====================

function readExcelFile(filePath) {
  const data = fs.readFileSync(filePath);
  const workbook = XLSX.read(data, { type: 'buffer' });
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  return XLSX.utils.sheet_to_json(worksheet, { raw: false });
}

function detectPlatform(data) {
  if (data.length === 0) return { detected: null };

  const actualColumns = Object.keys(data[0]);
  const platforms = Object.keys(fieldConfig);

  for (const platform of platforms) {
    const identifyColumns = fieldConfig[platform].identifyBy;
    const allMatch = identifyColumns.every(col => actualColumns.includes(col));
    if (allMatch) {
      return { detected: platform };
    }
  }
  return { detected: null };
}

function safeString(val) {
  if (val === null || val === undefined || val === '' || Number.isNaN(val)) {
    return '';
  }
  return String(val).trim();
}

// 產品搜尋 (簡化版)
function searchProduct(searchValue, searchType, productConfig, extraName = '') {
  const normalizedSearch = safeString(searchValue)
    .replace(/\u3000/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  for (const [code, info] of Object.entries(productConfig)) {
    if (searchType === 'c2c_code') {
      // 先比對 c2c_name
      if (extraName) {
        const normalizedExtra = safeString(extraName)
          .replace(/\u3000/g, ' ')
          .replace(/\s+/g, ' ')
          .replace(/-F$/, '')
          .trim();

        for (const name of info.c2c_name || []) {
          if (normalizedExtra.includes(name) || name.includes(normalizedExtra)) {
            return code;
          }
        }
      }
      // 再比對 c2c_code
      for (const codeItem of info.c2c_code || []) {
        if (normalizedSearch.includes(codeItem)) {
          return code;
        }
      }
    } else if (searchType === 'mixx_name') {
      for (const name of info.mixx_name || []) {
        const normalizedName = name.replace(/\u3000/g, ' ').replace(/\s+/g, ' ').trim();
        // 處理 "減醣市集｜" 前綴
        const cleanSearch = normalizedSearch.includes('｜')
          ? normalizedSearch.split('｜')[1]
          : normalizedSearch;

        if (cleanSearch === normalizedName || normalizedName.includes(cleanSearch)) {
          return code;
        }
      }
    }
  }
  return null;
}

// ==================== 處理器 ====================

class BaseProcessor {
  constructor(platform) {
    this.platform = platform;
    this.config = fieldConfig[platform];
    this.errors = [];
  }

  getFieldValue(row, fieldKey) {
    const fieldName = this.config[fieldKey];
    return safeString(row[fieldName]);
  }

  addError(orderId, field, message) {
    this.errors.push({ orderId, field, message });
  }

  getErrors() {
    return this.errors;
  }
}

class C2CProcessor extends BaseProcessor {
  constructor() {
    super('c2c');
  }

  getProductCode(row) {
    const productCode = safeString(row['商品編號']);
    const productStyle = safeString(row['商品樣式']);
    const code = searchProduct(productCode, 'c2c_code', productConfig, productStyle);
    if (!code) {
      this.addError(safeString(row['平台訂單編號']), '商品編號', `找不到商品: ${productCode} / ${productStyle}`);
    }
    return code || 'ERROR';
  }

  process(data) {
    const results = [];
    for (const row of data) {
      const orderId = this.getFieldValue(row, 'order_id');
      const productCode = this.getProductCode(row);
      const quantity = this.getFieldValue(row, 'product_quantity');

      results.push({
        orderId,
        productCode,
        productName: this.getFieldValue(row, 'product_name'),
        quantity,
        receiverName: this.getFieldValue(row, 'receiver_name'),
        receiverPhone: this.getFieldValue(row, 'receiver_phone'),
        receiverAddress: this.getFieldValue(row, 'receiver_address'),
        deliveryMethod: 'Tcat',
      });
    }
    return results;
  }
}

class ShoplineProcessor extends BaseProcessor {
  constructor() {
    super('shopline');
  }

  getDeliveryMethod(row) {
    const method = safeString(row['送貨方式']);
    if (method.includes('7-11')) return '7-11';
    if (method.includes('全家')) return '全家';
    return 'Tcat';
  }

  process(data) {
    const results = [];
    for (const row of data) {
      const orderId = this.getFieldValue(row, 'order_id');
      const productCode = this.getFieldValue(row, 'product_code');
      const productName = this.getFieldValue(row, 'product_name');

      // SHOPLINE 的商品貨號可能為空
      if (!productCode) {
        this.addError(orderId, '商品貨號', `商品貨號為空: ${productName}`);
      }

      results.push({
        orderId,
        productCode: productCode || 'ERROR-無貨號',
        productName,
        quantity: this.getFieldValue(row, 'product_quantity'),
        receiverName: this.getFieldValue(row, 'receiver_name'),
        receiverPhone: this.getFieldValue(row, 'receiver_phone'),
        receiverAddress: safeString(row['完整地址']),
        deliveryMethod: this.getDeliveryMethod(row),
      });
    }
    return results;
  }
}

class MixxProcessor extends BaseProcessor {
  constructor() {
    super('mixx');
  }

  getProductCode(row) {
    let productName = safeString(row['品名/規格']);
    // 處理 "減醣市集｜" 前綴
    if (productName.includes('｜')) {
      productName = productName.split('｜')[1];
    }
    const code = searchProduct(productName, 'mixx_name', productConfig);
    if (!code) {
      this.addError(safeString(row['*銷售單號']), '品名/規格', `找不到商品: ${productName}`);
    }
    return code || 'ERROR';
  }

  process(data) {
    const results = [];
    for (const row of data) {
      const orderId = this.getFieldValue(row, 'order_id');
      const productCode = this.getProductCode(row);

      results.push({
        orderId,
        productCode,
        productName: this.getFieldValue(row, 'product_name'),
        quantity: this.getFieldValue(row, 'product_quantity'),
        receiverName: this.getFieldValue(row, 'receiver_name'),
        receiverPhone: this.getFieldValue(row, 'receiver_phone'),
        receiverAddress: this.getFieldValue(row, 'receiver_address'),
        deliveryMethod: 'Tcat',
      });
    }
    return results;
  }
}

function createProcessor(platform) {
  switch (platform) {
    case 'c2c': return new C2CProcessor();
    case 'shopline': return new ShoplineProcessor();
    case 'mixx': return new MixxProcessor();
    default: throw new Error(`Unknown platform: ${platform}`);
  }
}

// ==================== 主測試函數 ====================

async function runTests() {
  const testDir = path.join(__dirname, '..', 'testexcel');
  const files = fs.readdirSync(testDir).filter(f =>
    (f.endsWith('.xlsx') || f.endsWith('.xls')) &&
    !f.includes('庫存明細')  // 排除庫存報表
  );

  console.log('\n' + '='.repeat(70));
  console.log('📊 訂單生成端對端測試報告');
  console.log('='.repeat(70));

  let totalOrders = 0;
  let totalErrors = 0;
  let successFiles = 0;

  for (const file of files) {
    const filePath = path.join(testDir, file);
    console.log(`\n${'─'.repeat(70)}`);
    console.log(`📁 ${file}`);

    try {
      // 1. 讀取檔案
      const data = readExcelFile(filePath);

      // 2. 識別平台
      const { detected: platform } = detectPlatform(data);
      if (!platform) {
        console.log('   ⚠ 無法識別平台，跳過');
        continue;
      }
      console.log(`   平台: ${platformNames[platform]}`);
      console.log(`   原始資料: ${data.length} 筆`);

      // 3. 處理訂單
      const processor = createProcessor(platform);
      const results = processor.process(data);
      const errors = processor.getErrors();

      // 4. 統計
      const uniqueOrders = new Set(results.map(r => r.orderId)).size;
      totalOrders += uniqueOrders;
      totalErrors += errors.length;

      console.log(`   處理結果: ${results.length} 筆 (${uniqueOrders} 個不重複訂單)`);

      // 5. 顯示範例資料
      if (results.length > 0) {
        console.log('\n   📋 處理後資料範例 (前 3 筆):');
        results.slice(0, 3).forEach((r, i) => {
          console.log(`      ${i + 1}. 訂單: ${r.orderId}`);
          console.log(`         商品碼: ${r.productCode}`);
          console.log(`         商品名: ${r.productName.substring(0, 30)}...`);
          console.log(`         數量: ${r.quantity}, 配送: ${r.deliveryMethod}`);
        });
      }

      // 6. 顯示錯誤
      if (errors.length > 0) {
        console.log(`\n   ⚠ 錯誤 (${errors.length} 項):`);
        errors.slice(0, 5).forEach(e => {
          console.log(`      • ${e.orderId}: ${e.message}`);
        });
        if (errors.length > 5) {
          console.log(`      ... 還有 ${errors.length - 5} 項錯誤`);
        }
      } else {
        console.log('\n   ✓ 無錯誤');
        successFiles++;
      }

    } catch (error) {
      console.log(`   ❌ 處理失敗: ${error.message}`);
    }
  }

  // 總結
  console.log('\n' + '='.repeat(70));
  console.log('📈 測試總結');
  console.log('='.repeat(70));
  console.log(`\n處理檔案: ${files.length} 個`);
  console.log(`無錯誤檔案: ${successFiles} 個`);
  console.log(`總訂單數: ${totalOrders} 筆`);
  console.log(`總錯誤數: ${totalErrors} 項`);

  if (totalErrors > 0) {
    console.log('\n💡 建議: 檢查 productConfig 中是否有缺少的商品配置');
  }

  console.log('\n' + '='.repeat(70) + '\n');
}

runTests().catch(console.error);
