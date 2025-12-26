import { BasePlatformAdapter } from './BasePlatformAdapter';
import { ShoplineAdapter } from './ShoplineAdapter';
import { C2CAdapter } from './C2CAdapter';
import { MixxAdapter } from './MixxAdapter';
import { AoshiAdapter } from './AoshiAdapter';
import { Platform, PlatformFieldConfig } from '@/config/fieldConfig';
import { ProductInfo } from '@/config/productConfig';

export { BasePlatformAdapter } from './BasePlatformAdapter';
export { ShoplineAdapter } from './ShoplineAdapter';
export { C2CAdapter } from './C2CAdapter';
export { MixxAdapter } from './MixxAdapter';
export { AoshiAdapter } from './AoshiAdapter';

/**
 * 建立平台轉換器
 * @param platform 平台類型
 * @param productConfig 商品配置
 * @param fieldConfig 可選的欄位配置（用於覆蓋預設值）
 */
export function createAdapter(
  platform: Platform,
  productConfig: Record<string, ProductInfo>,
  fieldConfig?: PlatformFieldConfig
): BasePlatformAdapter {
  switch (platform) {
    case 'shopline':
      return new ShoplineAdapter(productConfig, fieldConfig);
    case 'c2c':
      return new C2CAdapter(productConfig, fieldConfig);
    case 'mixx':
      return new MixxAdapter(productConfig, fieldConfig);
    case 'aoshi':
      return new AoshiAdapter(productConfig, fieldConfig);
    default:
      throw new Error(`未知的平台類型: ${platform}`);
  }
}
