import { OrderRow, RawOrderData, ProcessingError, Platform, StoreAddress } from '../types/order';
import { fieldConfig } from '@/config/fieldConfig';
import { productConfig as defaultProductConfig, ProductInfo } from '@/config/productConfig';
import { safeString, cleanProductName } from '../utils/stringUtils';
import { calculateBoxForOrders, BoxType, OrderItem } from '../utils/boxCalculator';

export abstract class BaseProcessor {
  protected platform: Platform;
  protected config: typeof fieldConfig[Platform];
  protected productConfig: Record<string, ProductInfo>;
  protected errors: ProcessingError[] = [];

  constructor(platform: Platform, productConfig?: Record<string, ProductInfo>) {
    this.platform = platform;
    this.config = fieldConfig[platform];
    this.productConfig = productConfig || defaultProductConfig;
  }

  protected getFieldValue(row: RawOrderData, fieldKey: keyof typeof this.config): string {
    const fieldName = this.config[fieldKey] as string;
    return safeString(row[fieldName]);
  }

  protected abstract getProductCode(row: RawOrderData): string;
  protected abstract getFormattedDate(row: RawOrderData): string;
  protected abstract getOrderMark(row: RawOrderData): string;
  protected abstract getDeliveryMethod(row: RawOrderData, storeAddress?: StoreAddress): string;
  protected abstract getReceiverAddress(row: RawOrderData, storeAddress?: StoreAddress): string;

  protected createBaseOrderRow(row: RawOrderData, deliveryMethod: string, address: string): OrderRow {
    return {
      '貨主編號': 'A442',
      '貨主單號\n(不同客戶端、不同溫層要分單)': this.getFieldValue(row, 'order_id'),
      '訂單\n品項序號': '',
      '客戶端代號(店號)': this.getFieldValue(row, 'receiver_name'),
      '訂購日期': this.getFormattedDate(row),
      '預計到貨日': '',
      '商品編號': this.getProductCode(row),
      '商品名稱': cleanProductName(this.getFieldValue(row, 'product_name')),
      '倉別': '',
      '指定效期': '',
      '指定\n(固定空白)': '',
      '訂購數量': this.getFieldValue(row, 'product_quantity'),
      '商品單價': '',
      '配送方式\nFT : 逢泰配送\nTcat : 黑貓宅配\n全家到府取貨': deliveryMethod,
      '收貨人姓名': this.getFieldValue(row, 'receiver_name'),
      '收貨人地址': address,
      '收貨人聯絡電話': this.getFieldValue(row, 'receiver_phone'),
      '日間聯絡電話': '',
      '夜間聯絡電話': '',
      '到貨時段\n1: 13點前\n2: 14~18\n3: 不限時': '',
      '代收金額\n( 不用代收請填 0 )': '',
      '訂單 / 宅配單備註': this.getOrderMark(row),
      '品項備註': '',
      '抛單日期': '',
      '訂單通路': '',
      '指定配送溫層\n001：常溫\n002：冷藏\n003：冷凍': '003',
    };
  }

  protected createBoxRow(templateRow: OrderRow, boxType: BoxType): OrderRow {
    return {
      ...templateRow,
      '商品編號': boxType.code,
      '商品名稱': boxType.name,
      '訂購數量': '1',
      '品項備註': '箱子',
    };
  }

  protected calculateBox(orders: OrderRow[]): BoxType {
    const orderItems: OrderItem[] = orders.map(order => ({
      productCode: order['商品編號'],
      quantity: parseInt(order['訂購數量']) || 0,
    }));
    return calculateBoxForOrders(orderItems, this.productConfig);
  }

  protected addError(orderId: string, field: string, message: string, severity: 'warning' | 'error' = 'warning'): void {
    this.errors.push({ orderId, field, message, severity });
  }

  public getErrors(): ProcessingError[] {
    return this.errors;
  }

  public abstract process(data: RawOrderData[], storeAddress?: StoreAddress): OrderRow[];
}
