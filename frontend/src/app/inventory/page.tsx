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
} from 'lucide-react';

// API Base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

// Brand colors
const BRAND_ORANGE = '#EB5C20';
const BRAND_GRAY = '#9FA0A0';

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
  id: string;
  date: string;
  item_name: string;
  category: string;
  previous_stock: number;
  new_stock: number;
  change_amount: number;
  source: string;
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

interface ItemTrend {
  name: string;
  category: string;
  data: TrendDataPoint[];
}

// API response types
interface ApiInventoryItem {
  id: string;
  name: string;
  category: string;
  current_stock: number;
  available_stock: number;
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
type TabType = 'inventory' | 'analysis' | 'restock';

export default function InventoryDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('inventory');
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
    rawItemCount: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trendData, setTrendData] = useState<ItemTrend[]>([]);
  const [selectedTrendItem, setSelectedTrendItem] = useState<string>('');
  const [trendDays, setTrendDays] = useState<number>(30);

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

  // Fetch restock logs
  const fetchRestockLogs = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/inventory/changes?limit=20`);
      const result = await response.json();

      if (result.success && result.data) {
        setRestockLogs(result.data);
      }
    } catch (err) {
      console.error('Failed to fetch restock logs:', err);
    }
  }, []);

  // Fetch trend data (only when user clicks)
  const fetchTrendData = useCallback(async (category?: string) => {
    try {
      const url = category
        ? `${API_BASE_URL}/api/inventory/trend?days=${trendDays}&category=${category}`
        : `${API_BASE_URL}/api/inventory/trend?days=${trendDays}`;
      const response = await fetch(url);
      const result = await response.json();

      if (result.success && result.data) {
        setTrendData(result.data);
        // Auto-select first item if none selected
        if (result.data.length > 0) {
          setSelectedTrendItem(result.data[0].name);
        }
      }
    } catch (err) {
      console.error('Failed to fetch trend data:', err);
    }
  }, [trendDays]);

  // Initialize: fetch from API (only once on mount)
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await fetchInventory();
      await fetchRestockLogs();
      setLoading(false);
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refresh data from database (no sync from email)
  const handleRefresh = async () => {
    setSyncing(true);
    await fetchInventory();
    await fetchRestockLogs();
    setSyncing(false);
  };

  // Computed Totals
  const totals = useMemo(() => {
    return {
      bread: items.filter((i) => i.category === 'bread').reduce((acc, curr) => acc + curr.stock, 0),
      box: items.filter((i) => i.category === 'box').reduce((acc, curr) => acc + curr.stock, 0),
      bag: items.filter((i) => i.category === 'bag').reduce((acc, curr) => acc + curr.stock, 0),
    };
  }, [items]);

  const filteredItems = items.filter((item) =>
    item.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const breadItems = filteredItems.filter((i) => i.category === 'bread');
  const boxItems = filteredItems.filter((i) => i.category === 'box');
  const bagItems = filteredItems.filter((i) => i.category === 'bag');

  // Loading state
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

  // Error state with no data
  if (error && items.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-[#EB5C20] mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-800 mb-2">無法載入庫存資料</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="space-y-3">
            <button
              onClick={handleRefresh}
              disabled={syncing}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#EB5C20] text-white rounded-lg hover:bg-[#d44c15] transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? '載入中...' : '重新載入'}
            </button>
            <Link
              href="/"
              className="block w-full px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              返回首頁
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 font-sans text-gray-800">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="flex items-center gap-2 text-gray-600 hover:text-[#EB5C20] transition-colors mr-4"
              >
                <ArrowLeft className="w-4 h-4" />
              </Link>
              <div className="w-8 h-8 rounded bg-[#EB5C20] flex items-center justify-center text-white font-bold">
                CR
              </div>
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">
                減醣市集{' '}
                <span className="text-[#9FA0A0] font-normal text-sm ml-2">
                  庫存管理儀表板
                </span>
                {snapshotInfo && (
                  <span className="ml-2 text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full border border-blue-200">
                    資料時間: {snapshotInfo.snapshotDate} {snapshotInfo.snapshotTime}
                  </span>
                )}
                {snapshotInfo && snapshotInfo.lowStockCount > 0 && (
                  <span className="ml-2 text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                    {snapshotInfo.lowStockCount} 項低庫存
                  </span>
                )}
              </h1>
            </div>

            <div className="flex items-center gap-4">
              {/* Refresh Button */}
              <button
                onClick={handleRefresh}
                disabled={syncing}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? '載入中...' : '重新整理'}
              </button>

              {/* Tab Navigation */}
              <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
                {[
                  { id: 'inventory' as TabType, label: '庫存總覽', icon: Package },
                  { id: 'analysis' as TabType, label: '銷量分析', icon: TrendingUp },
                  { id: 'restock' as TabType, label: '進貨紀錄', icon: ClipboardList },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`
                      flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all
                      ${
                        activeTab === tab.id
                          ? 'bg-white text-[#EB5C20] shadow-sm'
                          : 'text-gray-500 hover:text-gray-700 hover:bg-gray-200'
                      }
                    `}
                  >
                    <tab.icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Top Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatCard
            title="麵包總庫存"
            value={totals.bread}
            unit="個"
            icon={ShoppingBag}
            colorClass="text-[#EB5C20]"
          />
          <StatCard
            title="紙箱總庫存"
            value={totals.box}
            unit="個"
            icon={Box}
            colorClass="text-[#9FA0A0]"
          />
          <StatCard
            title="塑膠袋總庫存"
            value={Number(totals.bag.toFixed(1))}
            unit="捲"
            icon={Package}
            colorClass="text-blue-500"
          />
        </div>

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
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  資料來源: 倉庫明細表 (12/25)
                </span>
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
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          item.stockStatus === 'low'
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
                    <div className="mt-3 text-xs text-gray-400 flex justify-between">
                      <span>最低庫存: {item.minStock.toLocaleString()}</span>
                      <span>
                        可用量: {item.availableStock.toLocaleString()}
                      </span>
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
                      <StockLevelBar current={item.stock} max={6000} lowThreshold={500} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Bags */}
              <div className="lg:col-span-2">
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                    <span className="w-1.5 h-6 bg-blue-400 rounded-full"></span>
                    塑膠袋庫存
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
                        {bagItems.map((item) => (
                          <tr key={item.id} className="hover:bg-gray-50">
                            <td className="px-6 py-3 font-medium text-gray-700">{item.name}</td>
                            <td className="px-6 py-3 text-right font-bold text-gray-800">
                              {item.stock.toLocaleString()} {item.unit || '捲'}
                            </td>
                            <td className="px-6 py-3 text-right text-gray-500">
                              {item.itemsPerRoll
                                ? (item.stock * item.itemsPerRoll).toLocaleString()
                                : '-'} 個
                            </td>
                            <td className="px-6 py-3 text-right">
                              <span
                                className={`inline-block w-2.5 h-2.5 rounded-full ${
                                  item.stockStatus === 'low' ? 'bg-red-500' : item.stockStatus === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                                }`}
                              ></span>
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
          <div className="space-y-6">
            {/* Controls */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
              <div className="flex flex-wrap items-center gap-4">
                {/* Days selector */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">時間範圍:</span>
                  <div className="flex gap-1">
                    {[7, 14, 30].map((days) => (
                      <button
                        key={days}
                        onClick={() => setTrendDays(days)}
                        className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                          trendDays === days
                            ? 'bg-[#EB5C20] text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {days} 天
                      </button>
                    ))}
                  </div>
                </div>

                {/* Item selector */}
                <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                  <span className="text-sm text-gray-600">選擇品項:</span>
                  <select
                    value={selectedTrendItem}
                    onChange={(e) => setSelectedTrendItem(e.target.value)}
                    className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#EB5C20] focus:border-transparent"
                  >
                    {trendData.map((item) => (
                      <option key={item.name} value={item.name}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Refresh button */}
                <button
                  onClick={() => fetchTrendData('bread')}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  重新整理
                </button>
              </div>
            </div>

            {/* Trend Chart */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-gray-800">
                  庫存趨勢圖 - {selectedTrendItem || '請選擇品項'}
                </h3>
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  近 {trendDays} 天資料
                </span>
              </div>

              {trendData.length === 0 ? (
                <div className="h-80 flex items-center justify-center text-gray-400">
                  <div className="text-center">
                    <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>載入趨勢資料中...</p>
                  </div>
                </div>
              ) : (
                <div className="h-80 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={
                        trendData
                          .find((item) => item.name === selectedTrendItem)
                          ?.data.map((d) => ({
                            date: d.date.slice(5), // MM-DD format
                            庫存量: d.stock,
                          })) || []
                      }
                      margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11 }}
                        tickMargin={10}
                      />
                      <YAxis
                        tick={{ fontSize: 11 }}
                        tickFormatter={(value) => value.toLocaleString()}
                      />
                      <RechartsTooltip
                        contentStyle={{
                          borderRadius: '8px',
                          border: 'none',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                        }}
                        formatter={(value: number) => [value.toLocaleString(), '庫存量']}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="庫存量"
                        stroke="#EB5C20"
                        strokeWidth={2}
                        dot={{ fill: '#EB5C20', strokeWidth: 2, r: 4 }}
                        activeDot={{ r: 6, fill: '#EB5C20' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Items Table with current stock and trend */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h3 className="font-bold text-gray-800">各品項庫存走勢</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 text-gray-500 font-medium">
                    <tr>
                      <th className="px-6 py-3">商品名稱</th>
                      <th className="px-6 py-3 text-right">目前庫存</th>
                      <th className="px-6 py-3 text-right">{trendDays}天前庫存</th>
                      <th className="px-6 py-3 text-right">變化量</th>
                      <th className="px-6 py-3 text-right">趨勢</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {trendData.slice(0, 15).map((item) => {
                      const latestStock = item.data[item.data.length - 1]?.stock || 0;
                      const oldestStock = item.data[0]?.stock || 0;
                      const change = latestStock - oldestStock;
                      const changePercent = oldestStock > 0 ? ((change / oldestStock) * 100).toFixed(1) : 0;

                      return (
                        <tr
                          key={item.name}
                          className={`hover:bg-gray-50 cursor-pointer ${
                            selectedTrendItem === item.name ? 'bg-orange-50' : ''
                          }`}
                          onClick={() => setSelectedTrendItem(item.name)}
                        >
                          <td className="px-6 py-3 font-medium text-gray-700">
                            {item.name}
                            {selectedTrendItem === item.name && (
                              <span className="ml-2 text-xs text-[#EB5C20]">● 已選取</span>
                            )}
                          </td>
                          <td className="px-6 py-3 text-right font-bold text-gray-900">
                            {latestStock.toLocaleString()}
                          </td>
                          <td className="px-6 py-3 text-right text-gray-500">
                            {oldestStock.toLocaleString()}
                          </td>
                          <td className={`px-6 py-3 text-right font-bold ${
                            change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-500'
                          }`}>
                            {change > 0 ? '+' : ''}{change.toLocaleString()}
                            <span className="text-xs font-normal ml-1">({changePercent}%)</span>
                          </td>
                          <td className="px-6 py-3 text-right">
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
          </div>
        )}

        {/* Tab Content: Restock Log */}
        {activeTab === 'restock' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-bold text-gray-800">
                近期庫存變動紀錄 {restockLogs.length > 0 && `(${restockLogs.length} 筆)`}
              </h2>
              <button
                onClick={fetchRestockLogs}
                className="bg-[#EB5C20] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#d44c15] transition-colors flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                重新整理
              </button>
            </div>

            {restockLogs.length === 0 ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
                <ClipboardList className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">尚無庫存變動紀錄</p>
                <p className="text-sm text-gray-400 mt-1">當庫存發生變化時，紀錄會顯示在這裡</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 text-gray-500 font-medium">
                    <tr>
                      <th className="px-6 py-3">日期</th>
                      <th className="px-6 py-3">品項</th>
                      <th className="px-6 py-3">分類</th>
                      <th className="px-6 py-3 text-right">變動前</th>
                      <th className="px-6 py-3 text-right">變動後</th>
                      <th className="px-6 py-3 text-right">變動量</th>
                      <th className="px-6 py-3 text-right">來源</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {restockLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 text-gray-600 flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-gray-400" />
                          {new Date(log.date).toLocaleDateString('zh-TW')}
                        </td>
                        <td className="px-6 py-4 font-medium text-gray-800">{log.item_name}</td>
                        <td className="px-6 py-4 text-gray-600">
                          <span className="bg-gray-100 px-2 py-1 rounded text-xs">
                            {log.category === 'bread' ? '麵包' : log.category === 'box' ? '紙箱' : '袋子'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right text-gray-500">
                          {log.previous_stock.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-right text-gray-800">
                          {log.new_stock.toLocaleString()}
                        </td>
                        <td className={`px-6 py-4 text-right font-bold ${log.change_amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {log.change_amount >= 0 ? '+' : ''}{log.change_amount.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <span className="text-xs font-medium border px-2 py-1 rounded-full bg-blue-50 text-blue-600 border-blue-200">
                            {log.source === 'email' ? '郵件同步' : log.source}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="bg-[#FFF6F2] border border-[#ffdecb] rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-[#EB5C20] mt-0.5" />
              <div>
                <h4 className="font-bold text-[#EB5C20] text-sm">系統提示</h4>
                <p className="text-sm text-gray-600 mt-1">
                  {lastSyncDate
                    ? `以上數據已與 ${lastSyncDate} 的倉庫明細表同步。系統每日 21:05 自動從郵件同步庫存資料。`
                    : '尚未同步資料，請點擊「同步資料」按鈕從郵件匯入庫存明細。'}
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
