import { BaseProcessor } from './BaseProcessor';
import { OrderRow, RawOrderData, StoreAddress } from '../types/order';
import { ProductInfo } from '@/config/productConfig';
import { formatDateToYYYYMMDD } from '../utils/dateUtils';
import { safeString, formatOrderMark, isEmptyOrInvalid } from '../utils/stringUtils';
import { TargetShipping, CompanyName } from '@/config/fieldConfig';

export class ShoplineProcessor extends BaseProcessor {
  constructor(productConfig?: Record<string, ProductInfo>) {
    super('shopline', productConfig);
  }

  protected getProductCode(row: RawOrderData): string {
    return safeString(row['商品貨號']);
  }

  protected getFormattedDate(row: RawOrderData): string {
    return formatDateToYYYYMMDD(row['訂單日期'] as string);
  }

  protected getOrderMark(row: RawOrderData): string {
    return formatOrderMark('減醣市集', safeString(row['出貨備註']), '/');
  }

  protected getDeliveryMethod(row: RawOrderData): string {
    const deliveryMethod = safeString(row['送貨方式']).split('（')[0];

    if (deliveryMethod === TargetShipping.tacat) {
      return 'Tcat';
    }
    if (deliveryMethod === TargetShipping.family) {
      return '全家';
    }
    if (deliveryMethod === TargetShipping.seven) {
      return '7-11';
    }
    return 'UNKNOWN';
  }

  protected getReceiverAddress(row: RawOrderData, storeAddress?: StoreAddress): string {
    const deliveryMethod = safeString(row['送貨方式']).split('（')[0];
    const storeName = safeString(row['門市名稱']);
    const fullAddress = safeString(row['完整地址']);

    if (deliveryMethod === TargetShipping.tacat) {
      return fullAddress;
    }

    if (!storeAddress) {
      return 'ERROR';
    }

    if (deliveryMethod === TargetShipping.family) {
      const address = storeAddress[CompanyName.family]?.[storeName];
      if (!address) {
        return 'ERROR';
      }
      return `${storeName} (${address})`;
    }

    if (deliveryMethod === TargetShipping.seven) {
      const address = storeAddress[CompanyName.seven]?.[storeName];
      if (!address) {
        return 'ERROR';
      }
      return `(宅轉店)${address}`;
    }

    return 'ERROR';
  }

  public process(data: RawOrderData[], storeAddress?: StoreAddress): OrderRow[] {
    const newRows: OrderRow[] = [];
    let personalOrder: OrderRow[] = [];
    let skippedCount = 0;

    for (const row of data) {
      const currentOrderId = safeString(row['訂單號碼']);
      const productCode = safeString(row['商品貨號']);
      const deliveryMethod = this.getDeliveryMethod(row);
      const address = this.getReceiverAddress(row, storeAddress);

      const productCodeParts = productCode.split('-');
      const productMark = productCodeParts.length < 3 ? '' : `-${productCodeParts[2]}`;

      if (personalOrder.length > 0 &&
          personalOrder[0]['貨主單號\n(不同客戶端、不同溫層要分單)'] !== currentOrderId) {
        newRows.push(this.createBoxRow(personalOrder[0], this.calculateBox(personalOrder)));
        personalOrder = [];
      }

      const newRow = this.createBaseOrderRow(row, deliveryMethod, address);

      const productName = safeString(row['商品名稱']);
      const option = safeString(row['選項']);
      newRow['商品名稱'] = !isEmptyOrInvalid(productName)
        ? `${productName}${productMark}`
        : `${option}${productMark}`;

      if (!isEmptyOrInvalid(productCode)) {
        if (personalOrder.length === 0 ||
            personalOrder[0]['貨主單號\n(不同客戶端、不同溫層要分單)'] === currentOrderId) {
          personalOrder.push(newRow);
        } else {
          personalOrder = [newRow];
        }

        const arrivalTime = safeString(row['到貨時間']);
        if (arrivalTime === '上午到貨' || arrivalTime === '下午到貨') {
          newRow['到貨時段\n1: 13點前\n2: 14~18\n3: 不限時'] = arrivalTime === '上午到貨' ? '1' : '2';
        }

        newRows.push(newRow);
      } else {
        skippedCount++;
      }
    }

    if (personalOrder.length > 0) {
      newRows.push(this.createBoxRow(personalOrder[0], this.calculateBox(personalOrder)));
    }

    if (skippedCount > 0) {
      console.log(`商品貨號空白故扣除筆數：${skippedCount}`);
    }

    return newRows;
  }
}
