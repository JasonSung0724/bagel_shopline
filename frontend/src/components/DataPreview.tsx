'use client';

import { useMemo } from 'react';
import { RawOrderData, Platform } from '@/lib/types/order';
import { TargetShipping } from '@/config/fieldConfig';

interface DataPreviewProps {
  data: RawOrderData[];
  maxRows?: number;
  platform?: Platform;
}

interface ConvenienceStoreStats {
  sevenCount: number;
  sevenNames: string[];
  familyCount: number;
  familyNames: string[];
}

function analyzeConvenienceStoreOrders(data: RawOrderData[]): ConvenienceStoreStats {
  const sevenOrders = new Map<string, string>();
  const familyOrders = new Map<string, string>();

  data.forEach(row => {
    const deliveryMethod = String(row['送貨方式'] || '');
    const orderId = String(row['訂單號碼'] || '');
    const receiverName = String(row['收件人'] || '');

    if (deliveryMethod.startsWith(TargetShipping.seven)) {
      sevenOrders.set(orderId, receiverName);
    } else if (deliveryMethod.startsWith(TargetShipping.family)) {
      familyOrders.set(orderId, receiverName);
    }
  });

  return {
    sevenCount: sevenOrders.size,
    sevenNames: [...new Set(sevenOrders.values())],
    familyCount: familyOrders.size,
    familyNames: [...new Set(familyOrders.values())],
  };
}

export default function DataPreview({ data, maxRows = 5, platform }: DataPreviewProps) {
  if (data.length === 0) return null;

  const columns = Object.keys(data[0]).filter(col => !col.startsWith('Unnamed'));
  const previewData = data.slice(0, maxRows);

  const convenienceStats = useMemo(() => {
    if (platform !== 'shopline') return null;
    if (!data.some(row => '送貨方式' in row)) return null;
    return analyzeConvenienceStoreOrders(data);
  }, [data, platform]);

  return (
    <div className="card overflow-hidden">
      <div className="p-4 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">資料預覽</h3>
          <span className="text-sm text-gray-500">
            共 {data.length} 筆資料
          </span>
        </div>
      </div>

      {convenienceStats && (convenienceStats.sevenCount > 0 || convenienceStats.familyCount > 0) && (
        <div className="p-4 border-b border-gray-100 bg-blue-50">
          <h4 className="font-semibold text-gray-700 mb-3">超商取貨統計</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {convenienceStats.sevenCount > 0 && (
              <div className="bg-white rounded-lg p-3 border border-orange-200">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-orange-500 font-bold text-lg">7-11</span>
                  <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full text-sm font-medium">
                    {convenienceStats.sevenCount} 筆
                  </span>
                </div>
                <div className="text-sm text-gray-600">
                  <span className="font-medium">收件人：</span>
                  <span className="text-gray-800">
                    {convenienceStats.sevenNames.join('、')}
                  </span>
                </div>
              </div>
            )}
            {convenienceStats.familyCount > 0 && (
              <div className="bg-white rounded-lg p-3 border border-green-200">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-green-600 font-bold text-lg">全家</span>
                  <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded-full text-sm font-medium">
                    {convenienceStats.familyCount} 筆
                  </span>
                </div>
                <div className="text-sm text-gray-600">
                  <span className="font-medium">收件人：</span>
                  <span className="text-gray-800">
                    {convenienceStats.familyNames.join('、')}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              {columns.slice(0, 8).map((col) => (
                <th key={col} className="whitespace-nowrap">
                  {col.length > 15 ? col.substring(0, 15) + '...' : col}
                </th>
              ))}
              {columns.length > 8 && (
                <th className="text-gray-400">+{columns.length - 8} 欄</th>
              )}
            </tr>
          </thead>
          <tbody>
            {previewData.map((row, idx) => (
              <tr key={idx}>
                {columns.slice(0, 8).map((col) => (
                  <td key={col} className="whitespace-nowrap max-w-[200px] truncate">
                    {String(row[col] || '')}
                  </td>
                ))}
                {columns.length > 8 && <td className="text-gray-400">...</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.length > maxRows && (
        <div className="p-3 text-center text-sm text-gray-500 border-t border-gray-100">
          顯示前 {maxRows} 筆，共 {data.length} 筆
        </div>
      )}
    </div>
  );
}
