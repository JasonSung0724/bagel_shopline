'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  Package,
  ShoppingBag,
  Box,
  TrendingUp,
  Calendar,
  AlertCircle,
  ArrowUpRight,
  ClipboardList,
  Search,
  RefreshCw,
  Loader2,
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  Lock,
  Eye,
  EyeOff,
  Download,
  X,
  Check,
  Clock,
} from 'lucide-react';

// API Base URL - empty string means same origin (use Nginx proxy)
// API Base URL - use relative path to route through Next.js proxy
const API_BASE_URL = '';

// Brand colors
const BRAND_ORANGE = '#EB5C20';
const BRAND_GRAY = '#9FA0A0';

// Lead time constants (前置期天數)
const LEAD_TIME = {
  bread: 20,  // 麵包代工期 20 天
  box: 20,    // 紙箱製作期 20 天
  bag: 30,    // 塑膠袋製作期 30 天
};

// Target stock days (正常水位天數)
const TARGET_DAYS = 30;

// Items per roll for bags (每捲塑膠袋可包裝麵包數)
const ITEMS_PER_ROLL = 6000;

// Stock health status types
type StockHealthStatus = 'critical' | 'healthy' | 'overstock';

// Stock breakdown by accept date
interface StockByAcceptDate {
  date: string;  // 客戶端允收日期
  stock: number; // 該日期對應的庫存數量
}

// Inventory diagnosis for each item (from backend API)
interface ItemDiagnosis {
  name: string;
  category: 'bread' | 'box' | 'bag';
  current_stock: number;
  unit: string;
  lead_time?: number;
  daily_sales?: number;       // 日銷：最新一天的出庫量
  daily_sales_30d?: number;   // 30日均銷量
  daily_sales_20d?: number;   // 塑膠袋不需要
  total_sales_30d?: number;  // 塑膠袋不需要
  total_sales_20d?: number;  // 塑膠袋不需要
  days_of_stock?: number;    // 塑膠袋不需要
  reorder_point: number;
  target_stock: number;
  health_status: StockHealthStatus;
  suggested_order: number;
  matched_bag?: ItemDiagnosis | null;
  stock_by_accept_date?: StockByAcceptDate[];  // 依客戶端允收日期分組的庫存明細
}

// Diagnosis API response
interface DiagnosisResponse {
  snapshot_date: string;
  bread_items: ItemDiagnosis[];
  box_items: ItemDiagnosis[];
  bag_items: ItemDiagnosis[];
  summary: {
    critical_count: number;
    healthy_count: number;
    overstock_count: number;
    total_bread_stock: number;
    total_box_stock: number;
    total_bag_stock: number;
    total_bag_capacity: number;  // 可包裝量 = 塑膠袋卷數 * 6000
  };
}

// Chart colors for multi-line display
const CHART_COLORS = [
  '#EB5C20', // Brand orange
  '#10B981', // Green
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#06B6D4', // Cyan
  '#EC4899', // Pink
  '#84CC16', // Lime
  '#6366F1', // Indigo
];

// Types
interface InventoryItem {
  id: string;
  name: string;
  category: 'bread' | 'box' | 'bag';
  stock: number;
  availableStock: number;
  unit: string;
  minStock: number;
  stockStatus: 'high' | 'medium' | 'low';
  itemsPerRoll?: number;
  // Calculated fields for display
  dailySales: number;
  sales7d: number;
  sales14d: number;
  sales30d: number;
}

interface RestockLog {
  date: string;
  product_name: string;
  category: string;
  stock_in: number;
  expiry_date: string | null;
  warehouse_date: string | null;
}

interface SnapshotSummary {
  id: string;
  snapshot_date: string;
  source_file: string;
  total_bread_stock: number;
  total_box_stock: number;
  total_bag_rolls: number;
  low_stock_count: number;
}

// Trend data types
interface TrendDataPoint {
  date: string;
  stock: number;
}

interface SalesDataPoint {
  date: string;
  sales: number;
}

interface ItemTrend {
  name: string;
  category: string;
  data: TrendDataPoint[];
}

interface ItemSalesTrend {
  name: string;
  category: string;
  data: SalesDataPoint[];
}

// Stats for each period (from backend)
interface SalesStats {
  total: number;
  avg: number;
  max: number;
  min: number;
  days: number;
}

interface StockStats {
  latest: number;
  oldest: number;
  change: number;
  days: number;
}

// Analysis API response (combined endpoint)
interface AnalysisResponse {
  success: boolean;
  data: {
    sales: {
      items: ItemSalesTrend[];
      stats: {
        "7": Record<string, SalesStats>;
        "14": Record<string, SalesStats>;
        "30": Record<string, SalesStats>;
      };
    };
    stock: {
      items: ItemTrend[];
      stats: {
        "7": Record<string, StockStats>;
        "14": Record<string, StockStats>;
        "30": Record<string, StockStats>;
      };
    };
  };
}

// API response types
interface ApiInventoryItem {
  id: string;
  name: string;
  category: string;
  current_stock: number;
  available_stock: number;
  defective_stock: number;
  unit: string;
  min_stock: number;
  stock_status: string;
  items_per_roll?: number;
}

interface ApiInventoryResponse {
  success: boolean;
  data: {
    id: string;
    snapshot_date: string;
    source_file: string;
    source_email_date: string;
    total_bread_stock: number;
    total_box_stock: number;
    total_bag_rolls: number;
    total_bread_defective: number;
    total_box_defective: number;
    total_bag_defective: number;
    low_stock_count: number;
    raw_item_count: number;
    bread_items: ApiInventoryItem[];
    box_items: ApiInventoryItem[];
    bag_items: ApiInventoryItem[];
  } | null;
  message?: string;
}

// Transform API item to frontend format
const transformApiItem = (
  item: ApiInventoryItem,
  category: 'bread' | 'box' | 'bag',
  historicalData?: Map<string, number[]>
): InventoryItem => {
  // Calculate daily sales from historical data if available
  // For now, estimate based on min_stock as a baseline
  const estimatedDailySales = Math.round(item.min_stock / 10) || 50;

  return {
    id: item.id,
    name: item.name,
    category,
    stock: item.current_stock,
    availableStock: item.available_stock,
    unit: item.unit,
    minStock: item.min_stock,
    stockStatus: item.stock_status as 'high' | 'medium' | 'low',
    itemsPerRoll: item.items_per_roll,
    dailySales: estimatedDailySales,
    sales7d: estimatedDailySales * 7,
    sales14d: estimatedDailySales * 14,
    sales30d: estimatedDailySales * 30,
  };
};

// --- Components ---

// Stat Card
interface StatCardProps {
  title: string;
  value: number;
  unit?: string;
  icon: React.ElementType;
  colorClass: string;
}

const StatCard = ({ title, value, unit, icon: Icon, colorClass }: StatCardProps) => (
  <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
    <div>
      <p className="text-sm font-medium text-gray-500 mb-1">{title}</p>
      <div className="flex items-baseline gap-1">
        <h3 className="text-3xl font-bold text-gray-800">{value.toLocaleString()}</h3>
        {unit && <span className="text-sm text-gray-400 font-normal">{unit}</span>}
      </div>
    </div>
    <div className={`p-4 rounded-full bg-opacity-10 ${colorClass.includes('text-') ? colorClass.replace('text-', 'bg-') : ''}`}>
      <Icon className={`w-8 h-8 ${colorClass}`} />
    </div>
  </div>
);

// Stock Level Bar
interface StockLevelBarProps {
  current: number;
  max?: number;
  lowThreshold?: number;
}

const StockLevelBar = ({ current, max = 12000, lowThreshold = 1000 }: StockLevelBarProps) => {
  const percentage = Math.min((current / max) * 100, 100);
  let colorClass = 'bg-[#EB5C20]';

  if (current <= lowThreshold) colorClass = 'bg-red-500';
  else if (current > max * 0.7) colorClass = 'bg-green-500';

  return (
    <div className="w-full bg-gray-100 rounded-full h-2.5 mt-2">
      <div
        className={`h-2.5 rounded-full ${colorClass} transition-all duration-500`}
        style={{ width: `${percentage}%` }}
      ></div>
    </div>
  );
};

// Tab types
type TabType = 'diagnosis' | 'inventory' | 'analysis' | 'restock' | 'order';

// Session storage key for auth
const AUTH_SESSION_KEY = 'inventory_auth';

