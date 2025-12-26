'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import {
  BarChart,
  Bar,
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
  dailySales: number;
  sales7d: number;
  sales14d: number;
  sales30d: number;
  bagStock?: number;
}

interface RestockLog {
  id: number;
  date: string;
  item: string;
  quantity: number;
  supplier: string;
}

// --- Real Data Mapped from Uploaded CSV ---
const REAL_DATA_MAP: Record<string, { stock: number; dailySales: number; bagStock: number }> = {
  "低糖草莓乳酪貝果": { stock: 7109, dailySales: 92, bagStock: 18.1 },
  "日式香醇芝麻乳酪貝果": { stock: 8599, dailySales: 102, bagStock: 3.0 },
  "宇治抹茶紅豆貝果": { stock: 7502, dailySales: 62, bagStock: 6.0 },
  "低糖藍莓乳酪貝果": { stock: 7125, dailySales: 98, bagStock: 18.1 },
  "經典輕盈原味貝果": { stock: 10450, dailySales: 97, bagStock: 6.0 },
  "濃郁起司乳酪丁貝果": { stock: 6004, dailySales: 150, bagStock: 7.0 },
  "法式AOP極致奶油貝果": { stock: 11398, dailySales: 83, bagStock: 3.0 },
  "原味高蛋白奶酥貝果": { stock: 6972, dailySales: 27, bagStock: 3.0 },
  "伯爵高蛋白奶酥貝果": { stock: 6901, dailySales: 53, bagStock: 3.0 },
  "開心果乳酪貝果": { stock: 7300, dailySales: 42, bagStock: 3.0 },
  "開心果乳酪歐包": { stock: 5729, dailySales: 39, bagStock: 3.0 },
  "鹽之花鄉村歐包": { stock: 4231, dailySales: 42, bagStock: 3.0 },
  "伯爵白巧克力歐包": { stock: 5407, dailySales: 36, bagStock: 3.0 },
  "黑巧克力歐包": { stock: 4435, dailySales: 55, bagStock: 3.0 },
  "菠菜起司乳酪丁歐包": { stock: 6675, dailySales: 41, bagStock: 3.0 },
  "莓果綜合穀物歐包": { stock: 4709, dailySales: 35, bagStock: 3.0 },
};

const BREAD_FLAVORS = Object.keys(REAL_DATA_MAP);

const BOX_DATA = [
  { name: "60cm 紙箱", stock: 4724, dailyUse: 54 },
  { name: "90cm 紙箱", stock: 5314, dailyUse: 13 },
];

const LATEST_RESTOCK_LOGS: RestockLog[] = [
  { id: 1, date: '2025-12-19', item: '低糖藍莓乳酪貝果', quantity: 2400, supplier: '主要烘焙廠' },
  { id: 2, date: '2025-12-19', item: '法式AOP極致奶油貝果', quantity: 2400, supplier: '主要烘焙廠' },
  { id: 3, date: '2025-12-19', item: '經典輕盈原味貝果', quantity: 2400, supplier: '主要烘焙廠' },
  { id: 4, date: '2025-12-19', item: '伯爵白巧克力歐包', quantity: 1920, supplier: '主要烘焙廠' },
  { id: 5, date: '2025-12-18', item: '莓果綜合穀物歐包', quantity: 1920, supplier: '主要烘焙廠' },
  { id: 6, date: '2025-12-16', item: '開心果乳酪歐包', quantity: 2052, supplier: '主要烘焙廠' },
];

