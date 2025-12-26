import { productConfig, ProductInfo } from '@/config/productConfig';

export interface BoxType {
  code: string;
  name: string;
}

export const BOX_TYPES = {
  SMALL: { code: 'box60-EA', name: '60公分紙箱' },
  LARGE: { code: 'box90-EA', name: '90公分紙箱' },
  ERROR: { code: 'ERROR-需拆單', name: 'ERROR-需拆單' }
} as const;

const BOX_CAPACITY = {
  SMALL: 14,
  LARGE: 47
} as const;

export interface OrderItem {
  productCode: string;
  quantity: number;
}

export function calculateItemUnits(productCode: string, quantity: number, config: Record<string, ProductInfo> = productConfig): number {
  const productInfo = config[productCode];
  if (!productInfo) {
    console.warn(`未知商品編號: ${productCode}`);
    return 0;
  }
  return productInfo.qty * quantity;
}

export function calculateTotalUnits(orders: OrderItem[], config: Record<string, ProductInfo> = productConfig): number {
  return orders.reduce((total, order) => {
    if (!order.productCode || order.productCode === 'nan') return total;
    return total + calculateItemUnits(order.productCode, order.quantity, config);
  }, 0);
}

export function determineBoxType(totalUnits: number): BoxType {
  if (totalUnits <= BOX_CAPACITY.SMALL) {
    return BOX_TYPES.SMALL;
  }
  if (totalUnits <= BOX_CAPACITY.LARGE) {
    return BOX_TYPES.LARGE;
  }
  return BOX_TYPES.ERROR;
}

export function calculateBoxForOrders(orders: OrderItem[], config: Record<string, ProductInfo> = productConfig): BoxType {
  const totalUnits = calculateTotalUnits(orders, config);
  return determineBoxType(totalUnits);
}
