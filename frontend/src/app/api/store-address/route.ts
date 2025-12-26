import { NextRequest, NextResponse } from 'next/server';

interface StoreAddressResult {
  SEVEN: Record<string, string>;
  FAMILY: Record<string, string>;
}

/**
 * 查詢 7-11 門市地址
 */
async function fetchSevenAddress(storeName: string): Promise<string> {
  try {
    // 移除 "門市" 後綴
    const inputName = storeName.includes('門市')
      ? storeName.split('門市')[0]
      : storeName;

    const formData = new URLSearchParams({
      commandid: 'SearchStore',
      city: '',
      town: '',
      roadname: '',
      ID: '',
      StoreName: inputName,
      SpecialStore_Kind: '',
      leftMenuChecked: '',
      address: '',
    });

    const response = await fetch('https://emap.pcsc.com.tw/EMapSDK.aspx', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    const xmlText = await response.text();

    // 解析 XML 回應
    // 簡單的 XML 解析（因為 Node.js 沒有內建 DOMParser）
    const addressMatch = xmlText.match(/<POIName>([^<]+)<\/POIName>[\s\S]*?<Address>([^<]+)<\/Address>/g);

    if (addressMatch) {
      for (const match of addressMatch) {
        const nameMatch = match.match(/<POIName>([^<]+)<\/POIName>/);
        const addrMatch = match.match(/<Address>([^<]+)<\/Address>/);

        if (nameMatch && addrMatch && nameMatch[1] === inputName) {
          return addrMatch[1];
        }
      }
    }

    return `ERROR: 無法確認${storeName}正確地址`;
  } catch (error) {
    console.error(`7-11 API error for ${storeName}:`, error);
    return `ERROR: API查詢失敗 - ${storeName}`;
  }
}

/**
 * 查詢全家門市地址
 */
async function fetchFamilyAddress(storeName: string): Promise<string> {
  try {
    const params = new URLSearchParams({
      searchType: 'ShopName',
      type: '',
      kw: storeName,
      fun: 'getByName',
      key: '6F30E8BF706D653965BDE302661D1241F8BE9EBC',
    });

    const response = await fetch(`https://api.map.com.tw/net/familyShop.aspx?${params}`, {
      headers: {
        Referer: 'https://www.family.com.tw/',
      },
    });

    const text = await response.text();

    // 從回應中提取 JSON 陣列
    const startIndex = text.indexOf('[');
    const endIndex = text.lastIndexOf(']') + 1;

    if (startIndex === -1 || endIndex === 0) {
      return `ERROR: 無法確認${storeName}正確地址`;
    }

    const jsonText = text.substring(startIndex, endIndex);
    const data = JSON.parse(jsonText);

    for (const storeInfo of data) {
      if (storeInfo.NAME === storeName) {
        return storeInfo.addr;
      }
    }

    return `ERROR: 無法確認${storeName}正確地址`;
  } catch (error) {
    console.error(`全家 API error for ${storeName}:`, error);
    return `ERROR: API查詢失敗 - ${storeName}`;
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { sevenStores = [], familyStores = [] } = body as {
      sevenStores: string[];
      familyStores: string[];
    };

    const result: StoreAddressResult = {
      SEVEN: {},
      FAMILY: {},
    };

    // 並行查詢所有 7-11 門市
    const sevenPromises = sevenStores.map(async (store: string) => {
      const address = await fetchSevenAddress(store);
      return { store, address };
    });

    // 並行查詢所有全家門市
    const familyPromises = familyStores.map(async (store: string) => {
      const address = await fetchFamilyAddress(store);
      return { store, address };
    });

    // 等待所有查詢完成
    const [sevenResults, familyResults] = await Promise.all([
      Promise.all(sevenPromises),
      Promise.all(familyPromises),
    ]);

    // 整理結果
    for (const { store, address } of sevenResults) {
      result.SEVEN[store] = address;
    }

    for (const { store, address } of familyResults) {
      result.FAMILY[store] = address;
    }

    return NextResponse.json(result);
  } catch (error) {
    console.error('Store address API error:', error);
    return NextResponse.json(
      { error: '查詢門市地址失敗' },
      { status: 500 }
    );
  }
}
