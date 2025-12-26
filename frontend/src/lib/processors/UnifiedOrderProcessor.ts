import { StandardOrderItem } from '../types/standardOrder';
import { OrderRow, ProcessingError } from '../types/order';
import { ProductInfo } from '@/config/productConfig';
import { calculateBoxForOrders, BoxType, OrderItem } from '../utils/boxCalculator';
import { cleanProductName } from '../utils/stringUtils';

/**
 * 統一訂單處理器
 * 負責將標準訂單項目轉換為最終輸出格式
 */
export class UnifiedOrderProcessor {
  private productConfig: Record<string, ProductInfo>;
  private errors: ProcessingError[] = [];

  constructor(productConfig: Record<string, ProductInfo>) {
    this.productConfig = productConfig;
  }

  /**
   * 處理標準訂單項目，輸出最終格式
   */
  process(items: StandardOrderItem[]): OrderRow[] {
    this.errors = [];
    const results: OrderRow[] = [];

    // 按訂單編號分組
    const orderGroups = this.groupByOrderId(items);

    // 處理每個訂單
    orderGroups.forEach((orderItems, orderId) => {
      const orderRows = this.processOrder(orderId, orderItems);
      results.push(...orderRows);
    });

    return results;
  }

  /**
   * 按訂單編號分組
   */
  private groupByOrderId(items: StandardOrderItem[]): Map<string, StandardOrderItem[]> {
    const groups = new Map<string, StandardOrderItem[]>();

    for (const item of items) {
      const existing = groups.get(item.orderId) || [];
      existing.push(item);
      groups.set(item.orderId, existing);
    }

    return groups;
  }

  /**
   * 處理單一訂單（包含多個商品項目）
   */
  private processOrder(orderId: string, items: StandardOrderItem[]): OrderRow[] {
    const rows: OrderRow[] = [];

    // 產生每個商品項目的 OrderRow
    for (const item of items) {
      const row = this.createOrderRow(item);
      rows.push(row);
    }

    // 計算箱型並加入箱子列
    if (rows.length > 0) {
      const boxType = this.calculateBoxForOrder(items);
      const boxRow = this.createBoxRow(rows[0], boxType);
      rows.push(boxRow);

      // 如果箱型是 ERROR，記錄錯誤
      if (boxType.code.includes('ERROR')) {
        this.addError(orderId, '箱型', '訂單商品數量過多，需要拆單');
      }
    }

    return rows;
  }

  /**
   * 將 StandardOrderItem 轉換為 OrderRow
   */
  private createOrderRow(item: StandardOrderItem): OrderRow {
    return {
      '貨主編號': 'A442',
      '貨主單號\n(不同客戶端、不同溫層要分單)': item.orderId,
      '訂單\n品項序號': '',
      '客戶端代號(店號)': item.receiverName,
      '訂購日期': item.orderDate,
      '預計到貨日': '',
      '商品編號': item.productCode,
      '商品名稱': cleanProductName(item.productName),
      '倉別': '',
      '指定效期': '',
      '指定\n(固定空白)': '',
      '訂購數量': String(item.quantity),
      '商品單價': '',
      '配送方式\nFT : 逢泰配送\nTcat : 黑貓宅配\n全家到府取貨': item.deliveryMethod,
      '收貨人姓名': item.receiverName,
      '收貨人地址': item.receiverAddress,
      '收貨人聯絡電話': item.receiverPhone,
      '日間聯絡電話': '',
      '夜間聯絡電話': '',
      '到貨時段\n1: 13點前\n2: 14~18\n3: 不限時': item.arrivalTime,
      '代收金額\n( 不用代收請填 0 )': '',
      '訂單 / 宅配單備註': item.orderMark,
      '品項備註': '',
      '抛單日期': '',
      '訂單通路': '',
      '指定配送溫層\n001：常溫\n002：冷藏\n003：冷凍': '003',
    };
  }

  /**
   * 建立箱子列
   */
  private createBoxRow(templateRow: OrderRow, boxType: BoxType): OrderRow {
    return {
      ...templateRow,
      '商品編號': boxType.code,
      '商品名稱': boxType.name,
      '訂購數量': '1',
      '品項備註': '箱子',
    };
  }

  /**
   * 計算訂單的箱型
   */
  private calculateBoxForOrder(items: StandardOrderItem[]): BoxType {
    const orderItems: OrderItem[] = items.map(item => ({
      productCode: item.productCode,
      quantity: item.quantity,
    }));
    return calculateBoxForOrders(orderItems, this.productConfig);
  }

  /**
   * 記錄錯誤
   */
  private addError(orderId: string, field: string, message: string, severity: 'warning' | 'error' = 'warning'): void {
    this.errors.push({ orderId, field, message, severity });
  }

  /**
   * 取得所有錯誤
   */
  getErrors(): ProcessingError[] {
    return this.errors;
  }
}
