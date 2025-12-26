import { ProductInfo } from '@/config/productConfig';

function normalizeString(str: string): string {
  return str
    .replace(/\u3000/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function searchProduct(
  searchValue: string,
  searchType: 'mixx_name' | 'c2c_code' | 'aoshi_name',
  productConfig: Record<string, ProductInfo>,
  c2cName?: string
): string | null {
  const normalizedSearch = normalizeString(searchValue);

  for (const [productCode, productInfo] of Object.entries(productConfig)) {
    if (searchType === 'mixx_name') {
      for (const name of productInfo.mixx_name) {
        if (normalizeString(name) === normalizedSearch) {
          return productCode;
        }
      }
    }
    if (searchType === 'c2c_code' && c2cName) {
      const normalizedC2cName = normalizeString(c2cName);
      for (const name of productInfo.c2c_name) {
        if (normalizeString(name) === normalizedC2cName) {
          const c2cCodeList = productInfo.c2c_code;
          for (const code of c2cCodeList) {
            if (searchValue.includes(code)) {
              return productCode;
            }
          }
        }
      }
    }
    if (searchType === 'aoshi_name' && productInfo.aoshi_name) {
      for (const name of productInfo.aoshi_name) {
        if (normalizeString(name) === normalizedSearch) {
          return productCode;
        }
      }
    }
  }
  return null;
}
