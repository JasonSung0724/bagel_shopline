'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Gift,
  Plus,
  Trash2,
  Edit,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  Users,
  Award,
  RefreshCw,
  Loader2,
  ArrowLeft,
  Lock,
  Eye,
  EyeOff,
  Copy,
  Search,
  Calendar,
  Percent,
  Package,
  TicketCheck,
} from 'lucide-react';

// API Base URL
const API_BASE_URL = '';

// Types
interface Prize {
  id: string;
  campaign_id: string;
  name: string;
  description?: string;
  prize_type: 'physical' | 'coupon' | 'points' | 'free_shipping' | 'discount' | 'none';
  prize_value?: string;
  image_url?: string;
  total_quantity: number;
  remaining_quantity: number;
  probability: number;
  display_order: number;
  is_active: boolean;
}

interface Campaign {
  id: string;
  name: string;
  description?: string;
  start_date: string;
  end_date: string;
  status: 'draft' | 'active' | 'paused' | 'ended';
  max_attempts_per_user: number;
  require_login: boolean;
  prizes?: Prize[];
}

interface CampaignStats {
  total_participants: number;
  total_attempts: number;
  total_winners: number;
  total_redeemed: number;
  prizes_stats: {
    id: string;
    name: string;
    total: number;
    remaining: number;
    won: number;
    redeemed: number;
  }[];
}

interface LotteryResult {
  id: string;
  prize_name?: string;
  prize_type?: string;
  redemption_code?: string;
  is_winner: boolean;
  is_redeemed: boolean;
  scratched_at: string;
  redeemed_at?: string;
  lottery_participants?: {
    customer_email?: string;
    customer_name?: string;
    shopline_customer_id?: string;
  };
}

// Status badge colors
const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800',
  active: 'bg-green-100 text-green-800',
  paused: 'bg-yellow-100 text-yellow-800',
  ended: 'bg-red-100 text-red-800',
};

const statusLabels: Record<string, string> = {
  draft: '草稿',
  active: '進行中',
  paused: '暫停',
  ended: '已結束',
};

const prizeTypeLabels: Record<string, string> = {
  physical: '實體商品',
  coupon: '折價券',
  points: '點數',
  free_shipping: '免運',
  discount: '折扣',
  none: '未中獎',
};

