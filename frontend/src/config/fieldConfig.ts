/**
 * 平台欄位配置介面
 * 用於定義每個平台的欄位映射關係
 */
export interface PlatformFieldConfig {
  // 識別特徵：這些欄位同時存在時，判定為此平台
  identifyBy: string[];
  // 必要欄位：生成訂單時一定需要的欄位（缺少會阻止生成）
  requiredColumns: string[];
  // 所有預期欄位（用於參考）
  columns: string[];
  // 欄位映射
  order_id: string;
  receiver_name: string;
  receiver_phone: string;
  receiver_address: string;
  product_name: string;
  product_quantity: string;
  // 可選欄位映射
  product_code?: string;
  order_date?: string;
  order_mark?: string;
  delivery_method?: string;
  store_name?: string;
  arrival_time?: string;
}

export type FieldConfigMap = Record<string, PlatformFieldConfig>;

// 預設平台欄位配置（可透過 localStorage 覆蓋）
export const defaultFieldConfig: FieldConfigMap = {
  c2c: {
    // 識別特徵：這些欄位同時存在時，判定為此平台
    identifyBy: ["平台訂單編號", "商品編號", "商品樣式"],
    // 必要欄位：生成訂單時一定需要的欄位（缺少會阻止生成）
    requiredColumns: ["平台訂單編號", "收件者姓名", "收件者手機", "收件者地址", "商品樣式", "小計數量"],
    // 所有預期欄位（用於參考，缺少只會警告）
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
    // 識別特徵：這些欄位同時存在時，判定為此平台
    // 注意：部分 SHOPLINE 匯出可能沒有「商品貨號」，改用更穩定的欄位
    identifyBy: ["訂單號碼", "送貨方式", "收件人電話號碼"],
    // 必要欄位：生成訂單時一定需要的欄位
    requiredColumns: ["訂單號碼", "收件人", "收件人電話號碼", "商品名稱", "數量", "送貨方式"],
    columns: [
      "訂單號碼", "訂單日期", "訂單狀態", "付款狀態", "訂單備註",
      "送貨方式", "送貨狀態", "收件人", "收件人電話號碼", "門市名稱",
      "商品貨號", "商品名稱", "選項", "數量", "完整地址",
      "管理員備註", "出貨備註", "到貨時間"
    ],
    order_id: "訂單號碼",
    receiver_name: "收件人",
    receiver_address: "完整地址",
    product_code: "商品貨號",
    receiver_phone: "收件人電話號碼",
    product_name: "商品名稱",
    delivery_method: "送貨方式",
    store_name: "門市名稱",
    product_quantity: "數量",
    order_date: "訂單日期",
    arrival_time: "到貨時間",
    order_mark: "出貨備註"
  },
  mixx: {
    // 識別特徵：這些欄位同時存在時，判定為此平台
    identifyBy: ["*銷售單號", "品名/規格", "採購數量"],
    // 必要欄位
    requiredColumns: ["*銷售單號", "收件人", "收件人手機", "收件地址", "品名/規格", "採購數量"],
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
    // 識別特徵：這些欄位同時存在時，判定為此平台
    identifyBy: ["團購名稱", "訂單日期(年月日)", "商品代碼"],
    // 必要欄位
    requiredColumns: ["訂單號碼", "收件人姓名", "收件人地址", "收件人電話", "商品名稱", "商品數量"],
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

// 為了向後相容，保留 fieldConfig 別名
export const fieldConfig = defaultFieldConfig;

export type Platform = keyof typeof defaultFieldConfig;

// 運送方式常量
export const TargetShipping = {
  seven: "7-11低溫取貨",
  family: "全家低溫取貨",
  tacat: "低溫宅配"
} as const;

export const CompanyName = {
  seven: "SEVEN",
  family: "FAMILY",
  tacat: "TACAT"
} as const;

// 報告模板欄位
export const reportTemplateColumns = [
  "貨主編號",
  "貨主單號\n(不同客戶端、不同溫層要分單)",
  "訂單\n品項序號",
  "客戶端代號(店號)",
  "訂購日期",
  "預計到貨日",
  "商品編號",
  "商品名稱",
  "倉別",
  "指定效期",
  "指定\n(固定空白)",
  "訂購數量",
  "商品單價",
  "配送方式\nFT : 逢泰配送\nTcat : 黑貓宅配\n全家到府取貨",
  "收貨人姓名",
  "收貨人地址",
  "收貨人聯絡電話",
  "日間聯絡電話",
  "夜間聯絡電話",
  "到貨時段\n1: 13點前\n2: 14~18\n3: 不限時",
  "代收金額\n( 不用代收請填 0 )",
  "訂單 / 宅配單備註",
  "品項備註",
  "抛單日期",
  "訂單通路",
  "指定配送溫層\n001：常溫\n002：冷藏\n003：冷凍"
];
