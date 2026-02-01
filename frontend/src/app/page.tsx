'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { FileSpreadsheet, Loader2, Settings } from 'lucide-react';
import FileUploader from '@/components/FileUploader';
import PlatformSelector from '@/components/PlatformSelector';
import DataPreview from '@/components/DataPreview';
import ProcessingResult from '@/components/ProcessingResult';
import SystemSettings from '@/components/SystemSettings';
import { Platform, RawOrderData, ProcessingError } from '@/lib/types/order';
import { readExcelFile, detectPlatform, getPlatformDisplayName, PlatformDetectionResult } from '@/lib/excel/ExcelReader';

export default function Home() {
  const [platform, setPlatform] = useState<Platform>('shopline');
  const [autoDetectEnabled, setAutoDetectEnabled] = useState(true);
  const [detectionResult, setDetectionResult] = useState<PlatformDetectionResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [rawData, setRawData] = useState<RawOrderData[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [outputFileName, setOutputFileName] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const [processingResult, setProcessingResult] = useState<{
    originalCount: number;
    finalCount: number;
    uniqueOrderCount: number;
    errors: ProcessingError[];
    timeTaken: number;
    platformUsed: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 用於錯誤訊息滾動的 ref
  const errorRef = useRef<HTMLDivElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  // 當有錯誤時自動滾動到錯誤訊息
  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [error]);

  // 當處理結果有錯誤時自動滾動
  useEffect(() => {
    if (processingResult?.errors && processingResult.errors.length > 0 && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [processingResult]);

  const handleFileSelect = useCallback(async (file: File) => {
    setSelectedFile(file);
    setError(null);
    setProcessingResult(null);
    setDetectionResult(null);

    try {
      const data = await readExcelFile(file);
      setRawData(data);
      setOutputFileName(file.name.replace(/\.(xlsx|xls)$/, '_output'));

      // 自動識別平台
      if (autoDetectEnabled) {
        const detection = detectPlatform(data);
        setDetectionResult(detection);

        if (detection.detected) {
          setPlatform(detection.detected);
        } else if (detection.allPlatformScores[0]) {
          // 無法完全識別時，自動選擇最高匹配的平台
          setPlatform(detection.allPlatformScores[0].platform);
        }
      }

      console.log(`原始資料數量: ${data.length}\n`);
    } catch (err) {
      setError('檔案讀取失敗，請確認檔案格式正確');
    }
  }, [autoDetectEnabled]);

  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setRawData([]);
    setProcessingResult(null);
    setError(null);
    setOutputFileName('');
    setDetectionResult(null);
  }, []);

  const handleProcess = useCallback(async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('platform', platform);

      const response = await fetch('/api/report/generate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || '處理失敗');
      }

      // 處理檔案下載
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const safeFileName = outputFileName || `${selectedFile.name.replace(/\.(xlsx|xls)$/, '')}_output.xlsx`;
      a.download = safeFileName.endsWith('.xlsx') ? safeFileName : `${safeFileName}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      // Read stats from headers
      const originalRows = parseInt(response.headers.get('X-Report-Original-Rows') || '0');
      const totalOrders = parseInt(response.headers.get('X-Report-Total-Orders') || '0');
      const totalRows = parseInt(response.headers.get('X-Report-Row-Count') || '0');
      const timeTaken = parseFloat(response.headers.get('X-Report-Time-Taken') || '0');
      const platformUsed = response.headers.get('X-Report-Platform') || platform;

      // Parse detailed errors from header (base64 encoded)
      let detailedErrors: ProcessingError[] = [];
      try {
        const errorsBase64 = response.headers.get('X-Report-Errors');
        if (errorsBase64) {
          // Decode base64 to JSON string
          const errorsJson = atob(errorsBase64);
          const parsed = JSON.parse(errorsJson);
          detailedErrors = parsed.map((e: { order_id: string; field: string; message: string; severity: string }) => ({
            orderId: e.order_id,
            field: e.field,
            message: e.message,
            severity: e.severity as 'warning' | 'error'
          }));
        }
      } catch (e) {
        console.error('Failed to parse errors:', e);
      }

      setProcessingResult({
        originalCount: originalRows,
        finalCount: totalRows,
        uniqueOrderCount: totalOrders,
        errors: detailedErrors,
        timeTaken,
        platformUsed,
      });

    } catch (err: any) {
      setError(err.message || '處理過程發生錯誤');
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  }, [selectedFile, platform, outputFileName]);

  const isLoaded = true; // No longer loading config

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-green-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <header className="relative text-center mb-6 sm:mb-8">
          <div className="absolute right-0 top-0">
            <button
              onClick={() => setShowConfig(!showConfig)}
              className={`p-2 rounded-full transition-colors flex items-center gap-2 text-sm font-medium ${showConfig ? 'bg-green-100 text-green-700' : 'text-gray-400 hover:bg-gray-100'
                }`}
              title={showConfig ? "返回報表生成" : "管理產品資料庫"}
            >
              <Settings className="w-5 h-5" />
              <span className="hidden sm:inline">{showConfig ? '隱藏設定' : '產品設定'}</span>
            </button>
          </div>
          <div className="flex items-center justify-center gap-2 sm:gap-3 mb-2">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-green-400 to-green-600 rounded-xl flex items-center justify-center shadow-lg">
              <FileSpreadsheet className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
            </div>
            <h1 className="text-xl sm:text-3xl font-bold text-gray-800">
              減醣市集 訂單報告生成器
            </h1>
          </div>
          <p className="text-sm sm:text-base text-gray-500">
            快速整合多平台訂單，一鍵生成出貨報告
          </p>
        </header>


        {showConfig ? (
          <SystemSettings onClose={() => setShowConfig(false)} />
        ) : (
          <div className="space-y-6">
            <section className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  1. 選擇電商平台
                </h2>
                <label className="flex items-center gap-2 cursor-pointer">
                  <span className="text-sm text-gray-600">自動識別</span>
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={autoDetectEnabled}
                      onChange={(e) => setAutoDetectEnabled(e.target.checked)}
                      className="sr-only"
                    />
                    <div className={`w-10 h-5 rounded-full transition-colors ${autoDetectEnabled ? 'bg-green-500' : 'bg-gray-300'}`}>
                      <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${autoDetectEnabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
                    </div>
                  </div>
                </label>
              </div>

              {/* 自動識別結果提示 */}
              {detectionResult && autoDetectEnabled && (
                <div className={`mb-4 p-3 rounded-lg border ${detectionResult.detected
                  ? 'bg-green-50 border-green-200'
                  : 'bg-yellow-50 border-yellow-200'
                  }`}>
                  {detectionResult.detected ? (
                    <div className="flex items-center gap-2">
                      <span className="text-green-600 text-sm">✓ 自動識別為</span>
                      <span className="font-semibold text-green-700">
                        {getPlatformDisplayName(detectionResult.detected)}
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-yellow-600 text-sm">⚠ 無法完全識別，已選擇最接近的平台:</span>
                      <span className="font-semibold text-yellow-700">
                        {getPlatformDisplayName(detectionResult.allPlatformScores[0]?.platform)}
                      </span>
                    </div>
                  )}
                </div>
              )}

              <PlatformSelector selected={platform} onChange={setPlatform} />
            </section>

            <section className="card p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">
                2. 上傳訂單檔案
              </h2>
              <FileUploader
                onFileSelect={handleFileSelect}
                selectedFile={selectedFile}
                onClear={handleClear}
              />
              {error && (
                <div
                  ref={errorRef}
                  className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700"
                >
                  {error}
                </div>
              )}
            </section>

            {rawData.length > 0 && (
              <>
                <DataPreview data={rawData} platform={platform} />

                <section className="card p-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-4">
                    3. 設定輸出檔名
                  </h2>
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={outputFileName}
                      onChange={(e) => setOutputFileName(e.target.value)}
                      placeholder="輸出檔案名稱"
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    />
                    <span className="flex items-center text-gray-500">.xlsx</span>
                  </div>
                </section>

                <section className="card p-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-4">
                    4. 生成報告
                  </h2>
                  <button
                    onClick={handleProcess}
                    disabled={isProcessing || !outputFileName.trim()}
                    className="w-full btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        處理中...
                      </>
                    ) : (
                      '生成並下載報告'
                    )}
                  </button>

                  {processingResult && (
                    <div ref={resultRef}>
                      <ProcessingResult
                        originalCount={processingResult.originalCount}
                        finalCount={processingResult.finalCount}
                        uniqueOrderCount={processingResult.uniqueOrderCount}
                        errors={processingResult.errors}
                        timeTaken={processingResult.timeTaken}
                        platformUsed={processingResult.platformUsed}
                      />
                    </div>
                  )}
                </section>
              </>
            )}

          </div>

        )}

        <footer className="mt-12 text-center text-sm text-gray-400">
          <p>減醣市集 訂單報告生成器 v2.0</p>
          <p className="mt-1">Made with Next.js • 部署於 Vercel</p>
        </footer>
      </div>
    </div>
  );
}
