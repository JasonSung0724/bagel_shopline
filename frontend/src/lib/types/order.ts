export interface OrderRow {
  [key: string]: string;
}

export interface RawOrderData {
  [key: string]: string | number | Date | null | undefined;
}

export interface ProcessingResult {
  rows: OrderRow[];
  statistics: ProcessingStatistics;
  errors: ProcessingError[];
}

export interface ProcessingStatistics {
  originalCount: number;
  finalCount: number;
  uniqueOrderCount: number;
  mainProductCount?: number;
  freebiesCount?: number;
  skippedCount?: number;
}

export interface ProcessingError {
  orderId: string;
  field: string;
  message: string;
  severity: 'warning' | 'error';
}

export type Platform = 'c2c' | 'shopline' | 'mixx' | 'aoshi';

export interface StoreAddress {
  SEVEN: Record<string, string>;
  FAMILY: Record<string, string>;
}
