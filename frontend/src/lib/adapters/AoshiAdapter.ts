import { BasePlatformAdapter } from './BasePlatformAdapter';
import { RawOrderData } from '../types/order';
import { ConversionResult } from '../types/standardOrder';
import { ProductInfo } from '@/config/productConfig';
import { PlatformFieldConfig } from '@/config/fieldConfig';
import { formatDateToYYYYMMDD } from '../utils/dateUtils';
import { formatOrderMark } from '../utils/stringUtils';
import { searchProduct } from '../utils/productMatcher';

export class AoshiAdapter extends BasePlatformAdapter {
  constructor(productConfig: Record<string, ProductInfo>, fieldConfig?: PlatformFieldConfig) {
    super('AOSHI', 'aoshi', productConfig, fieldConfig);
  }

  convert(data: RawOrderData[]): ConversionResult {
    this.clearErrors();
    const items = [];

    for (const row of data) {
      const item = this.createStandardItem(row);
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

  protected getProductCode(row: RawOrderData): string {
    const productName = this.getFieldValue(row, 'product_name');
    const orderId = this.getOrderId(row);

    const code = searchProduct(productName, 'aoshi_name', this.productConfig);

    if (!code) {
      this.addError(orderId, '商品名稱', `找不到商品: ${productName}`, 'warning');
      return 'ERROR';
    }

    return code;
  }

  protected getOrderMark(row: RawOrderData): string {
    const mark = this.getFieldValue(row, 'order_mark');
    return formatOrderMark('減醣市集 X 奧世國際', mark, '/');
  }
}
