import * as XLSX from 'xlsx';
import { RawOrderData, Platform } from '../types/order';
import { fieldConfig } from '@/config/fieldConfig';

export interface ValidationResult {
  isValid: boolean;
  missingRequired: string[];    // 缺少的必要欄位（會阻止生成）
  missingOptional: string[];    // 缺少的可選欄位（只警告）
  extraColumns: string[];
}

export interface PlatformDetectionResult {
  detected: Platform | null;
  confidence: number; // 0-100
  matchedColumns: string[];
  allPlatformScores: { platform: Platform; score: number; matched: string[] }[];
}

/**
 * 智慧識別 Excel 檔案對應的平台
 * 根據 fieldConfig 中定義的 identifyBy 特徵欄位進行匹配
 */
export function detectPlatform(data: RawOrderData[]): PlatformDetectionResult {
  if (data.length === 0) {
    return {
      detected: null,
      confidence: 0,
      matchedColumns: [],
      allPlatformScores: [],
    };
  }

  const actualColumns = Object.keys(data[0]).filter(col => !col.startsWith('Unnamed'));
  const platforms = Object.keys(fieldConfig) as Platform[];

  const scores = platforms.map(platform => {
    const config = fieldConfig[platform];
    const identifyColumns = config.identifyBy as readonly string[];
    const matched = identifyColumns.filter(col => actualColumns.includes(col));
    const score = (matched.length / identifyColumns.length) * 100;

    return {
      platform,
      score,
      matched,
    };
  });

  // 按分數排序，取最高分
  scores.sort((a, b) => b.score - a.score);
  const best = scores[0];

  // 只有當所有識別欄位都匹配時才視為成功識別
  const isFullMatch = best.score === 100;

  return {
    detected: isFullMatch ? best.platform : null,
    confidence: best.score,
    matchedColumns: best.matched,
    allPlatformScores: scores,
  };
}

/**
 * 取得平台的中文顯示名稱
 */
export function getPlatformDisplayName(platform: Platform): string {
  const names: Record<Platform, string> = {
    c2c: '快電商 C2C',
    shopline: 'SHOPLINE',
    mixx: 'MIXX 團購',
    aoshi: '奧世國際',
  };
  return names[platform] || platform;
}

export function readExcelFile(file: File): Promise<RawOrderData[]> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json<RawOrderData>(worksheet, { raw: false });
        resolve(jsonData);
      } catch (error) {
        reject(new Error('無法讀取 Excel 檔案'));
      }
    };

    reader.onerror = () => reject(new Error('檔案讀取失敗'));
    reader.readAsArrayBuffer(file);
  });
}

export function validateColumns(data: RawOrderData[], platform: Platform): ValidationResult {
  if (data.length === 0) {
    return { isValid: false, missingRequired: ['檔案為空'], missingOptional: [], extraColumns: [] };
  }

  const config = fieldConfig[platform];
  const requiredColumns: string[] = [...config.requiredColumns];
  const allColumns: string[] = [...config.columns];
  const actualColumns = Object.keys(data[0]).filter(col => !col.startsWith('Unnamed'));

  // 檢查必要欄位
  const missingRequired = requiredColumns.filter(col => !actualColumns.includes(col));

  // 檢查可選欄位（在 columns 中但不在 requiredColumns 中的欄位）
  const optionalColumns = allColumns.filter(col => !requiredColumns.includes(col));
  const missingOptional = optionalColumns.filter(col => !actualColumns.includes(col));

  const extraColumns = actualColumns.filter(col => !allColumns.includes(col));

  return {
    isValid: missingRequired.length === 0,  // 只有缺少必要欄位才會失敗
    missingRequired,
    missingOptional,
    extraColumns,
  };
}

export function sortByOrderId(data: RawOrderData[], platform: Platform): RawOrderData[] {
  const orderIdField = fieldConfig[platform].order_id;
  return [...data].sort((a, b) => {
    const aId = String(a[orderIdField] || '');
    const bId = String(b[orderIdField] || '');
    return aId.localeCompare(bId);
  });
}
