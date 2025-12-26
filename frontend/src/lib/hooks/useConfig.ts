'use client';

import { useState, useCallback, useEffect } from 'react';
import { ProductInfo, productConfig as defaultProductConfig } from '@/config/productConfig';

const STORAGE_KEY = 'orderReportConfig';

interface ConfigState {
  productConfig: Record<string, ProductInfo>;
  lastUpdated: string;
}

export function useConfig() {
  const [productConfig, setProductConfig] = useState<Record<string, ProductInfo>>(() => ({ ...defaultProductConfig }));
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed: ConfigState = JSON.parse(stored);
        setProductConfig(parsed.productConfig);
      }
    } catch (e) {
      console.error('Failed to load config from localStorage');
    }
    setIsLoaded(true);
  }, []);

  const saveConfig = useCallback((newConfig: Record<string, ProductInfo>) => {
    setProductConfig(newConfig);
    const state: ConfigState = {
      productConfig: newConfig,
      lastUpdated: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, []);

  const resetConfig = useCallback(() => {
    saveConfig({ ...defaultProductConfig });
  }, [saveConfig]);

  const updateProduct = useCallback((code: string, info: ProductInfo) => {
    saveConfig({ ...productConfig, [code]: info });
  }, [productConfig, saveConfig]);

  const deleteProduct = useCallback((code: string) => {
    const newConfig = { ...productConfig };
    delete newConfig[code];
    saveConfig(newConfig);
  }, [productConfig, saveConfig]);

  const importConfig = useCallback((jsonString: string) => {
    try {
      const imported = JSON.parse(jsonString);
      saveConfig(imported);
      return true;
    } catch {
      return false;
    }
  }, [saveConfig]);

  const exportConfig = useCallback(() => {
    return JSON.stringify(productConfig, null, 2);
  }, [productConfig]);

  return {
    productConfig,
    isLoaded,
    saveConfig,
    resetConfig,
    updateProduct,
    deleteProduct,
    importConfig,
    exportConfig,
  };
}
