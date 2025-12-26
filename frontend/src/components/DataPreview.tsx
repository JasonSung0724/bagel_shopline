'use client';

import { RawOrderData } from '@/lib/types/order';

interface DataPreviewProps {
  data: RawOrderData[];
  maxRows?: number;
}

export default function DataPreview({ data, maxRows = 5 }: DataPreviewProps) {
  if (data.length === 0) return null;

  const columns = Object.keys(data[0]).filter(col => !col.startsWith('Unnamed'));
  const previewData = data.slice(0, maxRows);

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
