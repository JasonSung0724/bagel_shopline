import { useState, useEffect, useCallback } from 'react';
import { PlatformFieldConfig, FieldConfigMap, defaultFieldConfig, Platform } from '@/config/fieldConfig';

const FIELD_CONFIG_STORAGE_KEY = 'order-report-field-config';

/**
 * 欄位配置 Hook
 * 管理各平台的欄位映射配置，支援 localStorage 持久化
 */
export function useFieldConfig() {
  const [fieldConfig, setFieldConfig] = useState<FieldConfigMap>(defaultFieldConfig);
  const [isLoaded, setIsLoaded] = useState(false);

  // 從 localStorage 載入配置
  useEffect(() => {
    try {
      const stored = localStorage.getItem(FIELD_CONFIG_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as Partial<FieldConfigMap>;
        // 合併預設配置和儲存的配置
        const merged: FieldConfigMap = { ...defaultFieldConfig };
        for (const platform of Object.keys(parsed) as Platform[]) {
          if (parsed[platform]) {
            merged[platform] = { ...defaultFieldConfig[platform], ...parsed[platform] };
          }
        }
        setFieldConfig(merged);
      }
    } catch (error) {
      console.error('載入欄位配置失敗:', error);
    }
    setIsLoaded(true);
  }, []);

  // 儲存配置到 localStorage
  const saveConfig = useCallback((config: FieldConfigMap) => {
    try {
      // 只儲存與預設不同的配置
      const diff: Partial<FieldConfigMap> = {};
      for (const platform of Object.keys(config) as Platform[]) {
        if (JSON.stringify(config[platform]) !== JSON.stringify(defaultFieldConfig[platform])) {
          diff[platform] = config[platform];
        }
      }
      if (Object.keys(diff).length > 0) {
        localStorage.setItem(FIELD_CONFIG_STORAGE_KEY, JSON.stringify(diff));
      } else {
        localStorage.removeItem(FIELD_CONFIG_STORAGE_KEY);
      }
    } catch (error) {
      console.error('儲存欄位配置失敗:', error);
    }
  }, []);

  // 更新單一平台的欄位配置
  const updatePlatformConfig = useCallback((platform: Platform, config: Partial<PlatformFieldConfig>) => {
    setFieldConfig(prev => {
      const updated = {
        ...prev,
        [platform]: {
          ...prev[platform],
          ...config,
        },
      };
      saveConfig(updated);
      return updated;
    });
  }, [saveConfig]);

  // 更新單一欄位映射
  const updateFieldMapping = useCallback((
    platform: Platform,
    fieldKey: keyof PlatformFieldConfig,
    fieldName: string
  ) => {
    setFieldConfig(prev => {
      const updated = {
        ...prev,
        [platform]: {
          ...prev[platform],
          [fieldKey]: fieldName,
        },
      };
      saveConfig(updated);
      return updated;
    });
  }, [saveConfig]);

  // 重置單一平台配置為預設值
  const resetPlatformConfig = useCallback((platform: Platform) => {
    setFieldConfig(prev => {
      const updated = {
        ...prev,
        [platform]: defaultFieldConfig[platform],
      };
      saveConfig(updated);
      return updated;
    });
  }, [saveConfig]);

  // 重置所有配置為預設值
  const resetAllConfig = useCallback(() => {
    setFieldConfig(defaultFieldConfig);
    localStorage.removeItem(FIELD_CONFIG_STORAGE_KEY);
  }, []);

  // 取得特定平台的配置
  const getPlatformConfig = useCallback((platform: Platform): PlatformFieldConfig => {
    return fieldConfig[platform];
  }, [fieldConfig]);

  // 匯出配置
  const exportConfig = useCallback(() => {
    const dataStr = JSON.stringify(fieldConfig, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'field-config.json';
    a.click();
    URL.revokeObjectURL(url);
  }, [fieldConfig]);

  // 匯入配置
  const importConfig = useCallback((jsonString: string) => {
    try {
      const imported = JSON.parse(jsonString) as Partial<FieldConfigMap>;
      const merged: FieldConfigMap = { ...defaultFieldConfig };
      for (const platform of Object.keys(imported) as Platform[]) {
        if (imported[platform]) {
          merged[platform] = { ...defaultFieldConfig[platform], ...imported[platform] };
        }
      }
      setFieldConfig(merged);
      saveConfig(merged);
      return true;
    } catch (error) {
      console.error('匯入欄位配置失敗:', error);
      return false;
    }
  }, [saveConfig]);

  return {
    fieldConfig,
    isLoaded,
    updatePlatformConfig,
    updateFieldMapping,
    resetPlatformConfig,
    resetAllConfig,
    getPlatformConfig,
    exportConfig,
    importConfig,
  };
}