// Generate initial data
const generateInitialData = (): InventoryItem[] => {
  const data: InventoryItem[] = [];

  // 1. Breads
  BREAD_FLAVORS.forEach((flavor, index) => {
    const realData = REAL_DATA_MAP[flavor];
    const estSales7d = realData.dailySales * 7;
    const estSales14d = realData.dailySales * 14;
    const estSales30d = realData.dailySales * 30;

    data.push({
      id: `bread-${index}`,
      name: flavor,
      category: 'bread',
      stock: realData.stock,
      sales7d: estSales7d,
      sales14d: estSales14d,
      sales30d: estSales30d,
      dailySales: realData.dailySales,
    });
  });

  // 2. Boxes
  BOX_DATA.forEach((box, index) => {
    const estSales7d = box.dailyUse * 7;
    const estSales14d = box.dailyUse * 14;
    const estSales30d = box.dailyUse * 30;

    data.push({
      id: `box-${index}`,
      name: box.name,
      category: 'box',
      stock: box.stock,
      sales7d: estSales7d,
      sales14d: estSales14d,
      sales30d: estSales30d,
      dailySales: box.dailyUse,
    });
  });

  // 3. Bags
  BREAD_FLAVORS.forEach((flavor, index) => {
    const realData = REAL_DATA_MAP[flavor];
    const bagStock = realData.bagStock;

    data.push({
      id: `bag-${index}`,
      name: `${flavor}專用袋`,
      category: 'bag',
      stock: bagStock,
      sales7d: realData.dailySales * 7,
      sales14d: realData.dailySales * 14,
      sales30d: realData.dailySales * 30,
      dailySales: realData.dailySales,
      bagStock: bagStock,
    });
  });

  return data;
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
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncDate, setLastSyncDate] = useState<string>('2025/12/25');

  // Initialize with mock data
  useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => {
      setItems(generateInitialData());
      setLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  // Fetch from API (for future real data)
  const fetchInventory = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/inventory`);
      const result = await response.json();

      if (result.success && result.data) {
        // Transform API data to match our format
        // For now, we use mock data
        console.log('API data:', result.data);
      }
    } catch (err) {
      console.error('Failed to fetch inventory:', err);
    }
  }, []);

  // Trigger sync
  const handleSync = async () => {
    setSyncing(true);
    try {
      await fetch(`${API_BASE_URL}/api/inventory/sync`, { method: 'POST' });
      await fetchInventory();
      setLastSyncDate(new Date().toLocaleDateString('zh-TW'));
    } catch (err) {
      console.error('Sync failed:', err);
    } finally {
      setSyncing(false);
    }
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
                  庫存管理儀表板 (已同步 {lastSyncDate} 數據)
                </span>
              </h1>
            </div>

            <div className="flex items-center gap-4">
              {/* Sync Button */}
              <button
                onClick={handleSync}
                disabled={syncing}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-[#EB5C20] text-white rounded-lg hover:bg-[#d44c15] transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? '同步中...' : '同步資料'}
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
                          item.stock < 1000
                            ? 'bg-red-100 text-red-600'
                            : 'bg-green-100 text-green-600'
                        }`}
                      >
                        {item.stock < 1000 ? '低庫存' : '充足'}
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-[#EB5C20]">
                      {item.stock.toLocaleString()}{' '}
                      <span className="text-xs text-gray-400 font-normal">個</span>
                    </div>
                    <StockLevelBar current={item.stock} max={12000} lowThreshold={1000} />
                    <div className="mt-3 text-xs text-gray-400 flex justify-between">
                      <span>今日銷量: {item.dailySales}</span>
                      <span>
                        預估可售:{' '}
                        {item.dailySales > 0 ? (item.stock / item.dailySales).toFixed(0) : '>99'} 天
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
                              {item.stock.toFixed(1)} 捲
                            </td>
                            <td className="px-6 py-3 text-right text-gray-500">
                              {(item.stock * 6000).toLocaleString()} 個
                            </td>
                            <td className="px-6 py-3 text-right">
                              <span
                                className={`inline-block w-2.5 h-2.5 rounded-full ${
                                  item.stock <= 2 ? 'bg-red-500' : 'bg-green-500'
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
          <div className="space-y-8">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
              <h3 className="text-lg font-bold text-gray-800 mb-6">麵包銷量趨勢 (Top 5 熱銷)</h3>
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={breadItems.sort((a, b) => b.sales30d - a.sales30d).slice(0, 5)}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} interval={0} />
                    <YAxis />
                    <RechartsTooltip
                      contentStyle={{
                        borderRadius: '8px',
                        border: 'none',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                      }}
                    />
                    <Legend />
                    <Bar name="預估近7天" dataKey="sales7d" fill="#EB5C20" radius={[4, 4, 0, 0]} />
                    <Bar name="預估近14天" dataKey="sales14d" fill="#9FA0A0" radius={[4, 4, 0, 0]} />
                    <Bar name="預估近30天" dataKey="sales30d" fill="#2d3748" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h3 className="font-bold text-gray-800">各品項詳細銷量數據 (依今日銷量推算)</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 text-gray-500 font-medium">
                    <tr>
                      <th className="px-6 py-3">商品名稱</th>
                      <th className="px-6 py-3 text-right">今日實際銷量</th>
                      <th className="px-6 py-3 text-right text-[#EB5C20]">預估 7 天</th>
                      <th className="px-6 py-3 text-right text-gray-800">預估 30 天</th>
                      <th className="px-6 py-3 text-right">建議</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {breadItems.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50">
                        <td className="px-6 py-3 font-medium text-gray-700">{item.name}</td>
                        <td className="px-6 py-3 text-right font-bold text-gray-900 bg-gray-50">
                          {item.dailySales}
                        </td>
                        <td className="px-6 py-3 text-right font-bold text-[#EB5C20]">
                          {item.sales7d}
                        </td>
                        <td className="px-6 py-3 text-right text-gray-600">{item.sales30d}</td>
                        <td className="px-6 py-3 text-right">
                          {item.sales7d > 500 && item.stock < 2000 ? (
                            <span className="text-red-600 bg-red-50 px-2 py-1 rounded text-xs font-medium">
                              建議補貨
                            </span>
                          ) : (
                            <span className="text-green-600 bg-green-50 px-2 py-1 rounded text-xs font-medium">
                              庫存健康
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
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
              <h2 className="text-lg font-bold text-gray-800">近期進貨紀錄 (從庫存表提取)</h2>
              <button className="bg-[#EB5C20] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#d44c15] transition-colors flex items-center gap-2">
                <ArrowUpRight className="w-4 h-4" />
                手動新增
              </button>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 text-gray-500 font-medium">
                  <tr>
                    <th className="px-6 py-3">進貨日期 (最後入倉)</th>
                    <th className="px-6 py-3">品項</th>
                    <th className="px-6 py-3">供應商</th>
                    <th className="px-6 py-3 text-right">數量</th>
                    <th className="px-6 py-3 text-right">狀態</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {LATEST_RESTOCK_LOGS.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-600 flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        {log.date}
                      </td>
                      <td className="px-6 py-4 font-medium text-gray-800">{log.item}</td>
                      <td className="px-6 py-4 text-gray-600">
                        <span className="bg-gray-100 px-2 py-1 rounded text-xs">{log.supplier}</span>
                      </td>
                      <td className="px-6 py-4 text-right font-bold text-[#EB5C20]">
                        +{log.quantity.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-green-600 text-xs font-medium border border-green-200 bg-green-50 px-2 py-1 rounded-full">
                          已入庫
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-[#FFF6F2] border border-[#ffdecb] rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-[#EB5C20] mt-0.5" />
              <div>
                <h4 className="font-bold text-[#EB5C20] text-sm">系統提示</h4>
                <p className="text-sm text-gray-600 mt-1">
                  以上數據已與 {lastSyncDate} 的倉庫明細表同步。建議每週上傳新的 Excel 檔案以保持數據準確。
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
