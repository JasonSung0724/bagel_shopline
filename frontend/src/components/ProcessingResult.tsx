'use client';

import { CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react';
import { ProcessingError } from '@/lib/types/order';

interface ProcessingResultProps {
  originalCount: number;
  finalCount: number;
  uniqueOrderCount: number;
  errors: ProcessingError[];
}

export default function ProcessingResult({
  originalCount,
  finalCount,
  uniqueOrderCount,
  errors,
}: ProcessingResultProps) {
  const hasErrors = errors.some(e => e.severity === 'error');
  const hasWarnings = errors.some(e => e.severity === 'warning');

  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-center gap-2 mb-3">
        {hasErrors ? (
          <AlertCircle className="w-5 h-5 text-red-500" />
        ) : hasWarnings ? (
          <AlertTriangle className="w-5 h-5 text-yellow-500" />
        ) : (
          <CheckCircle className="w-5 h-5 text-green-500" />
        )}
        <span className="font-medium text-gray-800">處理完成</span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3">
        <div className="text-center p-2 bg-white rounded border">
          <p className="text-xl font-bold text-blue-600">{originalCount}</p>
          <p className="text-xs text-gray-500">原始資料</p>
        </div>
        <div className="text-center p-2 bg-white rounded border">
          <p className="text-xl font-bold text-green-600">{finalCount}</p>
          <p className="text-xs text-gray-500">最終訂單</p>
        </div>
        <div className="text-center p-2 bg-white rounded border">
          <p className="text-xl font-bold text-purple-600">{uniqueOrderCount}</p>
          <p className="text-xs text-gray-500">不重複訂單</p>
        </div>
      </div>

      {errors.length > 0 && (
        <div className="p-2 bg-yellow-50 rounded border border-yellow-200">
          <p className="font-medium text-yellow-800 text-sm mb-1">
            注意事項 ({errors.length} 項)
          </p>
          <div className="max-h-24 overflow-y-auto space-y-0.5">
            {errors.slice(0, 10).map((error, idx) => (
              <p key={idx} className={`text-xs ${error.severity === 'error' ? 'text-red-600' : 'text-yellow-700'}`}>
                • 訂單 {error.orderId}: {error.message}
              </p>
            ))}
            {errors.length > 10 && (
              <p className="text-xs text-gray-500">... 還有 {errors.length - 10} 項</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
