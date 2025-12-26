import { BaseProcessor } from './BaseProcessor';
import { MixxProcessor } from './MixxProcessor';
import { AoshiProcessor } from './AoshiProcessor';
import { C2CProcessor } from './C2CProcessor';
import { ShoplineProcessor } from './ShoplineProcessor';
import { Platform } from '../types/order';
import { ProductInfo } from '@/config/productConfig';

export { BaseProcessor, MixxProcessor, AoshiProcessor, C2CProcessor, ShoplineProcessor };

export function createProcessor(platform: Platform, productConfig?: Record<string, ProductInfo>): BaseProcessor {
  switch (platform) {
    case 'mixx':
      return new MixxProcessor(productConfig);
    case 'aoshi':
      return new AoshiProcessor(productConfig);
    case 'c2c':
      return new C2CProcessor(productConfig);
    case 'shopline':
      return new ShoplineProcessor(productConfig);
    default:
      throw new Error(`Unsupported platform: ${platform}`);
  }
}
