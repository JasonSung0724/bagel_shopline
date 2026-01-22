'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import {
  Gift,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  Copy,
  RefreshCw,
  LogIn,
  Sparkles,
} from 'lucide-react';

// API Base URL - this will be your backend server
const API_BASE_URL = '';

// Types
interface Campaign {
  id: string;
  name: string;
  description?: string;
  start_date: string;
  end_date: string;
  status: string;
  max_attempts_per_user: number;
  require_login: boolean;
  prizes?: {
    name: string;
    description?: string;
    prize_type: string;
    image_url?: string;
  }[];
}

interface ScratchResult {
  is_winner: boolean;
  prize?: {
    name: string;
    description?: string;
    prize_type: string;
    prize_value?: string;
    image_url?: string;
  };
  redemption_code?: string;
  message: string;
  attempts_remaining: number;
}

interface EligibilityCheck {
  eligible: boolean;
  reason?: string;
  campaign?: Campaign;
  attempts_used: number;
  attempts_remaining: number;
}

export default function LotteryScratchPage() {
  const params = useParams();
  const campaignId = params.campaignId as string;

  // State
  const [eligibility, setEligibility] = useState<EligibilityCheck | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isScratching, setIsScratching] = useState(false);
  const [scratchResult, setScratchResult] = useState<ScratchResult | null>(null);
  const [scratchProgress, setScratchProgress] = useState(0);
  const [isRevealed, setIsRevealed] = useState(false);
  const [copied, setCopied] = useState(false);

  // Canvas ref for scratch effect
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawing = useRef(false);

  // Get customer info from Shopline (will be injected via Liquid)
  const [customerId, setCustomerId] = useState<string | null>(null);
  const [customerEmail, setCustomerEmail] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState<string | null>(null);

  // Check for Shopline customer info on mount
  useEffect(() => {
    // Try to get customer info from window object (set by Shopline Liquid)
    const w = window as any;
    if (w.shoplineCustomer) {
      setCustomerId(w.shoplineCustomer.id || null);
      setCustomerEmail(w.shoplineCustomer.email || null);
      setCustomerName(w.shoplineCustomer.name || null);
    }

    // Also check URL params for testing
    const urlParams = new URLSearchParams(window.location.search);
    const testCustomerId = urlParams.get('customer_id');
    const testEmail = urlParams.get('email');
    const testName = urlParams.get('name');

    if (testCustomerId) setCustomerId(testCustomerId);
    if (testEmail) setCustomerEmail(testEmail);
    if (testName) setCustomerName(testName);
  }, []);

  // Check eligibility
  const checkEligibility = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (customerId) params.set('customer_id', customerId);

      const res = await fetch(`${API_BASE_URL}/api/lottery/campaigns/${campaignId}/check?${params}`);
      const data = await res.json();
      setEligibility(data);
    } catch (error) {
      console.error('Failed to check eligibility:', error);
      setEligibility({
        eligible: false,
        reason: '無法連線到伺服器',
        attempts_used: 0,
        attempts_remaining: 0,
      });
    } finally {
      setIsLoading(false);
    }
  }, [campaignId, customerId]);

  useEffect(() => {
    if (campaignId) {
      checkEligibility();
    }
  }, [campaignId, checkEligibility]);

  // Initialize scratch canvas
  const initScratchCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = canvas.offsetWidth * 2;
    canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);

    // Fill with scratch-off coating
    ctx.fillStyle = '#C0C0C0';
    ctx.fillRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);

    // Add shimmer effect
    const gradient = ctx.createLinearGradient(0, 0, canvas.offsetWidth, canvas.offsetHeight);
    gradient.addColorStop(0, 'rgba(255,255,255,0.3)');
    gradient.addColorStop(0.5, 'rgba(255,255,255,0)');
    gradient.addColorStop(1, 'rgba(255,255,255,0.3)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);

    // Add text
    ctx.fillStyle = '#888888';
    ctx.font = 'bold 20px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('刮開此處', canvas.offsetWidth / 2, canvas.offsetHeight / 2 - 10);
    ctx.font = '14px sans-serif';
    ctx.fillText('SCRATCH HERE', canvas.offsetWidth / 2, canvas.offsetHeight / 2 + 15);
  }, []);

  // Handle scratch
  const scratch = useCallback((x: number, y: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const canvasX = (x - rect.left) * scaleX / 2;
    const canvasY = (y - rect.top) * scaleY / 2;

    ctx.globalCompositeOperation = 'destination-out';
    ctx.beginPath();
    ctx.arc(canvasX, canvasY, 25, 0, Math.PI * 2);
    ctx.fill();

    // Calculate scratch progress
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    let transparent = 0;
    for (let i = 3; i < imageData.data.length; i += 4) {
      if (imageData.data[i] === 0) transparent++;
    }
    const progress = transparent / (imageData.data.length / 4);
    setScratchProgress(progress);

    // Auto-reveal if scratched enough
    if (progress > 0.5 && !isRevealed) {
      setIsRevealed(true);
    }
  }, [isRevealed]);

  // Mouse/Touch event handlers
  const handleStart = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (isRevealed) return;
    isDrawing.current = true;

    const pos = 'touches' in e
      ? { x: e.touches[0].clientX, y: e.touches[0].clientY }
      : { x: e.clientX, y: e.clientY };
    scratch(pos.x, pos.y);
  }, [scratch, isRevealed]);

  const handleMove = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing.current || isRevealed) return;

    const pos = 'touches' in e
      ? { x: e.touches[0].clientX, y: e.touches[0].clientY }
      : { x: e.clientX, y: e.clientY };
    scratch(pos.x, pos.y);
  }, [scratch, isRevealed]);

  const handleEnd = useCallback(() => {
    isDrawing.current = false;
  }, []);

  // Do scratch API call
  const doScratch = async () => {
    setIsScratching(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/lottery/campaigns/${campaignId}/scratch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_id: customerId,
          customer_email: customerEmail,
          customer_name: customerName,
        }),
      });

      const data = await res.json();

      if (data.success) {
        setScratchResult(data.result);
        // Initialize canvas after result is ready
        setTimeout(initScratchCanvas, 100);
      } else {
        setEligibility({
          eligible: false,
          reason: data.error || '刮獎失敗',
          attempts_used: eligibility?.attempts_used || 0,
          attempts_remaining: 0,
        });
      }
    } catch (error) {
      console.error('Failed to scratch:', error);
      setEligibility({
        eligible: false,
        reason: '無法連線到伺服器',
        attempts_used: eligibility?.attempts_used || 0,
        attempts_remaining: 0,
      });
    } finally {
      setIsScratching(false);
    }
  };

  // Copy redemption code
  const copyCode = () => {
    if (scratchResult?.redemption_code) {
      navigator.clipboard.writeText(scratchResult.redemption_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Reset for another try
  const resetScratch = () => {
    setScratchResult(null);
    setIsRevealed(false);
    setScratchProgress(0);
    checkEligibility();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-orange-50 to-orange-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-orange-500 mx-auto mb-4" />
          <p className="text-gray-600">載入中...</p>
        </div>
      </div>
    );
  }

  // Not eligible state
  if (!eligibility?.eligible && !scratchResult) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-orange-50 to-orange-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          {eligibility?.campaign?.require_login && !customerId ? (
            <>
              <LogIn className="w-16 h-16 text-orange-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-2">請先登入</h2>
              <p className="text-gray-600 mb-6">參加刮刮樂活動需要先登入會員</p>
              <a
                href="/users/sign_in"
                className="inline-block bg-orange-500 hover:bg-orange-600 text-white font-medium px-8 py-3 rounded-xl transition-colors"
              >
                登入會員
              </a>
            </>
          ) : (
            <>
              <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-2">無法參加</h2>
              <p className="text-gray-600 mb-6">{eligibility?.reason || '活動已結束或尚未開始'}</p>
              {eligibility?.campaign && (
                <div className="text-sm text-gray-500">
                  <p className="font-medium">{eligibility.campaign.name}</p>
                  <p>
                    活動期間：{new Date(eligibility.campaign.start_date).toLocaleDateString('zh-TW')} ~{' '}
                    {new Date(eligibility.campaign.end_date).toLocaleDateString('zh-TW')}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  // Ready to scratch state
  if (!scratchResult && eligibility?.eligible) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-orange-50 to-orange-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="mb-6">
            <Gift className="w-20 h-20 text-orange-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold mb-2">{eligibility.campaign?.name}</h1>
            {eligibility.campaign?.description && (
              <p className="text-gray-600">{eligibility.campaign.description}</p>
            )}
          </div>

          <div className="mb-6 p-4 bg-orange-50 rounded-xl">
            <p className="text-sm text-gray-600">
              您還有 <span className="font-bold text-orange-600">{eligibility.attempts_remaining}</span> 次刮獎機會
            </p>
          </div>

          {/* Prize showcase */}
          {eligibility.campaign?.prizes && eligibility.campaign.prizes.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-500 mb-3">獎品一覽</h3>
              <div className="flex flex-wrap justify-center gap-2">
                {eligibility.campaign.prizes.map((prize, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-700"
                  >
                    {prize.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={doScratch}
            disabled={isScratching}
            className="w-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white font-bold py-4 px-8 rounded-xl text-lg transition-all transform hover:scale-105 disabled:opacity-50 disabled:transform-none flex items-center justify-center gap-2"
          >
            {isScratching ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : (
              <>
                <Sparkles className="w-6 h-6" />
                開始刮獎！
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // Scratch card state
  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-50 to-orange-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-6 max-w-md w-full">
        <h2 className="text-xl font-bold text-center mb-4">{eligibility?.campaign?.name}</h2>

        {/* Scratch Card Area */}
        <div className="relative mb-6 rounded-xl overflow-hidden" style={{ aspectRatio: '16/9' }}>
          {/* Result layer (behind scratch layer) */}
          <div className={`absolute inset-0 flex items-center justify-center p-4 transition-opacity duration-500 ${
            isRevealed ? 'opacity-100' : 'opacity-0'
          }`}>
            {scratchResult?.is_winner ? (
              <div className="text-center">
                <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-2" />
                <h3 className="text-xl font-bold text-green-600 mb-1">恭喜中獎！</h3>
                <p className="text-lg font-medium">{scratchResult.prize?.name}</p>
              </div>
            ) : (
              <div className="text-center">
                <XCircle className="w-16 h-16 text-gray-400 mx-auto mb-2" />
                <h3 className="text-xl font-bold text-gray-600">再接再厲</h3>
                <p className="text-gray-500">下次一定會更幸運</p>
              </div>
            )}
          </div>

          {/* Scratch canvas layer */}
          {!isRevealed && (
            <canvas
              ref={canvasRef}
              className="absolute inset-0 w-full h-full cursor-crosshair touch-none"
              onMouseDown={handleStart}
              onMouseMove={handleMove}
              onMouseUp={handleEnd}
              onMouseLeave={handleEnd}
              onTouchStart={handleStart}
              onTouchMove={handleMove}
              onTouchEnd={handleEnd}
            />
          )}

          {/* Background */}
          <div className={`absolute inset-0 bg-gradient-to-br ${
            scratchResult?.is_winner
              ? 'from-yellow-100 to-orange-100'
              : 'from-gray-100 to-gray-200'
          } -z-10`} />
        </div>

        {/* Progress indicator */}
        {!isRevealed && scratchProgress > 0 && (
          <div className="mb-4">
            <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-orange-500 transition-all"
                style={{ width: `${Math.min(scratchProgress * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-center text-gray-500 mt-1">
              {scratchProgress < 0.5 ? '繼續刮！' : '快刮完了...'}
            </p>
          </div>
        )}

        {/* Result details */}
        {isRevealed && (
          <div className="space-y-4">
            {scratchResult?.is_winner && scratchResult.redemption_code && (
              <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                <p className="text-sm text-green-800 mb-2">您的兌換碼：</p>
                <div className="flex items-center justify-center gap-2">
                  <code className="text-xl font-mono font-bold text-green-600 bg-white px-4 py-2 rounded-lg">
                    {scratchResult.redemption_code}
                  </code>
                  <button
                    onClick={copyCode}
                    className="p-2 text-green-600 hover:text-green-800"
                    title="複製"
                  >
                    {copied ? <CheckCircle className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
                  </button>
                </div>
                <p className="text-xs text-green-700 mt-2 text-center">
                  請截圖保存此兌換碼，兌獎時出示
                </p>
              </div>
            )}

            {scratchResult?.prize?.description && (
              <p className="text-center text-gray-600">{scratchResult.prize.description}</p>
            )}

            <p className="text-center text-sm text-gray-500">{scratchResult?.message}</p>

            {scratchResult && scratchResult.attempts_remaining > 0 && (
              <button
                onClick={resetScratch}
                className="w-full bg-orange-500 hover:bg-orange-600 text-white font-medium py-3 px-6 rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-5 h-5" />
                再刮一次（剩餘 {scratchResult.attempts_remaining} 次）
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
