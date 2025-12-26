import { StoreAddress, RawOrderData } from '../types/order';
import { TargetShipping } from '@/config/fieldConfig';
import { safeString } from '../utils/stringUtils';

/**
 * 從訂單資料中提取需要查詢的便利商店門市名稱
 */
export function extractStoreNames(data: RawOrderData[]): {
  sevenStores: string[];
  familyStores: string[];
} {
  const sevenStores = new Set<string>();
  const familyStores = new Set<string>();

  for (const row of data) {
    const deliveryMethod = safeString(row['送貨方式']).split('（')[0];
    const storeName = safeString(row['門市名稱']);

    if (!storeName) continue;

    if (deliveryMethod === TargetShipping.seven) {
      sevenStores.add(storeName);
    } else if (deliveryMethod === TargetShipping.family) {
      familyStores.add(storeName);
    }
  }

  return {
    sevenStores: Array.from(sevenStores),
    familyStores: Array.from(familyStores),
  };
}

/**
 * 呼叫 API 查詢便利商店地址
 */
export async function fetchStoreAddresses(
  sevenStores: string[],
  familyStores: string[]
): Promise<StoreAddress> {
  // 如果沒有需要查詢的門市，直接返回空物件
  if (sevenStores.length === 0 && familyStores.length === 0) {
    return { SEVEN: {}, FAMILY: {} };
  }

  try {
    const response = await fetch('/api/store-address', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sevenStores, familyStores }),
    });

    if (!response.ok) {
      throw new Error('API 回應錯誤');
    }

    const result = await response.json();
    return result as StoreAddress;
  } catch (error) {
    console.error('查詢門市地址失敗:', error);
    // 返回錯誤訊息作為地址
    const errorResult: StoreAddress = { SEVEN: {}, FAMILY: {} };

    for (const store of sevenStores) {
      errorResult.SEVEN[store] = `ERROR: 查詢失敗 - ${store}`;
    }
    for (const store of familyStores) {
      errorResult.FAMILY[store] = `ERROR: 查詢失敗 - ${store}`;
    }

    return errorResult;
  }
}
