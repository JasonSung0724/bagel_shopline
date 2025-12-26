import { BaseProcessor } from './BaseProcessor';
import { OrderRow, RawOrderData } from '../types/order';
import { ProductInfo } from '@/config/productConfig';
import { formatDateToYYYYMMDD } from '../utils/dateUtils';
import { safeString, formatOrderMark, isEmptyOrInvalid, cleanProductName } from '../utils/stringUtils';
import { searchProduct } from '../utils/productMatcher';

const GIVEAWAY_CODE = 'F2500000044';

export class C2CProcessor extends BaseProcessor {
  constructor(productConfig?: Record<string, ProductInfo>) {
    super('c2c', productConfig);
  }

  protected getProductCode(row: RawOrderData): string {
    const productCode = safeString(row['商品編號']);
    const productStyle = safeString(row['商品樣式']);
    const code = searchProduct(productCode, 'c2c_code', this.productConfig, productStyle);
    if (!code) {
      this.addError(safeString(row['平台訂單編號']), '商品編號', `找不到商品: ${productCode}`);
    }
    return code || 'ERROR';
  }

  protected getFormattedDate(row: RawOrderData): string {
    return formatDateToYYYYMMDD(row['建立時間'] as string);
  }

  protected getOrderMark(row: RawOrderData): string {
    return formatOrderMark('減醣市集 X 快電商 C2C BUY', safeString(row['出貨備註']), ' | ');
  }

  protected getDeliveryMethod(_row: RawOrderData): string {
    return 'Tcat';
  }

  protected getReceiverAddress(row: RawOrderData): string {
    return safeString(row['收件者地址']);
  }

  public process(data: RawOrderData[]): OrderRow[] {
    const newRows: OrderRow[] = [];
    let personalOrder: OrderRow[] = [];

    for (const row of data) {
      const currentOrderId = safeString(row['平台訂單編號']);
      const productCode = safeString(row['商品編號']);

      if (productCode === GIVEAWAY_CODE) {
        const productStyle = safeString(row['商品樣式']);
        const cleanedStyle = productStyle.replace('(贈品)-F', '');
        const parts = cleanedStyle.split('+');

        for (let i = 0; i < 2; i++) {
          if (personalOrder.length > 0 &&
              personalOrder[0]['貨主單號\n(不同客戶端、不同溫層要分單)'] !== currentOrderId) {
            newRows.push(this.createBoxRow(personalOrder[0], this.calculateBox(personalOrder)));
            personalOrder = [];
          }

          const newRow = this.createBaseOrderRow(row, this.getDeliveryMethod(row), this.getReceiverAddress(row));
          newRow['商品名稱'] = parts[i] ? parts[i].trim() : cleanProductName(productStyle);

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
      } else {
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
    }

    if (personalOrder.length > 0) {
      newRows.push(this.createBoxRow(personalOrder[0], this.calculateBox(personalOrder)));
    }

    return newRows;
  }
}
