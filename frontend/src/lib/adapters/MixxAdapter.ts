import { BasePlatformAdapter } from './BasePlatformAdapter';
import { RawOrderData } from '../types/order';
import { ConversionResult } from '../types/standardOrder';
import { ProductInfo } from '@/config/productConfig';
import { PlatformFieldConfig } from '@/config/fieldConfig';
import { getCurrentDateYYYYMMDD } from '../utils/dateUtils';
import { formatOrderMark } from '../utils/stringUtils';
import { searchProduct } from '../utils/productMatcher';
import { safeString } from '../utils/stringUtils';

export class MixxAdapter extends BasePlatformAdapter {
  constructor(productConfig: Record<string, ProductInfo>, fieldConfig?: PlatformFieldConfig) {
    super('MIXX', 'mixx', productConfig, fieldConfig);
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

  protected getOrderDate(_row: RawOrderData): string {
    // MIXX 使用當天日期
    return getCurrentDateYYYYMMDD();
  }

  protected getProductCode(row: RawOrderData): string {
    const productName = this.extractProductName(row);
    const orderId = this.getOrderId(row);

    const code = searchProduct(productName, 'mixx_name', this.productConfig);

    if (!code) {
      this.addError(orderId, '商品名稱', `找不到商品: ${productName}`, 'warning');
      return 'ERROR';
    }

    return code;
  }

  /**
   * 提取商品名稱（移除 "減醣市集｜" 前綴）
   */
  private extractProductName(row: RawOrderData): string {
    let productName = this.getFieldValue(row, 'product_name');

    // 移除前綴
    if (productName.includes('｜')) {
      productName = productName.split('｜')[1];
    }

    return productName;
  }

  protected getOrderMark(row: RawOrderData): string {
    // MIXX 的備註欄位沒有在 fieldConfig 中定義，直接讀取
    const mark = safeString(row['備註']);
    return formatOrderMark('減醣市集 X MIXX團購', mark, ' | ');
  }
}
