/**
 * 標準化訂單格式
 * 所有平台的訂單都會先轉換成這個格式，再進行後續處理
 */

/**
 * 標準訂單項目（單一商品行）
 */
export interface StandardOrderItem {
  /** 訂單編號 */
  orderId: string;
  /** 訂購日期 (YYYYMMDD 格式) */
  orderDate: string;
  /** 收件人姓名 */
  receiverName: string;
  /** 收件人電話 */
  receiverPhone: string;
  /** 收件人地址 */
  receiverAddress: string;
  /** 配送方式: 'Tcat' | '7-11' | '全家' */
  deliveryMethod: string;
  /** 商品編號 (用於 productConfig 查詢) */
  productCode: string;
  /** 商品名稱 (顯示用) */
  productName: string;
  /** 訂購數量 */
  quantity: number;
  /** 訂單備註 */
  orderMark: string;
  /** 到貨時段: '1' (上午) | '2' (下午) | '' (不限) */
  arrivalTime: string;
  /** 來源平台 */
  sourcePlatform: string;
}

/**
 * 標準訂單（按訂單編號分組後的完整訂單）
 */
export interface StandardOrder {
  /** 訂單編號 */
  orderId: string;
  /** 訂購日期 */
  orderDate: string;
  /** 收件人姓名 */
  receiverName: string;
  /** 收件人電話 */
  receiverPhone: string;
  /** 收件人地址 */
  receiverAddress: string;
  /** 配送方式 */
  deliveryMethod: string;
  /** 訂單備註 */
  orderMark: string;
  /** 到貨時段 */
  arrivalTime: string;
  /** 來源平台 */
  sourcePlatform: string;
  /** 訂單商品列表 */
  items: StandardOrderItem[];
  /** 箱型 (計算後填入) */
  boxType?: {
    code: string;
    name: string;
  };
}

/**
 * 轉換錯誤
 */
export interface ConversionError {
  orderId: string;
  field: string;
  message: string;
  severity: 'warning' | 'error';
}

/**
 * 轉換結果
 */
export interface ConversionResult {
  items: StandardOrderItem[];
  errors: ConversionError[];
}