export default function InventoryDashboard() {
  // Authentication state - check sessionStorage immediately to avoid flash
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem(AUTH_SESSION_KEY) === 'true';
    }
    return false;
  });
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<TabType>('diagnosis');
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [restockLogs, setRestockLogs] = useState<RestockLog[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [snapshotInfo, setSnapshotInfo] = useState<{
    snapshotDate: string;
    snapshotTime: string;
    sourceFile: string;
    sourceEmailDate: string;
    lowStockCount: number;
    totalBreadStock: number;
    totalBoxStock: number;
    totalBagRolls: number;
    totalBreadDefective: number;
    totalBoxDefective: number;
    totalBagDefective: number;
    rawItemCount: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trendData, setTrendData] = useState<ItemTrend[]>([]);
  const [salesTrendData, setSalesTrendData] = useState<ItemSalesTrend[]>([]);
  const [salesStats, setSalesStats] = useState<Record<string, Record<string, SalesStats>>>({});
  const [stockStats, setStockStats] = useState<Record<string, Record<string, StockStats>>>({});
  const [selectedTrendItems, setSelectedTrendItems] = useState<Set<string>>(new Set());
  const [selectedSalesItems, setSelectedSalesItems] = useState<Set<string>>(new Set());
  const [trendDays, setTrendDays] = useState<number>(30);
  const [analysisMode, setAnalysisMode] = useState<'stock' | 'sales'>('sales');  // Default to sales
  const [focusedItem, setFocusedItem] = useState<string | null>(null);  // Track focused item (clicked from table)
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [productMappings, setProductMappings] = useState<{ bread_name: string; bag_name: string }[]>([]);
  const [diagnosisData, setDiagnosisData] = useState<DiagnosisResponse | null>(null);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  // Restock filters
  const [restockProductFilter, setRestockProductFilter] = useState<string>('');
  const [restockDateFrom, setRestockDateFrom] = useState<string>('');
  const [restockDateTo, setRestockDateTo] = useState<string>(new Date().toISOString().slice(0, 10));

  // Bread diagnosis sort
  type BreadSortKey = 'daily_sales' | 'total_sales_30d' | 'current_stock' | 'days_of_stock';
  const [breadSortKey, setBreadSortKey] = useState<BreadSortKey>('daily_sales');
  const [breadSortDesc, setBreadSortDesc] = useState<boolean>(true);

  // Sync tool states
  const [showSyncTool, setShowSyncTool] = useState(false);
  const [showSalesSyncTool, setShowSalesSyncTool] = useState(false);
  const [syncStartDate, setSyncStartDate] = useState<string>('');
  const [syncEndDate, setSyncEndDate] = useState<string>('');
  const [syncLoading, setSyncLoading] = useState(false);
  const [salesSyncLoading, setSalesSyncLoading] = useState(false);
  // syncTaskId removed - no longer tracking task status
  const [syncTaskStatus, setSyncTaskStatus] = useState<{
    status: 'pending' | 'running' | 'completed' | 'failed' | 'started';
    result?: {
      success: boolean;
      message: string;
      synced_count?: number;
      failed_count?: number;
      skipped_count?: number;
      details?: Array<{ date: string; success: boolean; message: string }>;
    };
    error?: string;
  } | null>(null);
  const [salesSyncTaskStatus, setSalesSyncTaskStatus] = useState<{
    status: 'started' | 'failed';
    error?: string;
  } | null>(null);


  // Handle password submission
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);

    try {
      const response = await fetch('/api/auth/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password }),
      });

      const result = await response.json();

      if (result.success) {
        sessionStorage.setItem(AUTH_SESSION_KEY, 'true');
        // Start loading data immediately while updating auth state
        // Use combined API for faster initial load (single request instead of multiple)
        setLoading(true);
        setIsAuthenticated(true);
        fetchInitialData().then(() => {
          setLoading(false);
        });
      } else {
        setAuthError(result.message || '密碼錯誤');
      }
    } catch {
      setAuthError('連線錯誤，請稍後再試');
    } finally {
      setAuthLoading(false);
    }
  };

  // Fetch inventory from API
  const fetchInventory = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/inventory`);
      const result: ApiInventoryResponse = await response.json();

      if (result.success && result.data) {
        const {
          bread_items,
          box_items,
          bag_items,
          snapshot_date,
          source_file,
          source_email_date,
          low_stock_count,
          total_bread_stock,
          total_box_stock,
          total_bag_rolls,
          total_bread_defective,
          total_box_defective,
          total_bag_defective,
          raw_item_count,
        } = result.data;

        // Transform API items to frontend format
        const allItems: InventoryItem[] = [
          ...bread_items.map((item) => transformApiItem(item, 'bread')),
          ...box_items.map((item) => transformApiItem(item, 'box')),
          ...bag_items.map((item) => transformApiItem(item, 'bag')),
        ];

        setItems(allItems);

        // Parse dates for display
        const snapshotDateObj = new Date(snapshot_date);
        setSnapshotInfo({
          snapshotDate: `${snapshotDateObj.getMonth() + 1}/${snapshotDateObj.getDate()}`,
          snapshotTime: '',  // Not used anymore
          sourceFile: source_file,
          sourceEmailDate: new Date(source_email_date).toLocaleString('zh-TW'),
          lowStockCount: low_stock_count,
          totalBreadStock: total_bread_stock,
          totalBoxStock: total_box_stock,
          totalBagRolls: total_bag_rolls,
          totalBreadDefective: total_bread_defective ?? 0,
          totalBoxDefective: total_box_defective ?? 0,
          totalBagDefective: total_bag_defective ?? 0,
          rawItemCount: raw_item_count,
        });
      } else {
        setError(result.message || '無庫存資料，請先同步');
      }
    } catch (err) {
      console.error('Failed to fetch inventory:', err);
      setError('無法連接伺服器，請確認後端已啟動');
    }
  }, []);

  // Fetch restock logs (入庫紀錄)
  const fetchRestockLogs = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/inventory/restock?days=30`);
      const result = await response.json();

      if (result.success && result.data) {
        setRestockLogs(result.data);
      }
    } catch (err) {
      console.error('Failed to fetch restock logs:', err);
    }
  }, []);

  // Fetch combined analysis data (sales + stock trends with stats for all periods)
  const fetchAnalysisData = useCallback(async (category: string = 'bread') => {
    try {
      setAnalysisLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/inventory/analysis?category=${category}`);
      const result: AnalysisResponse = await response.json();

      if (result.success && result.data) {
        // Set sales data
        setSalesTrendData(result.data.sales.items);
        setSalesStats(result.data.sales.stats);

        // Set stock data
        setTrendData(result.data.stock.items);
        setStockStats(result.data.stock.stats);

        // Auto-select all items by default
        if (result.data.sales.items.length > 0) {
          setSelectedSalesItems(new Set(result.data.sales.items.map((item: ItemSalesTrend) => item.name)));
        }
        if (result.data.stock.items.length > 0) {
          setSelectedTrendItems(new Set(result.data.stock.items.map((item: ItemTrend) => item.name)));
        }
      }
    } catch (err) {
      console.error('Failed to fetch analysis data:', err);
    } finally {
      setAnalysisLoading(false);
    }
  }, []);

  // Legacy fetch functions (kept for compatibility, but now just call the combined API)
  const fetchTrendData = useCallback(async (category?: string) => {
    await fetchAnalysisData(category || 'bread');
  }, [fetchAnalysisData]);

  const fetchSalesTrend = useCallback(async (category?: string) => {
    await fetchAnalysisData(category || 'bread');
  }, [fetchAnalysisData]);

  // Fetch product mappings (bread to bag relationships)
  const fetchProductMappings = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/inventory/product-mappings`);
      const result = await response.json();

      if (result.success && result.data) {
        setProductMappings(result.data);
      }
    } catch (err) {
      console.error('Failed to fetch product mappings:', err);
    }
  }, []);

  // Fetch comprehensive diagnosis data from backend (all calculations done server-side)
  const fetchDiagnosis = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/inventory/diagnosis`);
      const result = await response.json();

      if (result.success && result.data) {
        setDiagnosisData(result.data);
      }
    } catch (err) {
      console.error('Failed to fetch diagnosis:', err);
    }
  }, []);

  // Fetch all initial data in ONE request (faster than multiple parallel calls)
  const fetchInitialData = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/inventory/init`);
      const result = await response.json();

      if (result.success && result.data) {
        // Process inventory data
        const inventoryData = result.data.inventory;
        if (inventoryData) {
          const {
            bread_items,
            box_items,
            bag_items,
            snapshot_date,
            source_file,
            source_email_date,
            low_stock_count,
            total_bread_stock,
            total_box_stock,
            total_bag_rolls,
            total_bread_defective,
            total_box_defective,
            total_bag_defective,
            raw_item_count,
          } = inventoryData;

          const allItems: InventoryItem[] = [
            ...bread_items.map((item: ApiInventoryItem) => transformApiItem(item, 'bread')),
            ...box_items.map((item: ApiInventoryItem) => transformApiItem(item, 'box')),
            ...bag_items.map((item: ApiInventoryItem) => transformApiItem(item, 'bag')),
          ];

          setItems(allItems);

          const snapshotDateObj = new Date(snapshot_date);
          setSnapshotInfo({
            snapshotDate: `${snapshotDateObj.getMonth() + 1}/${snapshotDateObj.getDate()}`,
            snapshotTime: '',
            sourceFile: source_file,
            sourceEmailDate: new Date(source_email_date).toLocaleString('zh-TW'),
            lowStockCount: low_stock_count,
            totalBreadStock: total_bread_stock,
            totalBoxStock: total_box_stock,
            totalBagRolls: total_bag_rolls,
            totalBreadDefective: total_bread_defective ?? 0,
            totalBoxDefective: total_box_defective ?? 0,
            totalBagDefective: total_bag_defective ?? 0,
            rawItemCount: raw_item_count,
          });
        } else {
          setError('無庫存資料，請先同步');
        }

        // Process diagnosis data (check for valid structure, not just truthy)
        if (result.data.diagnosis && result.data.diagnosis.bread_items) {
          setDiagnosisData(result.data.diagnosis);
        }
      } else {
        setError(result.error || '無法載入資料');
      }
    } catch (err) {
      console.error('Failed to fetch initial data:', err);
      setError('無法連接伺服器，請確認後端已啟動');
    }
  }, []);

  // Toggle item selection
  const toggleTrendItem = (name: string) => {
    setSelectedTrendItems(prev => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const toggleSalesItem = (name: string) => {
    setSelectedSalesItems(prev => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  // Select/deselect all
  const selectAllTrendItems = () => {
    setSelectedTrendItems(new Set(trendData.map(item => item.name)));
  };

  const deselectAllTrendItems = () => {
    setSelectedTrendItems(new Set());
  };

  const selectAllSalesItems = () => {
    setSelectedSalesItems(new Set(salesTrendData.map(item => item.name)));
  };

  const deselectAllSalesItems = () => {
    setSelectedSalesItems(new Set());
  };

  // Initialize: fetch all data on page reload (when already authenticated)
  useEffect(() => {
    // Only run on mount when already authenticated from session storage
    // (handleLogin handles fresh logins and starts loading there)
    if (!isAuthenticated) return;

    const init = async () => {
      setLoading(true);
      // Use combined API for faster initial load (single request)
      await fetchInitialData();
      setLoading(false);
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-fetch data when switching tabs
  useEffect(() => {
    if (activeTab === 'analysis') {
      if (analysisMode === 'sales' && salesTrendData.length === 0) {
        fetchSalesTrend('bread');
      } else if (analysisMode === 'stock' && trendData.length === 0) {
        fetchTrendData('bread');
      }
    } else if (activeTab === 'restock' && restockLogs.length === 0) {
      fetchRestockLogs();
    }
  }, [activeTab, analysisMode, salesTrendData.length, trendData.length, restockLogs.length, fetchSalesTrend, fetchTrendData, fetchRestockLogs]);

  // Refresh data from database (no sync from email)
  const handleRefresh = async () => {
    setSyncing(true);

    switch (activeTab) {
      case 'diagnosis':
      case 'order':
        // Both diagnosis and order tabs need both inventory + diagnosis data
        // Use combined API for efficiency
        await fetchInitialData();
        break;
      case 'inventory':
        // Inventory tab only needs basic inventory data
        await fetchInventory();
        break;
      case 'analysis':
        if (analysisMode === 'sales') {
          await fetchSalesTrend('bread');
        } else {
          await fetchTrendData('bread');
        }
        break;
      case 'restock':
        await fetchRestockLogs();
        break;
    }

    setSyncing(false);
  };

  // Handle date range sync (補同步)
  const handleDateRangeSync = async () => {
    if (!syncStartDate || !syncEndDate) {
      return;
    }

    setSyncLoading(true);
    setSyncTaskStatus(null);

    try {
      // Call API with async=true to run in background
      const response = await fetch(`${API_BASE_URL}/api/inventory/sync`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start_date: syncStartDate,
          end_date: syncEndDate,
          async: true,
          notify: false,
        }),
      });

      const result = await response.json();

      if (result.success) {
        // Task started successfully, show message and close
        setSyncTaskStatus({ status: 'started' });
        setSyncLoading(false);
      } else {
        setSyncTaskStatus({
          status: 'failed',
          error: result.error || '啟動同步任務失敗',
        });
        setSyncLoading(false);
      }
    } catch {
      setSyncTaskStatus({
        status: 'failed',
        error: '連線錯誤，請稍後再試',
      });
      setSyncLoading(false);
    }
  };

  // Reset sync tool state
  const resetSyncTool = () => {
    setSyncStartDate('');
    setSyncEndDate('');
    setSyncTaskStatus(null);
    setSyncLoading(false);
  };

  // Handle sales date range sync (補銷量)
  const handleSalesDateRangeSync = async () => {
    if (!syncStartDate || !syncEndDate) {
      return;
    }

    setSalesSyncLoading(true);
    setSalesSyncTaskStatus(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/sales/sync`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start_date: syncStartDate,
          end_date: syncEndDate,
          async: true,
        }),
      });

      const result = await response.json();

      if (result.success) {
        setSalesSyncTaskStatus({ status: 'started' });
        setSalesSyncLoading(false);
      } else {
        setSalesSyncTaskStatus({
          status: 'failed',
          error: result.error || '啟動銷量同步任務失敗',
        });
        setSalesSyncLoading(false);
      }
    } catch {
      setSalesSyncTaskStatus({
        status: 'failed',
        error: '連線錯誤，請稍後再試',
      });
      setSalesSyncLoading(false);
    }
  };

  // Reset sales sync tool state
  const resetSalesSyncTool = () => {
    setSyncStartDate('');
    setSyncEndDate('');
    setSalesSyncTaskStatus(null);
    setSalesSyncLoading(false);
  };

  // Computed Totals
  const totals = useMemo(() => {
    return {
      bread: items.filter((i) => i.category === 'bread').reduce((acc, curr) => acc + curr.stock, 0),
      box: items.filter((i) => i.category === 'box').reduce((acc, curr) => acc + curr.stock, 0),
      bag: items.filter((i) => i.category === 'bag').reduce((acc, curr) => acc + curr.stock, 0),
    };
  }, [items]);

  // Summary statistics from backend diagnosis data
  const diagnosisSummary = useMemo(() => {
    if (!diagnosisData) {
      return {
        criticalCount: 0,
        overstockCount: 0,
        healthyCount: 0,
        totalBagCapacity: 0,
        totalDailySales: 0,
      };
    }
    // Calculate total daily bread sales (sum of all bread items' daily_sales)
    const totalDailySales = diagnosisData.bread_items.reduce(
      (sum, item) => sum + (item.daily_sales ?? 0),
      0
    );
    return {
      criticalCount: diagnosisData.summary.critical_count,
      overstockCount: diagnosisData.summary.overstock_count,
      healthyCount: diagnosisData.summary.healthy_count,
      totalBagCapacity: diagnosisData.summary.total_bag_capacity,
      totalDailySales,
    };
  }, [diagnosisData]);

  // All diagnosis items from backend (bread, box, bag combined)
  const allDiagnosisItems = useMemo((): ItemDiagnosis[] => {
    if (!diagnosisData) return [];
    return [
      ...diagnosisData.bread_items,
      ...diagnosisData.box_items,
      ...diagnosisData.bag_items,
    ];
  }, [diagnosisData]);

  // Items that need ordering (for order suggestion tab)
  const orderSuggestions = useMemo(() => {
    return allDiagnosisItems
      .filter(d => d.health_status === 'critical' && d.suggested_order > 0)
      .sort((a, b) => (a.days_of_stock ?? 0) - (b.days_of_stock ?? 0));  // Most urgent first
  }, [allDiagnosisItems]);

  const filteredItems = items.filter((item) =>
    item.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const breadItems = filteredItems.filter((i) => i.category === 'bread');
  const boxItems = filteredItems.filter((i) => i.category === 'box');
  const bagItems = filteredItems.filter((i) => i.category === 'bag');

  // Filtered diagnosis items by category (from backend data)
  const breadDiagnoses = useMemo(() => {
    if (!diagnosisData) return [];
    return diagnosisData.bread_items.filter(d =>
      d.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [diagnosisData, searchTerm]);

  const boxDiagnoses = useMemo(() => {
    if (!diagnosisData) return [];
    return diagnosisData.box_items.filter(d =>
      d.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [diagnosisData, searchTerm]);

  const bagDiagnoses = useMemo(() => {
    if (!diagnosisData) return [];
    return diagnosisData.bag_items.filter(d =>
      d.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [diagnosisData, searchTerm]);

  // Pair bread items with their matching bags (matched_bag comes from backend) and apply sorting
  const pairedBreadDiagnoses = useMemo(() => {
    const paired = breadDiagnoses.map(bread => ({
      bread,
      bag: bread.matched_bag || null,
    }));

    // Sort by selected key
    return paired.sort((a, b) => {
      const aVal = a.bread[breadSortKey] ?? 0;
      const bVal = b.bread[breadSortKey] ?? 0;
      return breadSortDesc ? bVal - aVal : aVal - bVal;
    });
  }, [breadDiagnoses, breadSortKey, breadSortDesc]);

  // Bags that don't have a matching bread (standalone bags)
  const standaloneBags = useMemo(() => {
    const pairedBagNames = new Set(
      pairedBreadDiagnoses
        .filter(p => p.bag)
        .map(p => p.bag!.name)
    );
    return bagDiagnoses.filter(bag => !pairedBagNames.has(bag.name));
  }, [bagDiagnoses, pairedBreadDiagnoses]);

  // Show login form if not authenticated (must be checked FIRST before loading/error states)
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-lg p-6 sm:p-8 w-full max-w-sm">
          <div className="text-center mb-6">
            <div className="w-14 h-14 rounded-xl bg-[#EB5C20] flex items-center justify-center text-white font-bold text-xl mx-auto mb-4">
              CR
            </div>
            <h1 className="text-xl font-bold text-gray-900">減醣市集 庫存系統</h1>
            <p className="text-sm text-gray-500 mt-1">請輸入密碼以存取庫存管理系統</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                密碼
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#EB5C20] focus:border-[#EB5C20] outline-none transition-colors"
                  placeholder="請輸入密碼"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {authError && (
              <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 p-3 rounded-lg">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading || !password}
              className="w-full py-2.5 bg-[#EB5C20] text-white font-medium rounded-lg hover:bg-[#d54e18] disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {authLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  驗證中...
                </>
              ) : (
                '登入'
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Loading state (only shown after authenticated)
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#EB5C20] mx-auto mb-4" />
          <p className="text-gray-600">載入庫存資料中...</p>
        </div>
      </div>
    );
  }

  // Error state with no data (only shown after authenticated)
  if (error && items.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-[#EB5C20] mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-800 mb-2">無法載入庫存資料</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={handleRefresh}
            disabled={syncing}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#EB5C20] text-white rounded-lg hover:bg-[#d44c15] transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? '載入中...' : '重新載入'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 font-sans text-gray-800">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Top row: Logo + Title + Refresh */}
          <div className="flex justify-between items-center h-14 lg:h-16">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
              <Link
                href="/"
                className="flex items-center gap-2 text-gray-600 hover:text-[#EB5C20] transition-colors flex-shrink-0"
              >
                <ArrowLeft className="w-4 h-4" />
              </Link>
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded bg-[#EB5C20] flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                CR
              </div>
              <div className="min-w-0 flex-1">
                <h1 className="text-base sm:text-xl font-bold text-gray-900 tracking-tight truncate">
                  減醣市集{' '}
                  <span className="hidden sm:inline text-[#9FA0A0] font-normal text-sm ml-2">
                    庫存管理儀表板
                  </span>
                </h1>
                {/* Mobile: show badges below title */}
                <div className="flex items-center gap-1 mt-0.5 sm:hidden">
                  {snapshotInfo && (
                    <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-full border border-blue-200">
                      {snapshotInfo.snapshotDate}
                    </span>
                  )}
                  {snapshotInfo && snapshotInfo.lowStockCount > 0 && (
                    <span className="text-[10px] bg-red-100 text-red-600 px-1.5 py-0.5 rounded-full">
                      {snapshotInfo.lowStockCount} 項低庫存
                    </span>
                  )}
                </div>
                {/* Desktop: show badges inline */}
                <div className="hidden sm:inline-flex items-center gap-2 ml-2">
                  {snapshotInfo && (
                    <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full border border-blue-200">
                      資料時間: {snapshotInfo.snapshotDate} {snapshotInfo.snapshotTime}
                    </span>
                  )}
                  {snapshotInfo && snapshotInfo.lowStockCount > 0 && (
                    <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                      {snapshotInfo.lowStockCount} 項低庫存
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Buttons */}
            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0 ml-2">
              {/* Sync Inventory Button */}
              <button
                onClick={() => setShowSyncTool(true)}
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 text-xs sm:text-sm bg-[#EB5C20] text-white rounded-lg hover:bg-[#d44c15] transition-colors"
              >
                <Download className="w-4 h-4" />
                <span className="hidden sm:inline">補庫存</span>
              </button>

              {/* Sync Sales Button */}
              <button
                onClick={() => setShowSalesSyncTool(true)}
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 text-xs sm:text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                <TrendingUp className="w-4 h-4" />
                <span className="hidden sm:inline">補銷量</span>
              </button>

              {/* Refresh Button */}
              <button
                onClick={handleRefresh}
                disabled={syncing}
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 text-xs sm:text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">{syncing ? '載入中...' : '重新整理'}</span>
              </button>
            </div>
          </div>

          {/* Tab Navigation - scrollable on mobile */}
          <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0 pb-2 sm:pb-0">
            <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg w-max sm:w-auto">
              {[
                { id: 'diagnosis' as TabType, label: '庫存診斷', shortLabel: '診斷', icon: AlertCircle },
                { id: 'order' as TabType, label: '叫貨建議', shortLabel: '叫貨', icon: FileText },
                { id: 'inventory' as TabType, label: '庫存總覽', shortLabel: '總覽', icon: Package },
                { id: 'analysis' as TabType, label: '銷量分析', shortLabel: '分析', icon: TrendingUp },
                { id: 'restock' as TabType, label: '進貨紀錄', shortLabel: '進貨', icon: ClipboardList },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm font-medium rounded-md transition-all whitespace-nowrap
                    ${activeTab === tab.id
                      ? 'bg-white text-[#EB5C20] shadow-sm'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-200'
                    }
                  `}
                >
                  <tab.icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  <span className="sm:hidden">{tab.shortLabel}</span>
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8">
        {/* Top Diagnosis Stats */}
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2 sm:gap-4 mb-4 sm:mb-8">
          {/* Diagnosis Summary Cards - compact on mobile */}
          <div className="col-span-1 md:col-span-2 bg-white p-3 sm:p-5 rounded-xl shadow-sm border-l-4 border-red-500">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-[10px] sm:text-sm font-medium text-gray-500 mb-0.5 sm:mb-1">急需補貨</p>
                <div className="flex items-baseline gap-1 sm:gap-2">
                  <h3 className="text-xl sm:text-3xl font-bold text-red-600">{diagnosisSummary.criticalCount}</h3>
                  <span className="text-[10px] sm:text-sm text-gray-400">項</span>
                </div>
                <p className="hidden sm:block text-xs text-gray-400 mt-1">庫存量已無法支撐到下次到貨</p>
              </div>
              <div className="hidden sm:block p-3 rounded-full bg-red-50">
                <AlertTriangle className="w-8 h-8 text-red-500" />
              </div>
            </div>
          </div>

          <div className="col-span-1 md:col-span-2 bg-white p-3 sm:p-5 rounded-xl shadow-sm border-l-4 border-orange-400">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-[10px] sm:text-sm font-medium text-gray-500 mb-0.5 sm:mb-1">庫存積壓</p>
                <div className="flex items-baseline gap-1 sm:gap-2">
                  <h3 className="text-xl sm:text-3xl font-bold text-orange-500">{diagnosisSummary.overstockCount}</h3>
                  <span className="text-[10px] sm:text-sm text-gray-400">項</span>
                </div>
                <p className="hidden sm:block text-xs text-gray-400 mt-1">高於正常水位，建議暫緩進貨</p>
              </div>
              <div className="hidden sm:block p-3 rounded-full bg-orange-50">
                <Box className="w-8 h-8 text-orange-500" />
              </div>
            </div>
          </div>

          <div className="col-span-1 md:col-span-2 bg-white p-3 sm:p-5 rounded-xl shadow-sm border-l-4 border-green-500">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-[10px] sm:text-sm font-medium text-gray-500 mb-0.5 sm:mb-1">水位健康</p>
                <div className="flex items-baseline gap-1 sm:gap-2">
                  <h3 className="text-xl sm:text-3xl font-bold text-green-600">{diagnosisSummary.healthyCount}</h3>
                  <span className="text-[10px] sm:text-sm text-gray-400">項</span>
                </div>
                <p className="hidden sm:block text-xs text-gray-400 mt-1">庫存介於補貨點與正常水位之間</p>
              </div>
              <div className="hidden sm:block p-3 rounded-full bg-green-50">
                <CheckCircle2 className="w-8 h-8 text-green-500" />
              </div>
            </div>
          </div>
        </div>

        {/* Secondary Stats - Original totals */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-4 mb-4 sm:mb-8">
          <div className="bg-[#FFF7ED] p-2 sm:p-4 rounded-lg border border-[#FDBA74] flex items-center justify-between">
            <div>
              <p className="text-[10px] sm:text-xs text-[#C2410C]">今日總銷量</p>
              <p className="text-sm sm:text-xl font-bold text-[#EA580C]">{diagnosisSummary.totalDailySales.toLocaleString()} <span className="text-[10px] sm:text-sm font-normal text-[#FB923C]">個</span></p>
            </div>
            <ShoppingBag className="w-4 h-4 sm:w-6 sm:h-6 text-[#EA580C]" />
          </div>
          <div className="bg-gray-50 p-2 sm:p-4 rounded-lg border border-gray-200 flex items-center justify-between">
            <div>
              <p className="text-[10px] sm:text-xs text-gray-500">麵包總庫存</p>
              <p className="text-sm sm:text-xl font-bold text-gray-800">{totals.bread.toLocaleString()} <span className="text-[10px] sm:text-sm font-normal text-gray-400">個</span></p>
              <p className="text-[10px] sm:text-xs text-gray-400 mt-0.5">不良品: <span className="text-gray-500">{(snapshotInfo?.totalBreadDefective ?? 0).toLocaleString()}</span></p>
            </div>
            <Package className="w-4 h-4 sm:w-6 sm:h-6 text-[#EB5C20]" />
          </div>
          <div className="bg-gray-50 p-2 sm:p-4 rounded-lg border border-gray-200 flex items-center justify-between">
            <div>
              <p className="text-[10px] sm:text-xs text-gray-500">紙箱總庫存</p>
              <p className="text-sm sm:text-xl font-bold text-gray-800">{totals.box.toLocaleString()} <span className="text-[10px] sm:text-sm font-normal text-gray-400">個</span></p>
              <p className="text-[10px] sm:text-xs text-gray-400 mt-0.5">不良品: <span className="text-gray-500">{(snapshotInfo?.totalBoxDefective ?? 0).toLocaleString()}</span></p>
            </div>
            <Box className="w-4 h-4 sm:w-6 sm:h-6 text-gray-500" />
          </div>
          <div className="bg-gray-50 p-2 sm:p-4 rounded-lg border border-gray-200 flex items-center justify-between">
            <div>
              <p className="text-[10px] sm:text-xs text-gray-500">塑膠袋總庫存</p>
              <p className="text-sm sm:text-xl font-bold text-gray-800">{Number(totals.bag.toFixed(1)).toLocaleString()} <span className="text-[10px] sm:text-sm font-normal text-gray-400">捲</span></p>
              <p className="text-[10px] sm:text-xs text-gray-400 mt-0.5">不良品: <span className="text-gray-500">{(snapshotInfo?.totalBagDefective ?? 0).toLocaleString()}</span></p>
              <p className="hidden sm:block text-xs text-gray-400 mt-0.5">可包裝約 {diagnosisSummary.totalBagCapacity.toLocaleString()} 個</p>
            </div>
            <Package className="w-4 h-4 sm:w-6 sm:h-6 text-blue-500" />
          </div>
        </div>

        {/* Tab Content: Diagnosis */}
        {activeTab === 'diagnosis' && (
          <div className="space-y-4 sm:space-y-8">
            {/* Search Filter */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 bg-white p-3 sm:p-4 rounded-lg shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 flex-1">
                <Search className="text-gray-400 w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" />
                <input
                  type="text"
                  placeholder="搜尋商品名稱..."
                  className="flex-1 outline-none text-sm sm:text-base text-gray-700 placeholder-gray-400"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-2 sm:gap-3 text-[10px] sm:text-xs text-gray-500 overflow-x-auto">
                <span className="flex items-center gap-1 whitespace-nowrap"><span className="w-2 h-2 rounded-full bg-red-500"></span>低於{LEAD_TIME.bread}天</span>
                <span className="flex items-center gap-1 whitespace-nowrap"><span className="w-2 h-2 rounded-full bg-green-500"></span>正常</span>
                <span className="flex items-center gap-1 whitespace-nowrap"><span className="w-2 h-2 rounded-full bg-orange-400"></span>高於{TARGET_DAYS}天</span>
              </div>
            </div>

            {/* Bread + Bag Paired Diagnosis */}
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 sm:mb-4">
                <h2 className="text-base sm:text-lg font-bold text-gray-800 flex items-center gap-2">
                  <span className="w-1 sm:w-1.5 h-5 sm:h-6 bg-[#EB5C20] rounded-full"></span>
                  麵包庫存診斷 ({pairedBreadDiagnoses.length})
                </h2>
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Sort selector */}
                  <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-lg px-2 py-1">
                    <span className="text-[10px] sm:text-xs text-gray-500">排序:</span>
                    <select
                      value={breadSortKey}
                      onChange={(e) => setBreadSortKey(e.target.value as typeof breadSortKey)}
                      className="text-[10px] sm:text-xs bg-transparent border-none outline-none text-gray-700 cursor-pointer"
                    >
                      <option value="daily_sales">日銷量</option>
                      <option value="total_sales_30d">30日銷量</option>
                      <option value="current_stock">庫存量</option>
                      <option value="days_of_stock">可售天數</option>
                    </select>
                    <button
                      onClick={() => setBreadSortDesc(!breadSortDesc)}
                      className="text-gray-500 hover:text-gray-700 p-0.5"
                      title={breadSortDesc ? '降序' : '升序'}
                    >
                      {breadSortDesc ? '↓' : '↑'}
                    </button>
                  </div>
                  <span className="text-[10px] sm:text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    麵包前置期: {LEAD_TIME.bread} 天 | 塑膠袋前置期: {LEAD_TIME.bag} 天
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {pairedBreadDiagnoses.map(({ bread, bag }) => {
                  // Bread bar calculations
                  const breadBarMax = Math.max(bread.current_stock, bread.target_stock) * 1.2 || 1;
                  const breadReorderPercent = (bread.reorder_point / breadBarMax) * 100;
                  const breadTargetPercent = (bread.target_stock / breadBarMax) * 100;
                  const breadCurrentPercent = Math.min((bread.current_stock / breadBarMax) * 100, 100);

                  // Bag bar calculations (if exists)
                  const bagBarMax = bag ? Math.max(bag.current_stock, bag.target_stock) * 1.2 || 1 : 1;
                  const bagReorderPercent = bag ? (bag.reorder_point / bagBarMax) * 100 : 0;
                  const bagTargetPercent = bag ? (bag.target_stock / bagBarMax) * 100 : 0;
                  const bagCurrentPercent = bag ? Math.min((bag.current_stock / bagBarMax) * 100, 100) : 0;

                  return (
                    <div
                      key={bread.name}
                      className="bg-white p-5 rounded-xl shadow-sm hover:shadow-md transition-shadow"
                    >
                      {/* Header: Title + Bread Status Badge (獨立顯示麵包狀態) */}
                      <div className="flex justify-between items-start mb-1">
                        <h3 className="font-bold text-gray-800 text-lg">{bread.name}</h3>
                        <span
                          className={`text-xs px-3 py-1 rounded-lg font-medium flex items-center gap-1 ${bread.health_status === 'critical'
                            ? 'bg-red-100 text-red-600'
                            : bread.health_status === 'overstock'
                              ? 'bg-orange-100 text-orange-600'
                              : 'bg-green-100 text-green-600'
                            }`}
                        >
                          {bread.health_status === 'critical' && <AlertTriangle className="w-3 h-3" />}
                          {bread.health_status === 'overstock' && <Box className="w-3 h-3" />}
                          {bread.health_status === 'healthy' && <CheckCircle2 className="w-3 h-3" />}
                          {bread.health_status === 'critical' ? '急需補貨' : bread.health_status === 'overstock' ? '庫存積壓' : '水位健康'}
                        </span>
                      </div>

                      {/* Bread Section */}
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-2">
                          <ShoppingBag className="w-4 h-4 text-[#EB5C20]" />
                          <span className="text-sm font-medium text-gray-700">麵包</span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${bread.health_status === 'critical' ? 'bg-red-100 text-red-600' :
                              bread.health_status === 'overstock' ? 'bg-orange-100 text-orange-600' : 'bg-green-100 text-green-600'
                              }`}
                          >
                            {bread.days_of_stock} 天
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mb-2">
                          日銷: {(bread.daily_sales ?? 0).toLocaleString()} | 30日銷量: {(bread.total_sales_30d ?? 0).toLocaleString()}
                        </p>
                        <div className="flex items-baseline gap-2 mb-2">
                          <span className="text-2xl font-bold text-gray-800">{bread.current_stock.toLocaleString()}</span>
                          <span className="text-xs text-gray-400">/ 正常水位 {bread.target_stock.toLocaleString()}</span>
                        </div>
                        {/* Bread Bar */}
                        <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${bread.health_status === 'critical' ? 'bg-red-400' :
                              bread.health_status === 'overstock' ? 'bg-orange-400' : 'bg-green-400'
                              }`}
                            style={{ width: `${breadCurrentPercent}%` }}
                          />
                          {/* Markers */}
                          <div className="absolute top-0 bottom-0 w-0.5 bg-red-500" style={{ left: `${breadReorderPercent}%` }} />
                          <div className="absolute top-0 bottom-0 w-0.5 bg-blue-500" style={{ left: `${breadTargetPercent}%` }} />
                        </div>
                        {/* Bar Labels - 固定在兩端避免重疊 */}
                        <div className="flex justify-between text-[10px] mt-1">
                          <span className="text-red-500 font-medium">補貨點 {bread.reorder_point.toLocaleString()}</span>
                          <span className="text-blue-500 font-medium">正常水位 {bread.target_stock.toLocaleString()}</span>
                        </div>
                      </div>

                      {/* Bag Section */}
                      {bag ? (
                        <div className="pt-3 border-t border-gray-100">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <Package className="w-4 h-4 text-blue-500" />
                              <span className="text-sm font-medium text-gray-700">塑膠袋</span>
                            </div>
                            <span
                              className={`text-xs px-2 py-0.5 rounded ${bag.health_status === 'critical' ? 'bg-red-100 text-red-600' :
                                bag.health_status === 'overstock' ? 'bg-orange-100 text-orange-600' : 'bg-green-100 text-green-600'
                                }`}
                            >
                              {bag.health_status === 'critical' ? '急需補貨' : bag.health_status === 'overstock' ? '庫存積壓' : '庫存充足'}
                            </span>
                          </div>
                          <div className="flex items-baseline gap-2 mb-2">
                            <span className="text-2xl font-bold text-gray-800">{bag.current_stock.toLocaleString()}</span>
                            <span className="text-xs text-gray-400">{bag.unit} / 正常水位 {bag.target_stock.toLocaleString()}</span>
                          </div>
                          {/* Bag Bar */}
                          <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${bag.health_status === 'critical' ? 'bg-red-400' :
                                bag.health_status === 'overstock' ? 'bg-orange-400' : 'bg-green-400'
                                }`}
                              style={{ width: `${bagCurrentPercent}%` }}
                            />
                            {/* Markers */}
                            <div className="absolute top-0 bottom-0 w-0.5 bg-red-500" style={{ left: `${bagReorderPercent}%` }} />
                            <div className="absolute top-0 bottom-0 w-0.5 bg-blue-500" style={{ left: `${bagTargetPercent}%` }} />
                          </div>
                          {/* Bar Labels - 固定在兩端避免重疊 */}
                          <div className="flex justify-between text-[10px] mt-1">
                            <span className="text-red-500 font-medium">補貨點 {bag.reorder_point.toLocaleString()}</span>
                            <span className="text-blue-500 font-medium">正常水位 {bag.target_stock.toLocaleString()}</span>
                          </div>
                        </div>
                      ) : (
                        <div className="pt-3 border-t border-gray-100">
                          <div className="flex items-center gap-2 text-gray-400">
                            <Package className="w-4 h-4" />
                            <span className="text-sm">無對應塑膠袋資料</span>
                          </div>
                        </div>
                      )}

                      {bread.stock_by_accept_date && bread.stock_by_accept_date.length > 0 && (
                        <div className="pt-3 border-t border-gray-100">
                          <button
                            onClick={() => {
                              const newExpanded = new Set(expandedItems);
                              if (newExpanded.has(bread.name)) {
                                newExpanded.delete(bread.name);
                              } else {
                                newExpanded.add(bread.name);
                              }
                              setExpandedItems(newExpanded);
                            }}
                            className="flex items-center justify-between w-full text-left"
                          >
                            <div className="flex items-center gap-2">
                              <Calendar className="w-4 h-4 text-gray-500" />
                              <span className="text-sm font-medium text-gray-700">允收日期明細</span>
                              <span className="text-xs text-gray-400">({bread.stock_by_accept_date.length} 筆)</span>
                            </div>
                            <span className="text-gray-400 text-sm">
                              {expandedItems.has(bread.name) ? '收合 ▲' : '展開 ▼'}
                            </span>
                          </button>
                          {expandedItems.has(bread.name) && (
                            <div className="mt-2 space-y-1">
                              {bread.stock_by_accept_date.map((item, idx) => (
                                <div
                                  key={idx}
                                  className={`flex justify-between items-center px-3 py-2 rounded text-sm ${
                                    idx === 0 && item.date !== '未設定'
                                      ? 'bg-amber-50 border border-amber-200'
                                      : 'bg-gray-50'
                                  }`}
                                >
                                  <span className={idx === 0 && item.date !== '未設定' ? 'text-amber-700 font-medium' : 'text-gray-600'}>
                                    {idx === 0 && item.date !== '未設定' && <Clock className="w-3 h-3 inline mr-1" />}
                                    {item.date}
                                  </span>
                                  <span className={idx === 0 && item.date !== '未設定' ? 'text-amber-700 font-bold' : 'text-gray-800 font-medium'}>
                                    {item.stock.toLocaleString()} {bread.unit}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      <div className="mt-3 space-y-1">
                        {bread.health_status === 'critical' && (
                          <div className="flex items-center gap-2 text-xs text-red-600">
                            <AlertTriangle className="w-3 h-3" />
                            <span>麵包庫存不足，距補貨點差 {Math.max(0, bread.reorder_point - bread.current_stock).toLocaleString()} 顆，距正常水位差 {Math.max(0, bread.target_stock - bread.current_stock).toLocaleString()} 顆</span>
                          </div>
                        )}
                        {bread.health_status === 'healthy' && (
                          <div className="flex items-center gap-2 text-xs text-green-600">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>庫存充足，距補貨點還有 {(bread.current_stock - bread.reorder_point).toLocaleString()} 顆</span>
                          </div>
                        )}
                        {bread.health_status === 'overstock' && (
                          <div className="flex items-center gap-2 text-xs text-orange-500">
                            <Box className="w-3 h-3" />
                            <span>庫存積壓，超出正常水位 {(bread.current_stock - bread.target_stock).toLocaleString()} 顆</span>
                          </div>
                        )}
                        {bag?.health_status === 'critical' && (
                          <div className="flex items-center gap-2 text-xs text-red-600">
                            <AlertTriangle className="w-3 h-3" />
                            <span>塑膠袋庫存不足，距補貨點差 {Math.max(0, bag.reorder_point - bag.current_stock).toLocaleString()} {bag.unit}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Box Diagnosis */}
            {boxDiagnoses.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                    <span className="w-1.5 h-6 bg-gray-400 rounded-full"></span>
                    紙箱庫存診斷 ({boxDiagnoses.length})
                  </h2>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    前置期: {LEAD_TIME.box} 天 | 正常水位: {TARGET_DAYS} 天
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {boxDiagnoses.map((item) => {
                    const barMax = Math.max(item.current_stock, item.target_stock) * 1.2;
                    const reorderPercent = (item.reorder_point / barMax) * 100;
                    const targetPercent = (item.target_stock / barMax) * 100;
                    const currentPercent = Math.min((item.current_stock / barMax) * 100, 100);

                    return (
                      <div
                        key={item.name}
                        className="bg-white p-5 rounded-xl shadow-sm hover:shadow-md transition-shadow"
                      >
                        <div className="flex justify-between items-start mb-1">
                          <h3 className="font-bold text-gray-800 text-lg">{item.name}</h3>
                          <span
                            className={`text-xs px-3 py-1 rounded-lg font-medium flex items-center gap-1 ${item.health_status === 'critical'
                              ? 'bg-red-100 text-red-600'
                              : item.health_status === 'overstock'
                                ? 'bg-orange-100 text-orange-600'
                                : 'bg-green-100 text-green-600'
                              }`}
                          >
                            {item.health_status === 'critical' && <AlertTriangle className="w-3 h-3" />}
                            {item.health_status === 'overstock' && <Box className="w-3 h-3" />}
                            {item.health_status === 'healthy' && <CheckCircle2 className="w-3 h-3" />}
                            {item.health_status === 'critical' ? '急需補貨' : item.health_status === 'overstock' ? '庫存積壓' : '水位健康'}
                          </span>
                        </div>

                        <p className="text-sm text-gray-500 mb-4">
                          日銷: {(item.daily_sales ?? 0).toLocaleString()} 個 | 30日銷量: {(item.total_sales_30d ?? 0).toLocaleString()} | 可售天數: <span className={`font-medium ${(item.days_of_stock ?? 0) < LEAD_TIME.box ? 'text-red-600' :
                            (item.days_of_stock ?? 0) > TARGET_DAYS ? 'text-orange-500' : 'text-green-600'
                            }`}>{item.days_of_stock ?? 0} 天</span>
                        </p>

                        <div className="flex items-baseline gap-2 mb-3">
                          <span className="text-3xl font-bold text-gray-800">{item.current_stock.toLocaleString()}</span>
                          <span className="text-sm text-gray-400">/ 正常水位 {item.target_stock.toLocaleString()}</span>
                        </div>

                        <div className="relative mb-2">
                          <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${item.health_status === 'critical' ? 'bg-red-400' :
                                item.health_status === 'overstock' ? 'bg-orange-400' : 'bg-green-400'
                                }`}
                              style={{ width: `${currentPercent}%` }}
                            />
                          </div>
                          {/* Markers */}
                          <div className="absolute top-0 w-0.5 h-3 bg-red-500" style={{ left: `${reorderPercent}%` }} />
                          <div className="absolute top-0 w-0.5 h-3 bg-blue-500" style={{ left: `${targetPercent}%` }} />
                        </div>
                        {/* Bar Labels - 固定在兩端避免重疊 */}
                        <div className="flex justify-between text-[10px] mb-4">
                          <span className="text-red-500 font-medium">補貨點 {item.reorder_point.toLocaleString()}</span>
                          <span className="text-blue-500 font-medium">正常水位 {item.target_stock.toLocaleString()}</span>
                        </div>

                        {item.health_status === 'critical' && (
                          <div className="flex items-center gap-2 text-sm text-red-600">
                            <AlertTriangle className="w-4 h-4" />
                            <span>庫存不足，距離補貨點還差 {Math.max(0, item.reorder_point - item.current_stock).toLocaleString()} 個</span>
                          </div>
                        )}
                        {item.health_status === 'overstock' && (
                          <div className="flex items-center gap-2 text-sm text-orange-500">
                            <Box className="w-4 h-4" />
                            <span>庫存積壓，超出30日銷量 {((item.current_stock ?? 0) - (item.total_sales_30d ?? 0)).toLocaleString()} 個</span>
                          </div>
                        )}
                        {item.health_status === 'healthy' && (
                          <div className="flex items-center gap-2 text-sm text-gray-500">
                            <CheckCircle2 className="w-4 h-4" />
                            <span>庫存正常，距離補貨點還有 {(item.current_stock - item.reorder_point).toLocaleString()} 個</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Standalone Bag Diagnosis (bags without matching bread) */}
            {standaloneBags.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                    <span className="w-1.5 h-6 bg-blue-400 rounded-full"></span>
                    其他塑膠袋 ({standaloneBags.length})
                  </h2>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    前置期: {LEAD_TIME.bag} 天 | 1捲 ≈ {ITEMS_PER_ROLL.toLocaleString()} 個
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {standaloneBags.map((item) => {
                    const barMax = Math.max(item.current_stock, item.target_stock) * 1.2;
                    const reorderPercent = (item.reorder_point / barMax) * 100;
                    const targetPercent = (item.target_stock / barMax) * 100;
                    const currentPercent = Math.min((item.current_stock / barMax) * 100, 100);

                    return (
                      <div
                        key={item.name}
                        className="bg-white p-5 rounded-xl shadow-sm hover:shadow-md transition-shadow"
                      >
                        <div className="flex justify-between items-start mb-1">
                          <h3 className="font-bold text-gray-800 text-lg">{item.name}</h3>
                          <span
                            className={`text-xs px-3 py-1 rounded-lg font-medium flex items-center gap-1 ${item.health_status === 'critical'
                              ? 'bg-red-100 text-red-600'
                              : item.health_status === 'overstock'
                                ? 'bg-orange-100 text-orange-600'
                                : 'bg-green-100 text-green-600'
                              }`}
                          >
                            {item.health_status === 'critical' && <AlertTriangle className="w-3 h-3" />}
                            {item.health_status === 'overstock' && <Box className="w-3 h-3" />}
                            {item.health_status === 'healthy' && <CheckCircle2 className="w-3 h-3" />}
                            {item.health_status === 'critical' ? '急需補貨' : item.health_status === 'overstock' ? '庫存積壓' : '水位健康'}
                          </span>
                        </div>

                        <div className="flex items-baseline gap-2 mb-3">
                          <span className="text-3xl font-bold text-gray-800">{item.current_stock.toLocaleString()}</span>
                          <span className="text-sm text-gray-400">{item.unit} / 正常水位 {item.target_stock.toLocaleString()} {item.unit}</span>
                        </div>

                        <div className="relative mb-2">
                          <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${item.health_status === 'critical' ? 'bg-red-400' :
                                item.health_status === 'overstock' ? 'bg-orange-400' : 'bg-green-400'
                                }`}
                              style={{ width: `${currentPercent}%` }}
                            />
                          </div>
                          {/* Markers */}
                          <div className="absolute top-0 w-0.5 h-3 bg-red-500" style={{ left: `${reorderPercent}%` }} />
                          <div className="absolute top-0 w-0.5 h-3 bg-blue-500" style={{ left: `${targetPercent}%` }} />
                        </div>
                        {/* Bar Labels - 固定在兩端避免重疊 */}
                        <div className="flex justify-between text-[10px] mb-4">
                          <span className="text-red-500 font-medium">補貨點 {item.reorder_point.toLocaleString()}</span>
                          <span className="text-blue-500 font-medium">正常水位 {item.target_stock.toLocaleString()}</span>
                        </div>

                        {item.health_status === 'critical' && (
                          <div className="flex items-center gap-2 text-sm text-red-600">
                            <AlertTriangle className="w-4 h-4" />
                            <span>庫存不足，距補貨點差 {Math.max(0, item.reorder_point - item.current_stock).toLocaleString()} {item.unit}</span>
                          </div>
                        )}
                        {item.health_status === 'overstock' && (
                          <div className="flex items-center gap-2 text-sm text-orange-500">
                            <Box className="w-4 h-4" />
                            <span>庫存積壓，超出正常水位 {(item.current_stock - item.target_stock).toLocaleString()} {item.unit}</span>
                          </div>
                        )}
                        {item.health_status === 'healthy' && (
                          <div className="flex items-center gap-2 text-sm text-gray-500">
                            <CheckCircle2 className="w-4 h-4" />
                            <span>庫存正常，距補貨點還有 {(item.current_stock - item.reorder_point).toLocaleString()} {item.unit}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab Content: Order Suggestions */}
        {activeTab === 'order' && (
          <div className="space-y-4 sm:space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-base sm:text-lg font-bold text-gray-800">
                叫貨建議表 {orderSuggestions.length > 0 && `(${orderSuggestions.length} 項需要叫貨)`}
              </h2>
            </div>

            {orderSuggestions.length === 0 ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 sm:p-12 text-center">
                <CheckCircle2 className="w-10 h-10 sm:w-12 sm:h-12 text-green-400 mx-auto mb-3 sm:mb-4" />
                <p className="text-sm sm:text-base text-gray-600 font-medium">目前沒有急需叫貨的商品</p>
                <p className="text-xs sm:text-sm text-gray-400 mt-1">所有商品庫存都在安全水位以上</p>
              </div>
            ) : (
              <>
                {/* Mobile: Card layout */}
                <div className="sm:hidden space-y-3">
                  {orderSuggestions.map((item, idx) => (
                    <div key={item.name} className={`bg-white rounded-lg shadow-sm border border-gray-100 p-3 ${idx < 3 ? 'border-l-4 border-l-red-500' : ''}`}>
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-gray-800 text-sm truncate">{item.name}</h3>
                          <span className="text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                            {item.category === 'bread' ? '麵包' : item.category === 'box' ? '紙箱' : '塑膠袋'}
                          </span>
                        </div>
                        {item.category === 'bag' ? (
                          item.current_stock < item.reorder_point ? (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 text-red-700 rounded-full text-[10px] font-medium">
                              <XCircle className="w-2.5 h-2.5" />緊急
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded-full text-[10px] font-medium">
                              <AlertTriangle className="w-2.5 h-2.5" />注意
                            </span>
                          )
                        ) : (
                          (item.days_of_stock ?? 0) < 10 ? (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 text-red-700 rounded-full text-[10px] font-medium">
                              <XCircle className="w-2.5 h-2.5" />緊急
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded-full text-[10px] font-medium">
                              <AlertTriangle className="w-2.5 h-2.5" />注意
                            </span>
                          )
                        )}
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <p className="text-gray-400 text-[10px]">目前庫存</p>
                          <p className="font-medium text-gray-800">{item.current_stock.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-gray-400 text-[10px]">可售天數</p>
                          <p className={`font-bold ${(item.days_of_stock ?? 0) < 10 ? 'text-red-600' : 'text-orange-500'}`}>
                            {item.category === 'bag' ? '-' : `${item.days_of_stock ?? 0} 天`}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-400 text-[10px]">建議叫貨</p>
                          <p className="font-bold text-[#EB5C20]">+{item.suggested_order.toLocaleString()}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Desktop: Table layout */}
                <div className="hidden sm:block bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-red-50 text-red-700 font-medium">
                      <tr>
                        <th className="px-4 lg:px-6 py-3 lg:py-4">商品名稱</th>
                        <th className="px-4 lg:px-6 py-3 lg:py-4">分類</th>
                        <th className="px-4 lg:px-6 py-3 lg:py-4 text-right">目前庫存</th>
                        <th className="px-4 lg:px-6 py-3 lg:py-4 text-right">日銷量</th>
                        <th className="px-4 lg:px-6 py-3 lg:py-4 text-right">可售天數</th>
                        <th className="px-4 lg:px-6 py-3 lg:py-4 text-right">補貨點</th>
                        <th className="px-4 lg:px-6 py-3 lg:py-4 text-right">建議叫貨量</th>
                        <th className="px-4 lg:px-6 py-3 lg:py-4 text-center">緊急程度</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {orderSuggestions.map((item, idx) => (
                        <tr key={item.name} className={`hover:bg-gray-50 ${idx < 3 ? 'bg-red-50/30' : ''}`}>
                          <td className="px-4 lg:px-6 py-3 lg:py-4 font-medium text-gray-800">{item.name}</td>
                          <td className="px-4 lg:px-6 py-3 lg:py-4 text-gray-600">
                            <span className="bg-gray-100 px-2 py-1 rounded text-xs">
                              {item.category === 'bread' ? '麵包' : item.category === 'box' ? '紙箱' : '塑膠袋'}
                            </span>
                          </td>
                          <td className="px-4 lg:px-6 py-3 lg:py-4 text-right text-gray-800">
                            {item.current_stock.toLocaleString()}
                          </td>
                          <td className="px-4 lg:px-6 py-3 lg:py-4 text-right text-gray-600">
                            {item.category === 'bag' ? '-' : (item.daily_sales ?? 0).toLocaleString()}
                          </td>
                          <td className={`px-4 lg:px-6 py-3 lg:py-4 text-right font-bold ${item.category === 'bag' ? 'text-gray-500' :
                            (item.days_of_stock ?? 0) < 10 ? 'text-red-600' : 'text-orange-500'
                            }`}>
                            {item.category === 'bag' ? '-' : `${item.days_of_stock ?? 0} 天`}
                          </td>
                          <td className="px-4 lg:px-6 py-3 lg:py-4 text-right text-gray-500">
                            {item.reorder_point.toLocaleString()}
                          </td>
                          <td className="px-4 lg:px-6 py-3 lg:py-4 text-right font-bold text-[#EB5C20]">
                            +{item.suggested_order.toLocaleString()} {item.unit}
                          </td>
                          <td className="px-4 lg:px-6 py-3 lg:py-4 text-center">
                            {item.category === 'bag' ? (
                              item.current_stock < item.reorder_point ? (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                                  <XCircle className="w-3 h-3" />
                                  緊急
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-medium">
                                  <AlertTriangle className="w-3 h-3" />
                                  注意
                                </span>
                              )
                            ) : (
                              (item.days_of_stock ?? 0) < 10 ? (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                                  <XCircle className="w-3 h-3" />
                                  緊急
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-medium">
                                  <AlertTriangle className="w-3 h-3" />
                                  注意
                                </span>
                              )
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <h4 className="font-bold text-blue-700 text-sm">叫貨邏輯說明</h4>
                <p className="text-sm text-blue-600 mt-1">
                  當庫存可售天數低於前置期（麵包/紙箱 {LEAD_TIME.bread} 天，塑膠袋 {LEAD_TIME.bag} 天）時，系統會建議叫貨。
                  建議叫貨量 = 正常水位 ({TARGET_DAYS} 天銷量) - 目前庫存。
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content: Inventory */}
        {activeTab === 'inventory' && (
          <div className="space-y-8">
            {/* Search Filter */}
            <div className="flex items-center gap-4 bg-white p-4 rounded-lg shadow-sm border border-gray-100">
              <Search className="text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="搜尋商品名稱..."
                className="flex-1 outline-none text-gray-700 placeholder-gray-400"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {/* Section 1: Breads */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-[#EB5C20] rounded-full"></span>
                  麵包庫存 ({breadItems.length})
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {breadItems.map((item) => (
                  <div
                    key={item.id}
                    className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-gray-800 text-sm">{item.name}</h3>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${item.stockStatus === 'low'
                          ? 'bg-red-100 text-red-600'
                          : item.stockStatus === 'medium'
                            ? 'bg-yellow-100 text-yellow-600'
                            : 'bg-green-100 text-green-600'
                          }`}
                      >
                        {item.stockStatus === 'low' ? '低庫存' : item.stockStatus === 'medium' ? '正常' : '充足'}
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-[#EB5C20]">
                      {item.stock.toLocaleString()}{' '}
                      <span className="text-xs text-gray-400 font-normal">{item.unit || '個'}</span>
                    </div>
                    <StockLevelBar current={item.stock} max={item.minStock * 3} lowThreshold={item.minStock} />
                    <div className="mt-3 text-xs text-gray-400 text-right">
                      <span>可用量: {item.availableStock.toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Section 2: Consumables (Boxes & Bags) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Boxes */}
              <div className="lg:col-span-1">
                <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2 mb-4">
                  <span className="w-1.5 h-6 bg-[#9FA0A0] rounded-full"></span>
                  紙箱庫存
                </h2>
                <div className="space-y-4">
                  {boxItems.map((item) => (
                    <div
                      key={item.id}
                      className="bg-white p-4 rounded-xl shadow-sm border border-gray-100"
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-gray-700">{item.name}</span>
                        <span className="text-xl font-bold text-gray-800">
                          {item.stock.toLocaleString()}
                        </span>
                      </div>
                      <StockLevelBar current={item.stock} max={item.minStock * 3 || 6000} lowThreshold={item.minStock || 500} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Bags - using diagnosis data for unified status calculation */}
              <div className="lg:col-span-2">
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                    <span className="w-1.5 h-6 bg-blue-400 rounded-full"></span>
                    塑膠袋庫存 ({bagDiagnoses.length})
                  </h2>
                  <span className="text-xs text-gray-500 bg-blue-50 text-blue-600 px-2 py-1 rounded border border-blue-100">
                    1 捲 ≈ 6,000 個袋子
                  </span>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="bg-gray-50 text-gray-500 font-medium">
                        <tr>
                          <th className="px-6 py-3">品項名稱</th>
                          <th className="px-6 py-3 text-right">目前庫存 (捲)</th>
                          <th className="px-6 py-3 text-right">可包裝量 (約)</th>
                          <th className="px-6 py-3 text-right">狀態</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {bagDiagnoses.map((bag) => (
                          <tr key={bag.name} className="hover:bg-gray-50">
                            <td className="px-6 py-3 font-medium text-gray-700">{bag.name}</td>
                            <td className="px-6 py-3 text-right font-bold text-gray-800">
                              {bag.current_stock.toLocaleString()} {bag.unit || '捲'}
                            </td>
                            <td className="px-6 py-3 text-right text-gray-500">
                              {(bag.current_stock * 6000).toLocaleString()} 個
                            </td>
                            <td className="px-6 py-3 text-right">
                              <span
                                className={`text-xs px-2 py-0.5 rounded-full ${bag.health_status === 'critical'
                                  ? 'bg-red-100 text-red-600'
                                  : bag.health_status === 'overstock'
                                    ? 'bg-yellow-100 text-yellow-600'
                                    : 'bg-green-100 text-green-600'
                                  }`}
                              >
                                {bag.health_status === 'critical' ? '急需補貨' : bag.health_status === 'overstock' ? '庫存積壓' : '庫存充足'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content: Analysis */}
        {activeTab === 'analysis' && (
          <div className="space-y-4 sm:space-y-6">
            {/* Controls */}
            <div className="bg-white p-3 sm:p-4 rounded-xl shadow-sm border border-gray-100">
              <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-3 sm:gap-4">
                {/* Mode selector: Sales vs Stock */}
                <div className="flex items-center gap-2">
                  <span className="text-xs sm:text-sm text-gray-600 whitespace-nowrap">分析類型:</span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => {
                        setAnalysisMode('sales');
                        if (salesTrendData.length === 0) fetchSalesTrend('bread');
                      }}
                      className={`px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm rounded-lg transition-colors ${analysisMode === 'sales'
                        ? 'bg-[#EB5C20] text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                    >
                      銷量趨勢
                    </button>
                    <button
                      onClick={() => {
                        setAnalysisMode('stock');
                        if (trendData.length === 0) fetchTrendData('bread');
                      }}
                      className={`px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm rounded-lg transition-colors ${analysisMode === 'stock'
                        ? 'bg-[#EB5C20] text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                    >
                      庫存趨勢
                    </button>
                  </div>
                </div>

                {/* Days selector */}
                <div className="flex items-center gap-2">
                  <span className="text-xs sm:text-sm text-gray-600 whitespace-nowrap">時間範圍:</span>
                  <div className="flex gap-1">
                    {[7, 14, 30].map((days) => (
                      <button
                        key={days}
                        onClick={() => setTrendDays(days)}
                        className={`px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm rounded-lg transition-colors ${trendDays === days
                          ? 'bg-[#EB5C20] text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                          }`}
                      >
                        {days}天
                      </button>
                    ))}
                  </div>
                </div>

                {/* Select/Deselect All buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={analysisMode === 'sales' ? selectAllSalesItems : selectAllTrendItems}
                    className="px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
                  >
                    全選
                  </button>
                  <button
                    onClick={analysisMode === 'sales' ? deselectAllSalesItems : deselectAllTrendItems}
                    className="px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    取消全選
                  </button>
                </div>

                {/* Refresh button */}
                <button
                  onClick={() => analysisMode === 'sales' ? fetchSalesTrend('bread') : fetchTrendData('bread')}
                  className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  <span className="hidden sm:inline">重新整理</span>
                </button>
              </div>

              {/* Selected count */}
              <div className="mt-2 sm:mt-3 text-xs sm:text-sm text-gray-500">
                已選擇: {analysisMode === 'sales' ? selectedSalesItems.size : selectedTrendItems.size} / {analysisMode === 'sales' ? salesTrendData.length : trendData.length} 項
              </div>
            </div>

            {/* Sales Trend Chart - Multi-line */}
            {analysisMode === 'sales' && (
              <div className="bg-white p-3 sm:p-6 rounded-xl shadow-sm border border-gray-100">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 sm:mb-6">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <h3 className="text-sm sm:text-lg font-bold text-gray-800">
                      銷量趨勢圖 (出庫量)
                    </h3>
                    {focusedItem && (
                      <button
                        onClick={() => setFocusedItem(null)}
                        className="text-[10px] sm:text-xs px-1.5 sm:px-2 py-0.5 sm:py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                      >
                        清除聚焦
                      </button>
                    )}
                  </div>
                  <span className="text-[10px] sm:text-xs text-gray-500 bg-gray-100 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded self-start sm:self-auto">
                    近 {trendDays} 天資料
                  </span>
                </div>

                {analysisLoading ? (
                  <div className="h-64 sm:h-96 flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <Loader2 className="w-8 h-8 sm:w-12 sm:h-12 mx-auto mb-2 animate-spin text-[#EB5C20]" />
                      <p className="text-sm sm:text-base">載入銷量資料中...</p>
                    </div>
                  </div>
                ) : salesTrendData.length === 0 ? (
                  <div className="h-64 sm:h-96 flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <TrendingUp className="w-8 h-8 sm:w-12 sm:h-12 mx-auto mb-2 opacity-50" />
                      <p className="text-sm sm:text-base">無銷量資料</p>
                    </div>
                  </div>
                ) : selectedSalesItems.size === 0 ? (
                  <div className="h-64 sm:h-96 flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <TrendingUp className="w-8 h-8 sm:w-12 sm:h-12 mx-auto mb-2 opacity-50" />
                      <p className="text-sm sm:text-base">請在下方表格選擇要顯示的品項</p>
                    </div>
                  </div>
                ) : (
                  <div className="h-64 sm:h-96 w-full relative">
                    {/* Focused item info panel - hidden on mobile, shown on desktop */}
                    {focusedItem && (
                      <div className="hidden sm:block absolute top-2 right-2 bg-white p-3 rounded-lg shadow-lg border border-gray-200 z-10 min-w-[200px]">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-4 h-4 rounded-full flex-shrink-0"
                            style={{ backgroundColor: CHART_COLORS[salesTrendData.findIndex(i => i.name === focusedItem) % CHART_COLORS.length] }}
                          />
                          <span className="font-bold text-gray-800">{focusedItem}</span>
                        </div>
                        {salesStats[String(trendDays)]?.[focusedItem] && (
                          <div className="mt-2 text-xs text-gray-500 space-y-1">
                            <div>總銷量: {salesStats[String(trendDays)][focusedItem].total.toLocaleString()}</div>
                            <div>日均: {salesStats[String(trendDays)][focusedItem].avg.toLocaleString()}</div>
                            <div>最高: {salesStats[String(trendDays)][focusedItem].max.toLocaleString()}</div>
                          </div>
                        )}
                      </div>
                    )}
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={(() => {
                          // Calculate date cutoff based on trendDays
                          const cutoffDate = new Date();
                          cutoffDate.setDate(cutoffDate.getDate() - trendDays);
                          const cutoffStr = cutoffDate.toISOString().slice(0, 10);

                          // Merge all selected items data by date, filtered by trendDays
                          // Use full date (YYYY-MM-DD) as key for correct cross-year sorting
                          const dateMap = new Map<string, Record<string, string | number>>();
                          salesTrendData
                            .filter(item => selectedSalesItems.has(item.name))
                            .forEach(item => {
                              item.data
                                .filter(d => d.date >= cutoffStr)
                                .forEach(d => {
                                  const fullDate = d.date; // YYYY-MM-DD for sorting
                                  const displayDate = d.date.slice(5); // MM-DD for display
                                  if (!dateMap.has(fullDate)) {
                                    dateMap.set(fullDate, { date: displayDate, _sortKey: fullDate });
                                  }
                                  dateMap.get(fullDate)![item.name] = d.sales;
                                });
                            });
                          // Sort by full date, then remove sort key
                          return Array.from(dateMap.values())
                            .sort((a, b) => String(a._sortKey).localeCompare(String(b._sortKey)))
                            .map(({ _sortKey, ...rest }) => rest);
                        })()}
                        margin={{ top: 20, right: 20, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 11 }} tickMargin={10} />
                        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => v.toLocaleString()} />
                        <RechartsTooltip
                          contentStyle={{
                            borderRadius: '8px',
                            border: 'none',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                            padding: '8px 12px'
                          }}
                          labelStyle={{ fontWeight: 'bold', marginBottom: '4px' }}
                        />
                        {salesTrendData
                          .filter(item => selectedSalesItems.has(item.name))
                          .map((item, idx) => (
                            <Line
                              key={item.name}
                              type="monotone"
                              dataKey={item.name}
                              stroke={CHART_COLORS[idx % CHART_COLORS.length]}
                              strokeWidth={focusedItem === item.name ? 4 : (focusedItem ? 1 : 2)}
                              strokeOpacity={focusedItem && focusedItem !== item.name ? 0.2 : 1}
                              dot={false}
                              activeDot={{ r: 6, strokeWidth: 2, stroke: '#fff' }}
                            />
                          ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}

            {/* Stock Trend Chart - Multi-line */}
            {analysisMode === 'stock' && (
              <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-bold text-gray-800">
                      庫存趨勢圖 (預計可用量)
                    </h3>
                    {focusedItem && (
                      <button
                        onClick={() => setFocusedItem(null)}
                        className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                      >
                        清除聚焦
                      </button>
                    )}
                  </div>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    近 {trendDays} 天資料
                  </span>
                </div>

                {analysisLoading ? (
                  <div className="h-96 flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <Loader2 className="w-12 h-12 mx-auto mb-2 animate-spin text-[#EB5C20]" />
                      <p>載入趨勢資料中...</p>
                    </div>
                  </div>
                ) : trendData.length === 0 ? (
                  <div className="h-96 flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>無庫存趨勢資料</p>
                    </div>
                  </div>
                ) : selectedTrendItems.size === 0 ? (
                  <div className="h-96 flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>請在下方表格選擇要顯示的品項</p>
                    </div>
                  </div>
                ) : (
                  <div className="h-96 w-full relative">
                    {/* Focused item info panel */}
                    {focusedItem && (
                      <div className="absolute top-2 right-2 bg-white p-3 rounded-lg shadow-lg border border-gray-200 z-10 min-w-[200px]">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-4 h-4 rounded-full flex-shrink-0"
                            style={{ backgroundColor: CHART_COLORS[trendData.findIndex(i => i.name === focusedItem) % CHART_COLORS.length] }}
                          />
                          <span className="font-bold text-gray-800">{focusedItem}</span>
                        </div>
                        {stockStats[String(trendDays)]?.[focusedItem] && (
                          <div className="mt-2 text-xs text-gray-500 space-y-1">
                            <div>目前庫存: {stockStats[String(trendDays)][focusedItem].latest.toLocaleString()}</div>
                            <div>{trendDays}天前: {stockStats[String(trendDays)][focusedItem].oldest.toLocaleString()}</div>
                            <div>變化: {stockStats[String(trendDays)][focusedItem].change > 0 ? '+' : ''}{stockStats[String(trendDays)][focusedItem].change.toLocaleString()}</div>
                          </div>
                        )}
                      </div>
                    )}
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={(() => {
                          // Calculate date cutoff based on trendDays
                          const cutoffDate = new Date();
                          cutoffDate.setDate(cutoffDate.getDate() - trendDays);
                          const cutoffStr = cutoffDate.toISOString().slice(0, 10);

                          // Merge all selected items data by date, filtered by trendDays
                          // Use full date (YYYY-MM-DD) as key for correct cross-year sorting
                          const dateMap = new Map<string, Record<string, string | number>>();
                          trendData
                            .filter(item => selectedTrendItems.has(item.name))
                            .forEach(item => {
                              item.data
                                .filter(d => d.date >= cutoffStr)
                                .forEach(d => {
                                  const fullDate = d.date; // YYYY-MM-DD for sorting
                                  const displayDate = d.date.slice(5); // MM-DD for display
                                  if (!dateMap.has(fullDate)) {
                                    dateMap.set(fullDate, { date: displayDate, _sortKey: fullDate });
                                  }
                                  dateMap.get(fullDate)![item.name] = d.stock;
                                });
                            });
                          // Sort by full date, then remove sort key
                          return Array.from(dateMap.values())
                            .sort((a, b) => String(a._sortKey).localeCompare(String(b._sortKey)))
                            .map(({ _sortKey, ...rest }) => rest);
                        })()}
                        margin={{ top: 20, right: 20, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 11 }} tickMargin={10} />
                        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => v.toLocaleString()} />
                        <RechartsTooltip
                          contentStyle={{
                            borderRadius: '8px',
                            border: 'none',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                            padding: '8px 12px'
                          }}
                          labelStyle={{ fontWeight: 'bold', marginBottom: '4px' }}
                        />
                        {trendData
                          .filter(item => selectedTrendItems.has(item.name))
                          .map((item, idx) => (
                            <Line
                              key={item.name}
                              type="monotone"
                              dataKey={item.name}
                              stroke={CHART_COLORS[idx % CHART_COLORS.length]}
                              strokeWidth={focusedItem === item.name ? 4 : (focusedItem ? 1 : 2)}
                              strokeOpacity={focusedItem && focusedItem !== item.name ? 0.2 : 1}
                              dot={false}
                              activeDot={{ r: 6, strokeWidth: 2, stroke: '#fff' }}
                            />
                          ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}

            {/* Sales Table with checkboxes */}
            {analysisMode === 'sales' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100">
                  <h3 className="font-bold text-gray-800">各品項銷量統計 (出庫量) - 點擊顏色圓點可聚焦該品項</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-gray-50 text-gray-500 font-medium">
                      <tr>
                        <th className="px-4 py-3 w-10">
                          <input
                            type="checkbox"
                            checked={selectedSalesItems.size === salesTrendData.length}
                            onChange={(e) => e.target.checked ? selectAllSalesItems() : deselectAllSalesItems()}
                            className="w-4 h-4 rounded border-gray-300 text-[#EB5C20] focus:ring-[#EB5C20]"
                          />
                        </th>
                        <th className="px-4 py-3">商品名稱</th>
                        <th className="px-4 py-3 text-right">{trendDays}天總銷量</th>
                        <th className="px-4 py-3 text-right">日均銷量</th>
                        <th className="px-4 py-3 text-right">最高日銷量</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {salesTrendData
                        .map((item) => {
                          // Use backend-calculated stats for current period
                          const stats = salesStats[String(trendDays)]?.[item.name];
                          return {
                            ...item,
                            totalSales: stats?.total ?? 0,
                            avgSales: stats?.avg ?? 0,
                            maxSales: stats?.max ?? 0,
                          };
                        })
                        .sort((a, b) => b.totalSales - a.totalSales)
                        .map((item) => {
                          const isSelected = selectedSalesItems.has(item.name);
                          const isFocused = focusedItem === item.name;
                          const colorIdx = salesTrendData.findIndex(i => i.name === item.name);
                          return (
                            <tr
                              key={item.name}
                              className={`hover:bg-gray-50 cursor-pointer ${isFocused ? 'bg-orange-100' : isSelected ? 'bg-green-50' : ''}`}
                              onClick={() => toggleSalesItem(item.name)}
                            >
                              <td className="px-4 py-3">
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleSalesItem(item.name)}
                                  onClick={(e) => e.stopPropagation()}
                                  className="w-4 h-4 rounded border-gray-300 text-[#EB5C20] focus:ring-[#EB5C20]"
                                />
                              </td>
                              <td className="px-4 py-3 font-medium text-gray-700">
                                <div className="flex items-center gap-2">
                                  {isSelected && (
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setFocusedItem(isFocused ? null : item.name);
                                      }}
                                      className={`w-4 h-4 rounded-full flex-shrink-0 transition-transform ${isFocused ? 'ring-2 ring-offset-1 ring-gray-400 scale-125' : 'hover:scale-110'}`}
                                      style={{ backgroundColor: CHART_COLORS[colorIdx % CHART_COLORS.length] }}
                                      title={isFocused ? '取消聚焦' : '點擊聚焦此品項'}
                                    />
                                  )}
                                  <span className={isFocused ? 'font-bold' : ''}>{item.name}</span>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-right font-bold text-gray-900">
                                {item.totalSales.toLocaleString()}
                              </td>
                              <td className="px-4 py-3 text-right text-gray-600">
                                {item.avgSales.toLocaleString()}
                              </td>
                              <td className="px-4 py-3 text-right text-green-600 font-medium">
                                {item.maxSales.toLocaleString()}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Stock Table with checkboxes */}
            {analysisMode === 'stock' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100">
                  <h3 className="font-bold text-gray-800">各品項庫存走勢 (預計可用量) - 點擊顏色圓點可聚焦該品項</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-gray-50 text-gray-500 font-medium">
                      <tr>
                        <th className="px-4 py-3 w-10">
                          <input
                            type="checkbox"
                            checked={selectedTrendItems.size === trendData.length}
                            onChange={(e) => e.target.checked ? selectAllTrendItems() : deselectAllTrendItems()}
                            className="w-4 h-4 rounded border-gray-300 text-[#EB5C20] focus:ring-[#EB5C20]"
                          />
                        </th>
                        <th className="px-4 py-3">商品名稱</th>
                        <th className="px-4 py-3 text-right">目前庫存</th>
                        <th className="px-4 py-3 text-right">{trendDays}天前庫存</th>
                        <th className="px-4 py-3 text-right">變化量</th>
                        <th className="px-4 py-3 text-right">趨勢</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {trendData.map((item) => {
                        // Use backend-calculated stats for current period
                        const stats = stockStats[String(trendDays)]?.[item.name];
                        const latestStock = stats?.latest ?? 0;
                        const oldestStock = stats?.oldest ?? 0;
                        const change = stats?.change ?? 0;
                        const changePercent = oldestStock > 0 ? ((change / oldestStock) * 100).toFixed(1) : 0;
                        const isSelected = selectedTrendItems.has(item.name);
                        const isFocused = focusedItem === item.name;
                        const colorIdx = trendData.findIndex(i => i.name === item.name);

                        return (
                          <tr
                            key={item.name}
                            className={`hover:bg-gray-50 cursor-pointer ${isFocused ? 'bg-orange-100' : isSelected ? 'bg-orange-50' : ''}`}
                            onClick={() => toggleTrendItem(item.name)}
                          >
                            <td className="px-4 py-3">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleTrendItem(item.name)}
                                onClick={(e) => e.stopPropagation()}
                                className="w-4 h-4 rounded border-gray-300 text-[#EB5C20] focus:ring-[#EB5C20]"
                              />
                            </td>
                            <td className="px-4 py-3 font-medium text-gray-700">
                              <div className="flex items-center gap-2">
                                {isSelected && (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setFocusedItem(isFocused ? null : item.name);
                                    }}
                                    className={`w-4 h-4 rounded-full flex-shrink-0 transition-transform ${isFocused ? 'ring-2 ring-offset-1 ring-gray-400 scale-125' : 'hover:scale-110'}`}
                                    style={{ backgroundColor: CHART_COLORS[colorIdx % CHART_COLORS.length] }}
                                    title={isFocused ? '取消聚焦' : '點擊聚焦此品項'}
                                  />
                                )}
                                <span className={isFocused ? 'font-bold' : ''}>{item.name}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-right font-bold text-gray-900">
                              {latestStock.toLocaleString()}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-500">
                              {oldestStock.toLocaleString()}
                            </td>
                            <td className={`px-4 py-3 text-right font-bold ${change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-500'
                              }`}>
                              {change > 0 ? '+' : ''}{change.toLocaleString()}
                              <span className="text-xs font-normal ml-1">({changePercent}%)</span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              {change > 0 ? (
                                <span className="inline-flex items-center text-green-600">
                                  <ArrowUpRight className="w-4 h-4" />
                                  補貨
                                </span>
                              ) : change < 0 ? (
                                <span className="inline-flex items-center text-red-600">
                                  <TrendingUp className="w-4 h-4 rotate-180" />
                                  消耗
                                </span>
                              ) : (
                                <span className="text-gray-400">持平</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab Content: Restock Log */}
        {activeTab === 'restock' && (
          <div className="space-y-4 sm:space-y-6">
            {/* Filters */}
            <div className="bg-white p-3 sm:p-4 rounded-xl shadow-sm border border-gray-100">
              <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-end gap-3 sm:gap-4">
                {/* Product filter */}
                <div className="flex-1 min-w-0 sm:min-w-[200px]">
                  <label className="block text-xs sm:text-sm text-gray-600 mb-1">品項搜尋</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="輸入品項名稱..."
                      value={restockProductFilter}
                      onChange={(e) => setRestockProductFilter(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#EB5C20] focus:border-transparent"
                    />
                  </div>
                </div>

                {/* Date filters - inline on mobile */}
                <div className="flex gap-2 sm:gap-4">
                  {/* Date from */}
                  <div className="flex-1 sm:flex-none">
                    <label className="block text-xs sm:text-sm text-gray-600 mb-1">起始日期</label>
                    <input
                      type="date"
                      value={restockDateFrom}
                      onChange={(e) => setRestockDateFrom(e.target.value)}
                      className="w-full sm:w-auto px-2 sm:px-3 py-2 border border-gray-200 rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-[#EB5C20] focus:border-transparent"
                    />
                  </div>

                  {/* Date to */}
                  <div className="flex-1 sm:flex-none">
                    <label className="block text-xs sm:text-sm text-gray-600 mb-1">結束日期</label>
                    <input
                      type="date"
                      value={restockDateTo}
                      onChange={(e) => setRestockDateTo(e.target.value)}
                      className="w-full sm:w-auto px-2 sm:px-3 py-2 border border-gray-200 rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-[#EB5C20] focus:border-transparent"
                    />
                  </div>
                </div>

                {/* Clear filters */}
                {(restockProductFilter || restockDateFrom || restockDateTo) && (
                  <button
                    onClick={() => {
                      setRestockProductFilter('');
                      setRestockDateFrom('');
                      setRestockDateTo('');
                    }}
                    className="px-3 py-2 text-xs sm:text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors self-end"
                  >
                    清除篩選
                  </button>
                )}

              </div>

              {/* Filter summary */}
              <div className="mt-2 sm:mt-3 text-xs sm:text-sm text-gray-500">
                {(() => {
                  const filteredLogs = restockLogs.filter(log => {
                    if (restockProductFilter && !log.product_name.toLowerCase().includes(restockProductFilter.toLowerCase())) {
                      return false;
                    }
                    if (restockDateFrom && log.date && log.date < restockDateFrom) {
                      return false;
                    }
                    if (restockDateTo && log.date && log.date > restockDateTo) {
                      return false;
                    }
                    return true;
                  });
                  return `顯示 ${filteredLogs.length} 筆紀錄`;
                })()}
              </div>
            </div>

            {restockLogs.length === 0 ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 sm:p-12 text-center">
                <ClipboardList className="w-10 h-10 sm:w-12 sm:h-12 text-gray-300 mx-auto mb-3 sm:mb-4" />
                <p className="text-sm sm:text-base text-gray-500">尚無入庫紀錄</p>
                <p className="text-xs sm:text-sm text-gray-400 mt-1">當有進貨入庫時，紀錄會顯示在這裡</p>
              </div>
            ) : (
              <>
                {/* Mobile: Card layout */}
                <div className="sm:hidden space-y-3">
                  {restockLogs
                    .filter(log => {
                      if (restockProductFilter && !log.product_name.toLowerCase().includes(restockProductFilter.toLowerCase())) {
                        return false;
                      }
                      if (restockDateFrom && log.date && log.date < restockDateFrom) {
                        return false;
                      }
                      if (restockDateTo && log.date && log.date > restockDateTo) {
                        return false;
                      }
                      return true;
                    })
                    .map((log, idx) => (
                      <div key={`${log.date}-${log.product_name}-${idx}`} className="bg-white rounded-lg shadow-sm border border-gray-100 p-3">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium text-gray-800 text-sm truncate">{log.product_name}</h3>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                                {log.category === 'bread' ? '麵包' : log.category === 'box' ? '紙箱' : '袋子'}
                              </span>
                              <span className="text-[10px] text-gray-400 flex items-center gap-1">
                                <Calendar className="w-3 h-3" />
                                {log.date ? new Date(log.date).toLocaleDateString('zh-TW') : '-'}
                              </span>
                            </div>
                          </div>
                          <span className="font-bold text-green-600 text-sm">+{log.stock_in.toLocaleString()}</span>
                        </div>
                        <div className="flex gap-4 text-[10px] text-gray-400">
                          <span>效期: {log.expiry_date || '-'}</span>
                          <span>入倉: {log.warehouse_date || '-'}</span>
                        </div>
                      </div>
                    ))}
                </div>

                {/* Desktop: Table layout */}
                <div className="hidden sm:block bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-gray-50 text-gray-500 font-medium">
                      <tr>
                        <th className="px-4 lg:px-6 py-3">資料日期</th>
                        <th className="px-4 lg:px-6 py-3">品項</th>
                        <th className="px-4 lg:px-6 py-3">分類</th>
                        <th className="px-4 lg:px-6 py-3 text-right">入庫數量</th>
                        <th className="px-4 lg:px-6 py-3 text-right">效期</th>
                        <th className="px-4 lg:px-6 py-3 text-right">入倉日期</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {restockLogs
                        .filter(log => {
                          if (restockProductFilter && !log.product_name.toLowerCase().includes(restockProductFilter.toLowerCase())) {
                            return false;
                          }
                          if (restockDateFrom && log.date && log.date < restockDateFrom) {
                            return false;
                          }
                          if (restockDateTo && log.date && log.date > restockDateTo) {
                            return false;
                          }
                          return true;
                        })
                        .map((log, idx) => (
                          <tr key={`${log.date}-${log.product_name}-${idx}`} className="hover:bg-gray-50">
                            <td className="px-4 lg:px-6 py-3 lg:py-4 text-gray-600">
                              <div className="flex items-center gap-2">
                                <Calendar className="w-4 h-4 text-gray-400" />
                                {log.date ? new Date(log.date).toLocaleDateString('zh-TW') : '-'}
                              </div>
                            </td>
                            <td className="px-4 lg:px-6 py-3 lg:py-4 font-medium text-gray-800">{log.product_name}</td>
                            <td className="px-4 lg:px-6 py-3 lg:py-4 text-gray-600">
                              <span className="bg-gray-100 px-2 py-1 rounded text-xs">
                                {log.category === 'bread' ? '麵包' : log.category === 'box' ? '紙箱' : '袋子'}
                              </span>
                            </td>
                            <td className="px-4 lg:px-6 py-3 lg:py-4 text-right font-bold text-green-600">
                              +{log.stock_in.toLocaleString()}
                            </td>
                            <td className="px-4 lg:px-6 py-3 lg:py-4 text-right text-gray-500">
                              {log.expiry_date || '-'}
                            </td>
                            <td className="px-4 lg:px-6 py-3 lg:py-4 text-right text-gray-500">
                              {log.warehouse_date || '-'}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            <div className="bg-[#FFF6F2] border border-[#ffdecb] rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-[#EB5C20] mt-0.5" />
              <div>
                <h4 className="font-bold text-[#EB5C20] text-sm">系統提示</h4>
                <p className="text-sm text-gray-600 mt-1">
                  {snapshotInfo?.snapshotDate
                    ? `以上數據已與 ${snapshotInfo.snapshotDate} 的倉庫明細表同步。系統每日 21:05 自動從郵件同步庫存資料。`
                    : '尚未同步資料，系統每日 21:05 自動從郵件同步庫存資料。'}
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Sync Tool Modal */}
      {showSyncTool && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                <Download className="w-5 h-5 text-[#EB5C20]" />
                補同步庫存資料
              </h3>
              <button
                onClick={() => {
                  setShowSyncTool(false);
                  resetSyncTool();
                }}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-4">
              <p className="text-sm text-gray-600">
                選擇日期範圍，系統將從郵件中補同步該期間的庫存資料。任務會在背景執行，您可以繼續操作其他功能。
              </p>

              {/* Date Range Inputs */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    開始日期
                  </label>
                  <input
                    type="date"
                    value={syncStartDate}
                    onChange={(e) => setSyncStartDate(e.target.value)}
                    max={syncEndDate || new Date().toISOString().slice(0, 10)}
                    disabled={syncLoading}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#EB5C20] focus:border-[#EB5C20] outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    結束日期
                  </label>
                  <input
                    type="date"
                    value={syncEndDate}
                    onChange={(e) => setSyncEndDate(e.target.value)}
                    min={syncStartDate}
                    max={new Date().toISOString().slice(0, 10)}
                    disabled={syncLoading}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#EB5C20] focus:border-[#EB5C20] outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Task Status */}
              {syncTaskStatus && (
                <div className={`p-3 rounded-lg flex items-start gap-3 ${
                  syncTaskStatus.status === 'started'
                    ? 'bg-green-50 border border-green-200'
                    : syncTaskStatus.status === 'failed'
                    ? 'bg-red-50 border border-red-200'
                    : 'bg-blue-50 border border-blue-200'
                }`}>
                  {syncTaskStatus.status === 'started' ? (
                    <>
                      <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-green-700">同步任務已啟動</p>
                        <p className="text-xs text-green-600 mt-1">
                          任務正在背景執行中，請稍候數分鐘後重新整理頁面查看結果。
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-red-700">同步失敗</p>
                        <p className="text-xs text-red-600 mt-1">
                          {syncTaskStatus.error || '未知錯誤'}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Info Box */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex items-start gap-2">
                <Clock className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-gray-500">
                  提示：每天的庫存資料來自早上 8:30 左右發送的郵件。最多可同步 90 天的資料。
                </p>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200">
              <button
                onClick={() => {
                  setShowSyncTool(false);
                  resetSyncTool();
                }}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                {syncTaskStatus?.status === 'started' ? '關閉' : '取消'}
              </button>
              {syncTaskStatus?.status !== 'started' && (
                <button
                  onClick={handleDateRangeSync}
                  disabled={!syncStartDate || !syncEndDate || syncLoading}
                  className="px-4 py-2 text-sm bg-[#EB5C20] text-white rounded-lg hover:bg-[#d44c15] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {syncLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      執行中...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      開始同步
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Sales Sync Tool Modal */}
      {showSalesSyncTool && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-500" />
                補同步銷量資料
              </h3>
              <button
                onClick={() => {
                  setShowSalesSyncTool(false);
                  resetSalesSyncTool();
                }}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-4">
              <p className="text-sm text-gray-600">
                選擇日期範圍，系統將從郵件中補同步該期間的銷量資料（訂單實出）。任務會在背景執行，您可以繼續操作其他功能。
              </p>

              {/* Date Range Inputs */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    開始日期
                  </label>
                  <input
                    type="date"
                    value={syncStartDate}
                    onChange={(e) => setSyncStartDate(e.target.value)}
                    max={syncEndDate || new Date().toISOString().slice(0, 10)}
                    disabled={salesSyncLoading}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    結束日期
                  </label>
                  <input
                    type="date"
                    value={syncEndDate}
                    onChange={(e) => setSyncEndDate(e.target.value)}
                    min={syncStartDate}
                    max={new Date().toISOString().slice(0, 10)}
                    disabled={salesSyncLoading}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Task Status */}
              {salesSyncTaskStatus && (
                <div className={`p-3 rounded-lg flex items-start gap-3 ${
                  salesSyncTaskStatus.status === 'started'
                    ? 'bg-green-50 border border-green-200'
                    : 'bg-red-50 border border-red-200'
                }`}>
                  {salesSyncTaskStatus.status === 'started' ? (
                    <>
                      <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-green-700">銷量同步任務已啟動</p>
                        <p className="text-xs text-green-600 mt-1">
                          任務正在背景執行中，請稍候數分鐘後重新整理頁面查看結果。
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-red-700">同步失敗</p>
                        <p className="text-xs text-red-600 mt-1">
                          {salesSyncTaskStatus.error || '未知錯誤'}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Info Box */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-start gap-2">
                <Clock className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-blue-600">
                  提示：銷量資料來自逢泰 A442_QC Excel 的「訂單實出」欄位。最多可同步 90 天的資料。
                </p>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200">
              <button
                onClick={() => {
                  setShowSalesSyncTool(false);
                  resetSalesSyncTool();
                }}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                {salesSyncTaskStatus?.status === 'started' ? '關閉' : '取消'}
              </button>
              {salesSyncTaskStatus?.status !== 'started' && (
                <button
                  onClick={handleSalesDateRangeSync}
                  disabled={!syncStartDate || !syncEndDate || salesSyncLoading}
                  className="px-4 py-2 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {salesSyncLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      執行中...
                    </>
                  ) : (
                    <>
                      <TrendingUp className="w-4 h-4" />
                      開始同步
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