export default function LotteryAdminPage() {
  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState('');
  const [isAuthLoading, setIsAuthLoading] = useState(false);

  // Data state
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [campaignStats, setCampaignStats] = useState<CampaignStats | null>(null);
  const [results, setResults] = useState<LotteryResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Modal state
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [showPrizeModal, setShowPrizeModal] = useState(false);
  const [showRedeemModal, setShowRedeemModal] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [editingPrize, setEditingPrize] = useState<Prize | null>(null);

  // Form state
  const [campaignForm, setCampaignForm] = useState({
    name: '',
    description: '',
    start_date: '',
    end_date: '',
    max_attempts_per_user: 1,
    require_login: true,
  });

  const [prizeForm, setPrizeForm] = useState({
    name: '',
    description: '',
    prize_type: 'physical' as Prize['prize_type'],
    prize_value: '',
    total_quantity: 0,
    probability: 0,
    display_order: 0,
  });

  const [redeemCode, setRedeemCode] = useState('');
  const [redeemResult, setRedeemResult] = useState<{ success: boolean; message: string } | null>(null);

  // Tab state
  const [activeTab, setActiveTab] = useState<'overview' | 'prizes' | 'results'>('overview');

  // Fetch with auth header
  const fetchWithAuth = useCallback(async (url: string, options: RequestInit = {}) => {
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'X-Admin-Password': password,
        'Content-Type': 'application/json',
      },
    });
  }, [password]);

  // Load campaigns
  const loadCampaigns = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_BASE_URL}/api/lottery/admin/campaigns`);
      const data = await res.json();
      if (data.success) {
        setCampaigns(data.data);
      }
    } catch (error) {
      console.error('Failed to load campaigns:', error);
    } finally {
      setIsLoading(false);
    }
  }, [fetchWithAuth]);

  // Load campaign details
  const loadCampaignDetails = useCallback(async (campaignId: string) => {
    setIsLoading(true);
    try {
      const [campaignRes, statsRes, resultsRes] = await Promise.all([
        fetchWithAuth(`${API_BASE_URL}/api/lottery/admin/campaigns/${campaignId}`),
        fetchWithAuth(`${API_BASE_URL}/api/lottery/admin/campaigns/${campaignId}/stats`),
        fetchWithAuth(`${API_BASE_URL}/api/lottery/admin/campaigns/${campaignId}/results?limit=50`),
      ]);

      const [campaignData, statsData, resultsData] = await Promise.all([
        campaignRes.json(),
        statsRes.json(),
        resultsRes.json(),
      ]);

      if (campaignData.success) setSelectedCampaign(campaignData.data);
      if (statsData.success) setCampaignStats(statsData.data);
      if (resultsData.success) setResults(resultsData.data);
    } catch (error) {
      console.error('Failed to load campaign details:', error);
    } finally {
      setIsLoading(false);
    }
  }, [fetchWithAuth]);

  // Auth
  const handleAuth = async () => {
    setIsAuthLoading(true);
    setAuthError('');

    try {
      const res = await fetch(`${API_BASE_URL}/api/lottery/admin/campaigns`, {
        headers: { 'X-Admin-Password': password },
      });

      if (res.ok) {
        setIsAuthenticated(true);
        localStorage.setItem('lottery_admin_pwd', password);
      } else {
        setAuthError('密碼錯誤');
      }
    } catch {
      setAuthError('連線失敗');
    } finally {
      setIsAuthLoading(false);
    }
  };

  // Check stored password on mount
  useEffect(() => {
    const stored = localStorage.getItem('lottery_admin_pwd');
    if (stored) {
      setPassword(stored);
      fetch(`${API_BASE_URL}/api/lottery/admin/campaigns`, {
        headers: { 'X-Admin-Password': stored },
      }).then(res => {
        if (res.ok) {
          setIsAuthenticated(true);
        }
      });
    }
  }, []);

  // Load campaigns when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadCampaigns();
    }
  }, [isAuthenticated, loadCampaigns]);

  // Campaign CRUD
  const saveCampaign = async () => {
    try {
      const url = editingCampaign
        ? `${API_BASE_URL}/api/lottery/admin/campaigns/${editingCampaign.id}`
        : `${API_BASE_URL}/api/lottery/admin/campaigns`;

      const method = editingCampaign ? 'PUT' : 'POST';

      const res = await fetchWithAuth(url, {
        method,
        body: JSON.stringify(campaignForm),
      });

      const data = await res.json();
      if (data.success) {
        setShowCampaignModal(false);
        loadCampaigns();
        if (selectedCampaign) {
          loadCampaignDetails(selectedCampaign.id);
        }
      } else {
        alert(data.error || '儲存失敗');
      }
    } catch (error) {
      console.error('Failed to save campaign:', error);
      alert('儲存失敗');
    }
  };

  const deleteCampaign = async (id: string) => {
    if (!confirm('確定要刪除此活動？')) return;

    try {
      const res = await fetchWithAuth(`${API_BASE_URL}/api/lottery/admin/campaigns/${id}`, {
        method: 'DELETE',
      });

      const data = await res.json();
      if (data.success) {
        loadCampaigns();
        if (selectedCampaign?.id === id) {
          setSelectedCampaign(null);
        }
      } else {
        alert(data.error || '刪除失敗');
      }
    } catch (error) {
      console.error('Failed to delete campaign:', error);
      alert('刪除失敗');
    }
  };

  const updateCampaignStatus = async (id: string, status: string) => {
    try {
      const res = await fetchWithAuth(`${API_BASE_URL}/api/lottery/admin/campaigns/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      });

      const data = await res.json();
      if (data.success) {
        loadCampaigns();
        if (selectedCampaign?.id === id) {
          loadCampaignDetails(id);
        }
      } else {
        alert(data.error || '更新失敗');
      }
    } catch (error) {
      console.error('Failed to update status:', error);
      alert('更新失敗');
    }
  };

  // Prize CRUD
  const savePrize = async () => {
    if (!selectedCampaign) return;

    try {
      const url = editingPrize
        ? `${API_BASE_URL}/api/lottery/admin/prizes/${editingPrize.id}`
        : `${API_BASE_URL}/api/lottery/admin/campaigns/${selectedCampaign.id}/prizes`;

      const method = editingPrize ? 'PUT' : 'POST';

      const res = await fetchWithAuth(url, {
        method,
        body: JSON.stringify(prizeForm),
      });

      const data = await res.json();
      if (data.success) {
        setShowPrizeModal(false);
        loadCampaignDetails(selectedCampaign.id);
      } else {
        alert(data.error || '儲存失敗');
      }
    } catch (error) {
      console.error('Failed to save prize:', error);
      alert('儲存失敗');
    }
  };

  const deletePrize = async (id: string) => {
    if (!confirm('確定要刪除此獎品？')) return;

    try {
      const res = await fetchWithAuth(`${API_BASE_URL}/api/lottery/admin/prizes/${id}`, {
        method: 'DELETE',
      });

      const data = await res.json();
      if (data.success && selectedCampaign) {
        loadCampaignDetails(selectedCampaign.id);
      } else {
        alert(data.error || '刪除失敗');
      }
    } catch (error) {
      console.error('Failed to delete prize:', error);
      alert('刪除失敗');
    }
  };

  // Redeem
  const handleRedeem = async () => {
    if (!redeemCode.trim()) return;

    try {
      const res = await fetchWithAuth(`${API_BASE_URL}/api/lottery/redeem`, {
        method: 'POST',
        body: JSON.stringify({ code: redeemCode.trim() }),
      });

      const data = await res.json();
      setRedeemResult({
        success: data.success,
        message: data.success ? '兌換成功！' : (data.error || '兌換失敗'),
      });

      if (data.success && selectedCampaign) {
        loadCampaignDetails(selectedCampaign.id);
      }
    } catch (error) {
      console.error('Failed to redeem:', error);
      setRedeemResult({ success: false, message: '兌換失敗' });
    }
  };

  // Auth screen
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-md">
          <div className="flex items-center justify-center mb-6">
            <Gift className="w-12 h-12 text-orange-500" />
          </div>
          <h1 className="text-2xl font-bold text-center mb-6">刮刮樂管理後台</h1>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                管理員密碼
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAuth()}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                  placeholder="請輸入密碼"
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
              <div className="text-red-500 text-sm text-center">{authError}</div>
            )}

            <button
              onClick={handleAuth}
              disabled={isAuthLoading || !password}
              className="w-full bg-orange-500 hover:bg-orange-600 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isAuthLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Lock className="w-5 h-5" />
              )}
              登入
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Campaign detail view
  if (selectedCampaign) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSelectedCampaign(null)}
                className="text-gray-500 hover:text-gray-700"
              >
                <ArrowLeft className="w-6 h-6" />
              </button>
              <div>
                <h1 className="text-xl font-bold">{selectedCampaign.name}</h1>
                <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[selectedCampaign.status]}`}>
                  {statusLabels[selectedCampaign.status]}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {selectedCampaign.status === 'draft' && (
                <button
                  onClick={() => updateCampaignStatus(selectedCampaign.id, 'active')}
                  className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
                >
                  <Play className="w-4 h-4" />
                  啟動活動
                </button>
              )}
              {selectedCampaign.status === 'active' && (
                <button
                  onClick={() => updateCampaignStatus(selectedCampaign.id, 'paused')}
                  className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
                >
                  <Pause className="w-4 h-4" />
                  暫停活動
                </button>
              )}
              {selectedCampaign.status === 'paused' && (
                <button
                  onClick={() => updateCampaignStatus(selectedCampaign.id, 'active')}
                  className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
                >
                  <Play className="w-4 h-4" />
                  恢復活動
                </button>
              )}
              {(selectedCampaign.status === 'active' || selectedCampaign.status === 'paused') && (
                <button
                  onClick={() => updateCampaignStatus(selectedCampaign.id, 'ended')}
                  className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
                >
                  <XCircle className="w-4 h-4" />
                  結束活動
                </button>
              )}
              <button
                onClick={() => loadCampaignDetails(selectedCampaign.id)}
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex gap-4 border-b -mb-px">
              {(['overview', 'prizes', 'results'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-3 font-medium border-b-2 transition-colors ${
                    activeTab === tab
                      ? 'border-orange-500 text-orange-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab === 'overview' && '總覽'}
                  {tab === 'prizes' && '獎品設定'}
                  {tab === 'results' && '刮獎記錄'}
                </button>
              ))}
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 py-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
            </div>
          ) : (
            <>
              {/* Overview Tab */}
              {activeTab === 'overview' && campaignStats && (
                <div className="space-y-6">
                  {/* Stats Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <Users className="w-6 h-6 text-blue-600" />
                        </div>
                        <div>
                          <div className="text-2xl font-bold">{campaignStats.total_participants}</div>
                          <div className="text-sm text-gray-500">參與人數</div>
                        </div>
                      </div>
                    </div>

                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-100 rounded-lg">
                          <TicketCheck className="w-6 h-6 text-purple-600" />
                        </div>
                        <div>
                          <div className="text-2xl font-bold">{campaignStats.total_attempts}</div>
                          <div className="text-sm text-gray-500">刮獎次數</div>
                        </div>
                      </div>
                    </div>

                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-100 rounded-lg">
                          <Award className="w-6 h-6 text-green-600" />
                        </div>
                        <div>
                          <div className="text-2xl font-bold">{campaignStats.total_winners}</div>
                          <div className="text-sm text-gray-500">中獎人數</div>
                        </div>
                      </div>
                    </div>

                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-orange-100 rounded-lg">
                          <Gift className="w-6 h-6 text-orange-600" />
                        </div>
                        <div>
                          <div className="text-2xl font-bold">{campaignStats.total_redeemed}</div>
                          <div className="text-sm text-gray-500">已兌換</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Campaign Info */}
                  <div className="bg-white rounded-lg p-6 shadow-sm">
                    <h3 className="font-semibold mb-4">活動資訊</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">活動期間：</span>
                        <span className="ml-2">
                          {new Date(selectedCampaign.start_date).toLocaleString('zh-TW')} ~{' '}
                          {new Date(selectedCampaign.end_date).toLocaleString('zh-TW')}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">每人可刮次數：</span>
                        <span className="ml-2">{selectedCampaign.max_attempts_per_user} 次</span>
                      </div>
                      <div>
                        <span className="text-gray-500">需要登入：</span>
                        <span className="ml-2">{selectedCampaign.require_login ? '是' : '否'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">活動說明：</span>
                        <span className="ml-2">{selectedCampaign.description || '-'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Prize Stats */}
                  <div className="bg-white rounded-lg p-6 shadow-sm">
                    <h3 className="font-semibold mb-4">獎品統計</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2">獎品名稱</th>
                            <th className="text-center py-2">總數量</th>
                            <th className="text-center py-2">剩餘</th>
                            <th className="text-center py-2">已中獎</th>
                            <th className="text-center py-2">已兌換</th>
                          </tr>
                        </thead>
                        <tbody>
                          {campaignStats.prizes_stats.map((p) => (
                            <tr key={p.id} className="border-b">
                              <td className="py-2">{p.name}</td>
                              <td className="text-center py-2">{p.total}</td>
                              <td className="text-center py-2">{p.remaining}</td>
                              <td className="text-center py-2">{p.won}</td>
                              <td className="text-center py-2">{p.redeemed}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Redeem Section */}
                  <div className="bg-white rounded-lg p-6 shadow-sm">
                    <h3 className="font-semibold mb-4">兌獎</h3>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={redeemCode}
                        onChange={(e) => setRedeemCode(e.target.value.toUpperCase())}
                        placeholder="輸入兌換碼 (XXXX-XXXX-XXXX)"
                        className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500"
                      />
                      <button
                        onClick={handleRedeem}
                        disabled={!redeemCode.trim()}
                        className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-2 rounded-lg disabled:opacity-50"
                      >
                        兌換
                      </button>
                    </div>
                    {redeemResult && (
                      <div className={`mt-2 text-sm ${redeemResult.success ? 'text-green-600' : 'text-red-600'}`}>
                        {redeemResult.message}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Prizes Tab */}
              {activeTab === 'prizes' && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold">獎品列表</h3>
                    <button
                      onClick={() => {
                        setEditingPrize(null);
                        setPrizeForm({
                          name: '',
                          description: '',
                          prize_type: 'physical',
                          prize_value: '',
                          total_quantity: 0,
                          probability: 0,
                          display_order: (selectedCampaign.prizes?.length || 0) + 1,
                        });
                        setShowPrizeModal(true);
                      }}
                      className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
                    >
                      <Plus className="w-4 h-4" />
                      新增獎品
                    </button>
                  </div>

                  <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="text-left px-4 py-3">獎品名稱</th>
                          <th className="text-center px-4 py-3">類型</th>
                          <th className="text-center px-4 py-3">數量</th>
                          <th className="text-center px-4 py-3">剩餘</th>
                          <th className="text-center px-4 py-3">機率</th>
                          <th className="text-center px-4 py-3">狀態</th>
                          <th className="text-center px-4 py-3">操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedCampaign.prizes?.map((prize) => (
                          <tr key={prize.id} className="border-t">
                            <td className="px-4 py-3">
                              <div className="font-medium">{prize.name}</div>
                              {prize.description && (
                                <div className="text-gray-500 text-xs">{prize.description}</div>
                              )}
                            </td>
                            <td className="text-center px-4 py-3">
                              {prizeTypeLabels[prize.prize_type]}
                            </td>
                            <td className="text-center px-4 py-3">{prize.total_quantity}</td>
                            <td className="text-center px-4 py-3">{prize.remaining_quantity}</td>
                            <td className="text-center px-4 py-3">{(prize.probability * 100).toFixed(2)}%</td>
                            <td className="text-center px-4 py-3">
                              {prize.is_active ? (
                                <span className="text-green-600">啟用</span>
                              ) : (
                                <span className="text-gray-400">停用</span>
                              )}
                            </td>
                            <td className="text-center px-4 py-3">
                              <div className="flex items-center justify-center gap-2">
                                <button
                                  onClick={() => {
                                    setEditingPrize(prize);
                                    setPrizeForm({
                                      name: prize.name,
                                      description: prize.description || '',
                                      prize_type: prize.prize_type,
                                      prize_value: prize.prize_value || '',
                                      total_quantity: prize.total_quantity,
                                      probability: prize.probability,
                                      display_order: prize.display_order,
                                    });
                                    setShowPrizeModal(true);
                                  }}
                                  className="text-blue-600 hover:text-blue-800"
                                >
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => deletePrize(prize.id)}
                                  className="text-red-600 hover:text-red-800"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                        {(!selectedCampaign.prizes || selectedCampaign.prizes.length === 0) && (
                          <tr>
                            <td colSpan={7} className="text-center py-8 text-gray-500">
                              尚未設定獎品
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Probability Summary */}
                  {selectedCampaign.prizes && selectedCampaign.prizes.length > 0 && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-yellow-800">
                        <Percent className="w-5 h-5" />
                        <span className="font-medium">
                          機率總和：{(selectedCampaign.prizes.reduce((sum, p) => sum + p.probability, 0) * 100).toFixed(2)}%
                        </span>
                        <span className="text-sm">
                          （剩餘 {((1 - selectedCampaign.prizes.reduce((sum, p) => sum + p.probability, 0)) * 100).toFixed(2)}% 為未中獎）
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Results Tab */}
              {activeTab === 'results' && (
                <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left px-4 py-3">時間</th>
                        <th className="text-left px-4 py-3">會員</th>
                        <th className="text-center px-4 py-3">結果</th>
                        <th className="text-left px-4 py-3">獎品</th>
                        <th className="text-left px-4 py-3">兌換碼</th>
                        <th className="text-center px-4 py-3">兌換狀態</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.map((result) => (
                        <tr key={result.id} className="border-t">
                          <td className="px-4 py-3 text-gray-500">
                            {new Date(result.scratched_at).toLocaleString('zh-TW')}
                          </td>
                          <td className="px-4 py-3">
                            <div>{result.lottery_participants?.customer_name || '-'}</div>
                            <div className="text-gray-500 text-xs">
                              {result.lottery_participants?.customer_email || result.lottery_participants?.shopline_customer_id}
                            </div>
                          </td>
                          <td className="text-center px-4 py-3">
                            {result.is_winner ? (
                              <span className="inline-flex items-center gap-1 text-green-600">
                                <CheckCircle className="w-4 h-4" />
                                中獎
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-gray-400">
                                <XCircle className="w-4 h-4" />
                                未中
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">{result.prize_name || '-'}</td>
                          <td className="px-4 py-3">
                            {result.redemption_code && (
                              <div className="flex items-center gap-1">
                                <code className="bg-gray-100 px-2 py-0.5 rounded text-xs">
                                  {result.redemption_code}
                                </code>
                                <button
                                  onClick={() => navigator.clipboard.writeText(result.redemption_code!)}
                                  className="text-gray-400 hover:text-gray-600"
                                >
                                  <Copy className="w-3 h-3" />
                                </button>
                              </div>
                            )}
                          </td>
                          <td className="text-center px-4 py-3">
                            {result.is_winner && (
                              result.is_redeemed ? (
                                <span className="text-green-600">已兌換</span>
                              ) : (
                                <span className="text-orange-600">未兌換</span>
                              )
                            )}
                          </td>
                        </tr>
                      ))}
                      {results.length === 0 && (
                        <tr>
                          <td colSpan={6} className="text-center py-8 text-gray-500">
                            尚無刮獎記錄
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </main>

        {/* Prize Modal */}
        {showPrizeModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <h3 className="text-lg font-semibold mb-4">
                  {editingPrize ? '編輯獎品' : '新增獎品'}
                </h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">獎品名稱 *</label>
                    <input
                      type="text"
                      value={prizeForm.name}
                      onChange={(e) => setPrizeForm({ ...prizeForm, name: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">說明</label>
                    <textarea
                      value={prizeForm.description}
                      onChange={(e) => setPrizeForm({ ...prizeForm, description: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg"
                      rows={2}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">獎品類型</label>
                    <select
                      value={prizeForm.prize_type}
                      onChange={(e) => setPrizeForm({ ...prizeForm, prize_type: e.target.value as Prize['prize_type'] })}
                      className="w-full px-3 py-2 border rounded-lg"
                    >
                      <option value="physical">實體商品</option>
                      <option value="coupon">折價券</option>
                      <option value="points">點數</option>
                      <option value="free_shipping">免運</option>
                      <option value="discount">折扣</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">獎品價值/代碼</label>
                    <input
                      type="text"
                      value={prizeForm.prize_value}
                      onChange={(e) => setPrizeForm({ ...prizeForm, prize_value: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg"
                      placeholder="例：100元折價券、COUPON2024"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">總數量 *</label>
                      <input
                        type="number"
                        value={prizeForm.total_quantity}
                        onChange={(e) => setPrizeForm({ ...prizeForm, total_quantity: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 border rounded-lg"
                        min={0}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">中獎機率 * (%)</label>
                      <input
                        type="number"
                        value={(prizeForm.probability * 100).toFixed(2)}
                        onChange={(e) => setPrizeForm({ ...prizeForm, probability: (parseFloat(e.target.value) || 0) / 100 })}
                        className="w-full px-3 py-2 border rounded-lg"
                        min={0}
                        max={100}
                        step={0.01}
                      />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-2 mt-6">
                  <button
                    onClick={() => setShowPrizeModal(false)}
                    className="px-4 py-2 text-gray-600 hover:text-gray-800"
                  >
                    取消
                  </button>
                  <button
                    onClick={savePrize}
                    disabled={!prizeForm.name || prizeForm.total_quantity <= 0}
                    className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
                  >
                    儲存
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Campaign list view
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-gray-500 hover:text-gray-700">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <Gift className="w-8 h-8 text-orange-500" />
            <h1 className="text-xl font-bold">刮刮樂管理後台</h1>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadCampaigns}
              className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              重新整理
            </button>
            <button
              onClick={() => {
                setEditingCampaign(null);
                setCampaignForm({
                  name: '',
                  description: '',
                  start_date: new Date().toISOString().slice(0, 16),
                  end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16),
                  max_attempts_per_user: 1,
                  require_login: true,
                });
                setShowCampaignModal(true);
              }}
              className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              新增活動
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
          </div>
        ) : campaigns.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Gift className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>尚未建立任何活動</p>
            <p className="text-sm">點擊右上角「新增活動」開始建立</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {campaigns.map((campaign) => (
              <div
                key={campaign.id}
                className="bg-white rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => loadCampaignDetails(campaign.id)}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold text-lg">{campaign.name}</h3>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[campaign.status]}`}>
                        {statusLabels[campaign.status]}
                      </span>
                    </div>
                    {campaign.description && (
                      <p className="text-gray-500 text-sm mb-2">{campaign.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {new Date(campaign.start_date).toLocaleDateString('zh-TW')} ~{' '}
                        {new Date(campaign.end_date).toLocaleDateString('zh-TW')}
                      </span>
                      <span>每人 {campaign.max_attempts_per_user} 次</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => {
                        setEditingCampaign(campaign);
                        setCampaignForm({
                          name: campaign.name,
                          description: campaign.description || '',
                          start_date: campaign.start_date.slice(0, 16),
                          end_date: campaign.end_date.slice(0, 16),
                          max_attempts_per_user: campaign.max_attempts_per_user,
                          require_login: campaign.require_login,
                        });
                        setShowCampaignModal(true);
                      }}
                      className="text-blue-600 hover:text-blue-800 p-2"
                    >
                      <Edit className="w-5 h-5" />
                    </button>
                    {campaign.status === 'draft' && (
                      <button
                        onClick={() => deleteCampaign(campaign.id)}
                        className="text-red-600 hover:text-red-800 p-2"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Campaign Modal */}
      {showCampaignModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h3 className="text-lg font-semibold mb-4">
                {editingCampaign ? '編輯活動' : '新增活動'}
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">活動名稱 *</label>
                  <input
                    type="text"
                    value={campaignForm.name}
                    onChange={(e) => setCampaignForm({ ...campaignForm, name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="例：新春刮刮樂"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">活動說明</label>
                  <textarea
                    value={campaignForm.description}
                    onChange={(e) => setCampaignForm({ ...campaignForm, description: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    rows={3}
                    placeholder="活動說明..."
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">開始時間 *</label>
                    <input
                      type="datetime-local"
                      value={campaignForm.start_date}
                      onChange={(e) => setCampaignForm({ ...campaignForm, start_date: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">結束時間 *</label>
                    <input
                      type="datetime-local"
                      value={campaignForm.end_date}
                      onChange={(e) => setCampaignForm({ ...campaignForm, end_date: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">每人可刮次數</label>
                  <input
                    type="number"
                    value={campaignForm.max_attempts_per_user}
                    onChange={(e) => setCampaignForm({ ...campaignForm, max_attempts_per_user: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border rounded-lg"
                    min={1}
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="require_login"
                    checked={campaignForm.require_login}
                    onChange={(e) => setCampaignForm({ ...campaignForm, require_login: e.target.checked })}
                    className="w-4 h-4 text-orange-500"
                  />
                  <label htmlFor="require_login" className="text-sm">
                    需要會員登入才能參加
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setShowCampaignModal(false)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  取消
                </button>
                <button
                  onClick={saveCampaign}
                  disabled={!campaignForm.name || !campaignForm.start_date || !campaignForm.end_date}
                  className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
                >
                  儲存
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
