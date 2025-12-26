import { BaseProcessor } from './BaseProcessor';
import { OrderRow, RawOrderData } from '../types/order';
import { ProductInfo } from '@/config/productConfig';
import { getCurrentDateYYYYMMDD } from '../utils/dateUtils';
import { safeString, formatOrderMark, isEmptyOrInvalid } from '../utils/stringUtils';
import { searchProduct } from '../utils/productMatcher';

export class MixxProcessor extends BaseProcessor {
  constructor(productConfig?: Record<string, ProductInfo>) {
    super('mixx', productConfig);
  }

  protected getProductCode(row: RawOrderData): string {
    const productNameRaw = safeString(row['品名/規格']);
    const productName = productNameRaw.includes('｜')
      ? productNameRaw.split('｜')[1]
      : productNameRaw;
    const code = searchProduct(productName, 'mixx_name', this.productConfig);
    if (!code) {
      this.addError(safeString(row['*銷售單號']), '商品編號', `找不到商品: ${productName}`);
    }
    return code || 'ERROR';
  }

  protected getFormattedDate(_row: RawOrderData): string {
    return getCurrentDateYYYYMMDD();
  }

  protected getOrderMark(row: RawOrderData): string {
    return formatOrderMark('減醣市集', safeString(row['備註']), '/');
  }

  protected getDeliveryMethod(_row: RawOrderData): string {
    return 'Tcat';
  }

  protected getReceiverAddress(row: RawOrderData): string {
    return safeString(row['收件地址']);
  }

  public process(data: RawOrderData[]): OrderRow[] {
    const newRows: OrderRow[] = [];
    let personalOrder: OrderRow[] = [];

    for (const row of data) {
      const currentOrderId = safeString(row['*銷售單號']);

      if (personalOrder.length > 0 &&
          personalOrder[0]['貨主單號\n(不同客戶端、不同溫層要分單)'] !== currentOrderId) {
        newRows.push(this.createBoxRow(personalOrder[0], this.calculateBox(personalOrder)));
        personalOrder = [];
      }

      const newRow = this.createBaseOrderRow(row, this.getDeliveryMethod(row), this.getReceiverAddress(row));

      if (!isEmptyOrInvalid(currentOrderId)) {
        if (personalOrder.length === 0 ||
            personalOrder[0]['貨主單號\n(不同客戶端、不同溫層要分單)'] === currentOrderId) {
          personalOrder.push(newRow);
        } else {
          personalOrder = [newRow];
        }
        newRows.push(newRow);
      }
    }

    if (personalOrder.length > 0) {
      newRows.push(this.createBoxRow(personalOrder[0], this.calculateBox(personalOrder)));
    }

    return newRows;
  }
}
