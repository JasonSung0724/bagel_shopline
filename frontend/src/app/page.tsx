'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { FileSpreadsheet, Loader2 } from 'lucide-react';
import FileUploader from '@/components/FileUploader';
import PlatformSelector from '@/components/PlatformSelector';
import DataPreview from '@/components/DataPreview';
import ConfigEditor from '@/components/ConfigEditor';
import ProcessingResult from '@/components/ProcessingResult';
import { useConfig } from '@/lib/hooks/useConfig';
import { Platform, RawOrderData, ProcessingError } from '@/lib/types/order';
import { readExcelFile, validateColumns, sortByOrderId, detectPlatform, getPlatformDisplayName, PlatformDetectionResult } from '@/lib/excel/ExcelReader';
import { fieldConfig } from '@/config/fieldConfig';
import { generateAndDownloadReport } from '@/lib/excel/ExcelWriter';
import { createAdapter } from '@/lib/adapters';
import { UnifiedOrderProcessor } from '@/lib/processors/UnifiedOrderProcessor';
import { extractStoreNames, fetchStoreAddresses } from '@/lib/api/storeAddress';

export default function Home() {
  const [platform, setPlatform] = useState<Platform>('shopline');
  const [autoDetectEnabled, setAutoDetectEnabled] = useState(true);
  const [detectionResult, setDetectionResult] = useState<PlatformDetectionResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [rawData, setRawData] = useState<RawOrderData[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [outputFileName, setOutputFileName] = useState('');
  const [processingResult, setProcessingResult] = useState<{
    originalCount: number;
    finalCount: number;
    uniqueOrderCount: number;
    errors: ProcessingError[];
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

  const {
    productConfig,
    isLoaded,
    updateProduct,
    deleteProduct,
    resetConfig,
    importConfig,
    exportConfig,
  } = useConfig();

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
    if (rawData.length === 0) return;

    setIsProcessing(true);
    setError(null);

    try {
      const validation = validateColumns(rawData, platform);
      if (!validation.isValid) {
        setError(`欄位驗證失敗。缺少必要欄位: ${validation.missingRequired.join(', ')}`);
        setIsProcessing(false);
        return;
      }

      // 如果有缺少的可選欄位，只在 console 顯示警告
      if (validation.missingOptional.length > 0) {
        console.log(`注意: 缺少可選欄位: ${validation.missingOptional.join(', ')}`);
      }

      const sortedData = sortByOrderId(rawData, platform);

      // SHOPLINE 需要查詢便利商店地址
      let storeAddress = undefined;
      if (platform === 'shopline') {
        const { sevenStores, familyStores } = extractStoreNames(sortedData);
        if (sevenStores.length > 0 || familyStores.length > 0) {
          console.log(`查詢便利商店地址: 7-11 ${sevenStores.length} 間, 全家 ${familyStores.length} 間`);
          storeAddress = await fetchStoreAddresses(sevenStores, familyStores);
        }
      }

      // 新架構：Adapter 轉換 → UnifiedProcessor 處理
      const adapter = createAdapter(platform, productConfig);
      const { items, errors: adapterErrors } = adapter.convert(sortedData, storeAddress);

      const processor = new UnifiedOrderProcessor(productConfig);
      const rows = processor.process(items);
      const processorErrors = processor.getErrors();

      const errors = [...adapterErrors, ...processorErrors];

      const orderIdField = fieldConfig[platform].order_id;
      const uniqueOrderCount = new Set(sortedData.map(r => String(r[orderIdField]))).size;

      console.log(`最終筆數: ${rows.length}\n`);
      console.log(`總訂單數: ${uniqueOrderCount}\n`);

      setProcessingResult({
        originalCount: rawData.length,
        finalCount: rows.length,
        uniqueOrderCount,
        errors,
      });

      await generateAndDownloadReport(rows, outputFileName);
    } catch (err) {
      setError('處理過程發生錯誤');
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  }, [rawData, platform, outputFileName, productConfig]);

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
        <header className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-2">
            <div className="w-12 h-12 bg-gradient-to-br from-green-400 to-green-600 rounded-xl flex items-center justify-center shadow-lg">
              <FileSpreadsheet className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-800">
              減醣市集 訂單報告生成器
            </h1>
          </div>
          <p className="text-gray-500">
            快速整合多平台訂單，一鍵生成出貨報告
          </p>
        </header>

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
              <div className={`mb-4 p-3 rounded-lg border ${
                detectionResult.detected
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
              <DataPreview data={rawData} />

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
                    />
                  </div>
                )}
              </section>
            </>
          )}

          <ConfigEditor
            productConfig={productConfig}
            onUpdate={updateProduct}
            onDelete={deleteProduct}
            onReset={resetConfig}
            onImport={importConfig}
            onExport={exportConfig}
          />
        </div>

        <footer className="mt-12 text-center text-sm text-gray-400">
          <p>減醣市集 訂單報告生成器 v2.0</p>
          <p className="mt-1">Made with Next.js • 部署於 Vercel</p>
        </footer>
      </div>
    </div>
  );
}
