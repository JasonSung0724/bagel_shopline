import { BasePlatformAdapter, safeString } from './BasePlatformAdapter';
import { RawOrderData, StoreAddress } from '../types/order';
import { ConversionResult } from '../types/standardOrder';
import { ProductInfo } from '@/config/productConfig';
import { PlatformFieldConfig, TargetShipping, CompanyName } from '@/config/fieldConfig';
import { formatDateToYYYYMMDD } from '../utils/dateUtils';
import { formatOrderMark } from '../utils/stringUtils';

export class ShoplineAdapter extends BasePlatformAdapter {
  constructor(productConfig: Record<string, ProductInfo>, fieldConfig?: PlatformFieldConfig) {
    super('SHOPLINE', 'shopline', productConfig, fieldConfig);
  }

  convert(data: RawOrderData[], storeAddress?: StoreAddress): ConversionResult {
    this.clearErrors();
    const items = [];

    for (const row of data) {
      // SHOPLINE 特殊處理：商品貨號為空時跳過（通常是組合商品的父項）
      const productCode = this.getFieldValue(row, 'product_code');
      if (!productCode) {
        continue;
      }

      const item = this.createStandardItem(row, storeAddress);
      if (item) {
        items.push(item);
      }
    }

    return { items, errors: this.errors };
  }

  protected getOrderDate(row: RawOrderData): string {
    const dateValue = this.getFieldValue(row, 'order_date');
    return formatDateToYYYYMMDD(dateValue);
  }

  protected getReceiverAddress(row: RawOrderData, storeAddress?: StoreAddress): string {
    const deliveryMethodRaw = this.getFieldValue(row, 'delivery_method');
    const deliveryMethod = deliveryMethodRaw.split('（')[0];
    const storeName = this.getFieldValue(row, 'store_name');
    const fullAddress = this.getFieldValue(row, 'receiver_address');
    const orderId = this.getOrderId(row);

    // 宅配直接使用完整地址
    if (deliveryMethod === TargetShipping.tacat) {
      return fullAddress;
    }

    // 便利商店需要查詢地址
    if (!storeAddress) {
      this.addError(orderId, '地址', `缺少門市地址資料: ${storeName}`, 'error');
      return 'ERROR';
    }

    if (deliveryMethod === TargetShipping.family) {
      const address = storeAddress[CompanyName.family]?.[storeName];
      if (!address || address.includes('ERROR')) {
        this.addError(orderId, '地址', `找不到全家門市: ${storeName}`, 'error');
        return address || 'ERROR';
      }
      return `${storeName} (${address})`;
    }

    if (deliveryMethod === TargetShipping.seven) {
      const address = storeAddress[CompanyName.seven]?.[storeName];
      if (!address || address.includes('ERROR')) {
        this.addError(orderId, '地址', `找不到7-11門市: ${storeName}`, 'error');
        return address || 'ERROR';
      }
      return `(宅轉店)${address}`;
    }

    this.addError(orderId, '配送方式', `未知的配送方式: ${deliveryMethod}`, 'warning');
    return fullAddress || 'ERROR';
  }

  protected getDeliveryMethod(row: RawOrderData): string {
    const deliveryMethodRaw = this.getFieldValue(row, 'delivery_method');
    const deliveryMethod = deliveryMethodRaw.split('（')[0];

    if (deliveryMethod === TargetShipping.tacat) {
      return 'Tcat';
    }
    if (deliveryMethod === TargetShipping.family) {
      return '全家';
    }
    if (deliveryMethod === TargetShipping.seven) {
      return '7-11';
    }
    return 'Tcat'; // 預設
  }

  protected getProductCode(row: RawOrderData): string {
    return this.getFieldValue(row, 'product_code');
  }

  protected getProductName(row: RawOrderData): string {
    const productCode = this.getFieldValue(row, 'product_code');
    const productName = this.getFieldValue(row, 'product_name');
    const option = safeString(row['選項']); // 選項欄位目前沒有加入配置

    // 提取商品標記（如 -459）
    const productCodeParts = productCode.split('-');
    const productMark = productCodeParts.length < 3 ? '' : `-${productCodeParts[2]}`;

    if (productName) {
      return `${productName}${productMark}`;
    }
    return `${option}${productMark}`;
  }

  protected getOrderMark(row: RawOrderData): string {
    const mark = this.getFieldValue(row, 'order_mark');
    return formatOrderMark('減醣市集', mark, '/');
  }

  protected getArrivalTime(row: RawOrderData): string {
    const arrivalTime = this.getFieldValue(row, 'arrival_time');
    if (arrivalTime === '上午到貨') return '1';
    if (arrivalTime === '下午到貨') return '2';
    return '';
  }
}
