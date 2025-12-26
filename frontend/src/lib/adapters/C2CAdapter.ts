import { BasePlatformAdapter, isEmptyOrInvalid } from './BasePlatformAdapter';
import { RawOrderData } from '../types/order';
import { ConversionResult, StandardOrderItem } from '../types/standardOrder';
import { ProductInfo } from '@/config/productConfig';
import { PlatformFieldConfig } from '@/config/fieldConfig';
import { formatDateToYYYYMMDD } from '../utils/dateUtils';
import { formatOrderMark, cleanProductName } from '../utils/stringUtils';
import { searchProduct } from '../utils/productMatcher';

const GIVEAWAY_CODE = 'F2500000044';

export class C2CAdapter extends BasePlatformAdapter {
  constructor(productConfig: Record<string, ProductInfo>, fieldConfig?: PlatformFieldConfig) {
    super('C2C', 'c2c', productConfig, fieldConfig);
  }

  convert(data: RawOrderData[]): ConversionResult {
    this.clearErrors();
    const items: StandardOrderItem[] = [];

    for (const row of data) {
      const orderId = this.getOrderId(row);
      const rawProductCode = this.getFieldValue(row, 'product_code');

      if (isEmptyOrInvalid(orderId)) {
        continue;
      }

      // 贈品特殊處理：一個贈品碼可能對應多個商品
      if (rawProductCode === GIVEAWAY_CODE) {
        const giftItems = this.processGiveaway(row);
        items.push(...giftItems);
      } else {
        const item = this.createStandardItem(row);
        if (item) {
          items.push(item);
        }
      }
    }

    return { items, errors: this.errors };
  }

  /**
   * 處理贈品（可能包含多個商品）
   */
  private processGiveaway(row: RawOrderData): StandardOrderItem[] {
    const items: StandardOrderItem[] = [];
    const productStyle = this.getFieldValue(row, 'product_name');
    const cleanedStyle = productStyle.replace('(贈品)-F', '');
    const parts = cleanedStyle.split('+');

    // 贈品通常拆成 2 個商品
    for (let i = 0; i < Math.min(parts.length, 2); i++) {
      const baseItem = this.createStandardItem(row);
      if (baseItem) {
        baseItem.productName = parts[i] ? parts[i].trim() : cleanProductName(productStyle);
        items.push(baseItem);
      }
    }

    return items;
  }

  protected getOrderDate(row: RawOrderData): string {
    const dateValue = this.getFieldValue(row, 'order_date');
    return formatDateToYYYYMMDD(dateValue);
  }

  protected getProductCode(row: RawOrderData): string {
    const rawProductCode = this.getFieldValue(row, 'product_code');
    const productStyle = this.getFieldValue(row, 'product_name');
    const orderId = this.getOrderId(row);

    const code = searchProduct(rawProductCode, 'c2c_code', this.productConfig, productStyle);

    if (!code) {
      this.addError(orderId, '商品編號', `找不到商品: ${rawProductCode} / ${productStyle}`, 'warning');
      return 'ERROR';
    }

    return code;
  }

  protected getProductName(row: RawOrderData): string {
    const productName = this.getFieldValue(row, 'product_name');
    return cleanProductName(productName);
  }

  protected getOrderMark(row: RawOrderData): string {
    const mark = this.getFieldValue(row, 'order_mark');
    return formatOrderMark('減醣市集 X 快電商 C2C BUY', mark, ' | ');
  }
}
