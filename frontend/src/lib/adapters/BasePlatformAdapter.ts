import { RawOrderData, StoreAddress } from '../types/order';
import { StandardOrderItem, ConversionError, ConversionResult } from '../types/standardOrder';
import { ProductInfo } from '@/config/productConfig';
import { PlatformFieldConfig, defaultFieldConfig, Platform } from '@/config/fieldConfig';
import { safeString, isEmptyOrInvalid } from '../utils/stringUtils';

/**
 * 平台轉換器基類
 * 負責將各平台的原始資料轉換為標準訂單格式
 * 支援彈性欄位配置，廠商 Excel 欄位變更時可透過配置調整
 */
export abstract class BasePlatformAdapter {
  protected platformName: string;
  protected platformKey: Platform;
  protected productConfig: Record<string, ProductInfo>;
  protected fieldConfig: PlatformFieldConfig;
  protected errors: ConversionError[] = [];

  constructor(
    platformName: string,
    platformKey: Platform,
    productConfig: Record<string, ProductInfo>,
    fieldConfig?: PlatformFieldConfig
  ) {
    this.platformName = platformName;
    this.platformKey = platformKey;
    this.productConfig = productConfig;
    // 允許傳入自訂欄位配置，否則使用預設配置
    this.fieldConfig = fieldConfig || defaultFieldConfig[platformKey];
  }

  /**
   * 從 row 中根據欄位配置取得值
   * @param row 原始資料列
   * @param fieldKey 欄位鍵名（如 order_id, receiver_name）
   */
  protected getFieldValue(row: RawOrderData, fieldKey: keyof PlatformFieldConfig): string {
    const fieldName = this.fieldConfig[fieldKey] as string | undefined;
    if (!fieldName) return '';
    return safeString(row[fieldName]);
  }

  /**
   * 將原始資料轉換為標準訂單項目
   */
  abstract convert(data: RawOrderData[], storeAddress?: StoreAddress): ConversionResult;

  /**
   * 取得訂單編號
   */
  protected getOrderId(row: RawOrderData): string {
    return this.getFieldValue(row, 'order_id');
  }

  /**
   * 取得訂購日期 (返回 YYYYMMDD 格式)
   * 子類應覆寫此方法以處理特定日期格式
   */
  protected abstract getOrderDate(row: RawOrderData): string;

  /**
   * 取得收件人姓名
   */
  protected getReceiverName(row: RawOrderData): string {
    return this.getFieldValue(row, 'receiver_name');
  }

  /**
   * 取得收件人電話
   */
  protected getReceiverPhone(row: RawOrderData): string {
    return this.getFieldValue(row, 'receiver_phone');
  }

  /**
   * 取得收件人地址
   * 子類可覆寫以處理便利商店地址等特殊情況
   */
  protected getReceiverAddress(row: RawOrderData, _storeAddress?: StoreAddress): string {
    return this.getFieldValue(row, 'receiver_address');
  }

  /**
   * 取得配送方式
   * 子類可覆寫以處理平台特定的配送方式邏輯
   */
  protected getDeliveryMethod(_row: RawOrderData): string {
    return 'Tcat'; // 預設黑貓宅配
  }

  /**
   * 取得商品編號 (用於 productConfig 查詢)
   * 子類應覆寫此方法以處理商品查詢邏輯
   */
  protected abstract getProductCode(row: RawOrderData): string;

  /**
   * 取得商品名稱
   */
  protected getProductName(row: RawOrderData): string {
    return this.getFieldValue(row, 'product_name');
  }

  /**
   * 取得訂購數量
   */
  protected getQuantity(row: RawOrderData): number {
    const qty = this.getFieldValue(row, 'product_quantity');
    return parseInt(qty) || 0;
  }

  /**
   * 取得訂單備註
   */
  protected getOrderMark(row: RawOrderData): string {
    return this.getFieldValue(row, 'order_mark');
  }

  /**
   * 取得到貨時段
   */
  protected getArrivalTime(_row: RawOrderData): string {
    return ''; // 預設不限時段，子類可覆寫
  }

  /**
   * 記錄錯誤
   */
  protected addError(orderId: string, field: string, message: string, severity: 'warning' | 'error' = 'warning'): void {
    this.errors.push({ orderId, field, message, severity });
  }

  /**
   * 取得所有錯誤
   */
  public getErrors(): ConversionError[] {
    return this.errors;
  }

  /**
   * 清除錯誤
   */
  protected clearErrors(): void {
    this.errors = [];
  }

  /**
   * 驗證必要欄位是否有值
   */
  protected validateRequiredFields(row: RawOrderData, orderId: string): boolean {
    const requiredFields: (keyof PlatformFieldConfig)[] = [
      'order_id',
      'receiver_name',
      'receiver_phone',
      'receiver_address',
      'product_name',
      'product_quantity'
    ];

    let isValid = true;
    for (const field of requiredFields) {
      const value = this.getFieldValue(row, field);
      if (isEmptyOrInvalid(value)) {
        const fieldName = this.fieldConfig[field] as string || field;
        this.addError(orderId, fieldName, `必要欄位 "${fieldName}" 為空`, 'error');
        isValid = false;
      }
    }
    return isValid;
  }

  /**
   * 建立標準訂單項目
   */
  protected createStandardItem(row: RawOrderData, storeAddress?: StoreAddress): StandardOrderItem | null {
    const orderId = this.getOrderId(row);

    if (isEmptyOrInvalid(orderId)) {
      return null;
    }

    return {
      orderId,
      orderDate: this.getOrderDate(row),
      receiverName: this.getReceiverName(row),
      receiverPhone: this.getReceiverPhone(row),
      receiverAddress: this.getReceiverAddress(row, storeAddress),
      deliveryMethod: this.getDeliveryMethod(row),
      productCode: this.getProductCode(row),
      productName: this.getProductName(row),
      quantity: this.getQuantity(row),
      orderMark: this.getOrderMark(row),
      arrivalTime: this.getArrivalTime(row),
      sourcePlatform: this.platformName,
    };
  }
}

// 匯出工具函數
export { safeString, isEmptyOrInvalid };
