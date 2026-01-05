'use client';

import { CheckCircle, AlertTriangle, AlertCircle, Clock, Server } from 'lucide-react';
import { ProcessingError } from '@/lib/types/order';

// Platform display names
const PLATFORM_NAMES: Record<string, string> = {
  shopline: 'Shopline',
  mixx: 'Mixx',
  c2c: 'C2C',
  aoshi: 'Aoshi (奧實)',
};

interface ProcessingResultProps {
  originalCount: number;
  finalCount: number;
  uniqueOrderCount: number;
  errors: ProcessingError[];
  timeTaken?: number;
  platformUsed?: string;
}

export default function ProcessingResult({
  originalCount,
  finalCount,
  uniqueOrderCount,
  errors,
  timeTaken,
  platformUsed,
}: ProcessingResultProps) {
  const hasErrors = errors.some(e => e.severity === 'error');
  const hasWarnings = errors.some(e => e.severity === 'warning');
  const errorCount = errors.filter(e => e.severity === 'error').length;
  const warningCount = errors.filter(e => e.severity === 'warning').length;

  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
      {/* Header with status */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {hasErrors ? (
            <AlertCircle className="w-5 h-5 text-red-500" />
          ) : hasWarnings ? (
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
          ) : (
            <CheckCircle className="w-5 h-5 text-green-500" />
          )}
          <span className="font-medium text-gray-800">處理完成</span>
        </div>

        {/* Platform and Time */}
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {platformUsed && (
            <span className="flex items-center gap-1">
              <Server className="w-3 h-3" />
              {PLATFORM_NAMES[platformUsed] || platformUsed}
            </span>
          )}
          {timeTaken !== undefined && timeTaken > 0 && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {timeTaken.toFixed(2)}s
            </span>
          )}
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        <div className="text-center p-2 bg-white rounded border">
          <p className="text-lg font-bold text-blue-600">{originalCount}</p>
          <p className="text-xs text-gray-500">原始行數</p>
        </div>
        <div className="text-center p-2 bg-white rounded border">
          <p className="text-lg font-bold text-purple-600">{uniqueOrderCount}</p>
          <p className="text-xs text-gray-500">訂單數量</p>
        </div>
        <div className="text-center p-2 bg-white rounded border">
          <p className="text-lg font-bold text-green-600">{finalCount}</p>
          <p className="text-xs text-gray-500">輸出行數</p>
        </div>
        <div className="text-center p-2 bg-white rounded border">
          <p className={`text-lg font-bold ${errorCount > 0 ? 'text-red-600' : warningCount > 0 ? 'text-yellow-600' : 'text-gray-400'}`}>
            {errors.length}
          </p>
          <p className="text-xs text-gray-500">錯誤/警告</p>
        </div>
      </div>

      {/* Detailed Errors */}
      {errors.length > 0 && (
        <div className="p-3 bg-yellow-50 rounded border border-yellow-200">
          <p className="font-medium text-yellow-800 text-sm mb-2">
            注意事項
            {errorCount > 0 && <span className="text-red-600 ml-1">({errorCount} 錯誤)</span>}
            {warningCount > 0 && <span className="text-yellow-600 ml-1">({warningCount} 警告)</span>}
          </p>
          <div className="max-h-32 overflow-y-auto space-y-1">
            {errors.slice(0, 20).map((error, idx) => (
              <div
                key={idx}
                className={`text-xs p-1.5 rounded ${
                  error.severity === 'error'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-yellow-100 text-yellow-700'
                }`}
              >
                <span className="font-medium">[{error.severity === 'error' ? 'ERROR' : 'WARNING'}]</span>
                {' '}訂單 {error.orderId}: {error.message}
              </div>
            ))}
            {errors.length > 20 && (
              <p className="text-xs text-gray-500 pt-1">... 還有 {errors.length - 20} 項</p>
            )}
          </div>
        </div>
      )}

      {/* Success message when no errors */}
      {errors.length === 0 && (
        <div className="p-2 bg-green-50 rounded border border-green-200 text-center">
          <p className="text-sm text-green-700">所有訂單處理完成，無錯誤或警告</p>
        </div>
      )}
    </div>
  );
}
