-- =============================================
-- 刮刮樂系統資料表
-- 執行方式：在 Supabase Dashboard > SQL Editor 中執行此腳本
-- =============================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- 1. lottery_campaigns - 刮刮樂活動表
-- =============================================
CREATE TABLE IF NOT EXISTS lottery_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'ended')),
    max_attempts_per_user INTEGER DEFAULT 1,
    require_login BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for lottery_campaigns
CREATE INDEX IF NOT EXISTS ix_lottery_campaigns_status ON lottery_campaigns (status);
CREATE INDEX IF NOT EXISTS ix_lottery_campaigns_dates ON lottery_campaigns (start_date, end_date);

-- =============================================
-- 2. lottery_prizes - 獎品表
-- =============================================
CREATE TABLE IF NOT EXISTS lottery_prizes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES lottery_campaigns(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    prize_type VARCHAR(50) DEFAULT 'physical' CHECK (prize_type IN ('physical', 'coupon', 'points', 'free_shipping', 'discount', 'none')),
    prize_value VARCHAR(255),
    image_url TEXT,
    total_quantity INTEGER NOT NULL DEFAULT 0,
    remaining_quantity INTEGER NOT NULL DEFAULT 0,
    probability DECIMAL(5, 4) NOT NULL DEFAULT 0.0000,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_remaining_quantity CHECK (remaining_quantity >= 0),
    CONSTRAINT check_remaining_not_exceed_total CHECK (remaining_quantity <= total_quantity),
    CONSTRAINT check_probability_range CHECK (probability >= 0 AND probability <= 1)
);

-- Indexes for lottery_prizes
CREATE INDEX IF NOT EXISTS ix_lottery_prizes_campaign ON lottery_prizes (campaign_id);
CREATE INDEX IF NOT EXISTS ix_lottery_prizes_active ON lottery_prizes (campaign_id, is_active);

-- =============================================
-- 3. lottery_participants - 參與者記錄表
-- =============================================
CREATE TABLE IF NOT EXISTS lottery_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES lottery_campaigns(id) ON DELETE CASCADE,
    shopline_customer_id VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255),
    customer_name VARCHAR(255),
    attempt_count INTEGER DEFAULT 0,
    first_attempt_at TIMESTAMP,
    last_attempt_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_participant_campaign UNIQUE (campaign_id, shopline_customer_id)
);

-- Indexes for lottery_participants
CREATE INDEX IF NOT EXISTS ix_lottery_participants_campaign ON lottery_participants (campaign_id);
CREATE INDEX IF NOT EXISTS ix_lottery_participants_customer ON lottery_participants (shopline_customer_id);

-- =============================================
-- 4. lottery_results - 刮刮樂結果記錄表
-- =============================================
CREATE TABLE IF NOT EXISTS lottery_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES lottery_campaigns(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES lottery_participants(id) ON DELETE CASCADE,
    prize_id UUID REFERENCES lottery_prizes(id) ON DELETE SET NULL,
    prize_name VARCHAR(255),
    prize_type VARCHAR(50),
    redemption_code VARCHAR(100) UNIQUE,
    is_winner BOOLEAN DEFAULT false,
    is_redeemed BOOLEAN DEFAULT false,
    redeemed_at TIMESTAMP,
    redeemed_by VARCHAR(255),
    scratched_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for lottery_results
CREATE INDEX IF NOT EXISTS ix_lottery_results_campaign ON lottery_results (campaign_id);
CREATE INDEX IF NOT EXISTS ix_lottery_results_participant ON lottery_results (participant_id);
CREATE INDEX IF NOT EXISTS ix_lottery_results_prize ON lottery_results (prize_id);
CREATE INDEX IF NOT EXISTS ix_lottery_results_redemption_code ON lottery_results (redemption_code);
CREATE INDEX IF NOT EXISTS ix_lottery_results_redeemed ON lottery_results (is_redeemed, is_winner);

-- =============================================
-- 5. lottery_admin_logs - 管理操作日誌表
-- =============================================
CREATE TABLE IF NOT EXISTS lottery_admin_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES lottery_campaigns(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    performed_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for admin logs
CREATE INDEX IF NOT EXISTS ix_lottery_admin_logs_campaign ON lottery_admin_logs (campaign_id);
CREATE INDEX IF NOT EXISTS ix_lottery_admin_logs_action ON lottery_admin_logs (action);

-- =============================================
-- Enable Row Level Security (RLS)
-- =============================================
ALTER TABLE lottery_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE lottery_prizes ENABLE ROW LEVEL SECURITY;
ALTER TABLE lottery_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE lottery_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE lottery_admin_logs ENABLE ROW LEVEL SECURITY;

-- =============================================
-- RLS Policies - Allow all for service role
-- =============================================
DO $$
BEGIN
    -- lottery_campaigns
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'lottery_campaigns' AND policyname = 'Allow all for service role') THEN
        CREATE POLICY "Allow all for service role" ON lottery_campaigns FOR ALL USING (true) WITH CHECK (true);
    END IF;

    -- lottery_prizes
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'lottery_prizes' AND policyname = 'Allow all for service role') THEN
        CREATE POLICY "Allow all for service role" ON lottery_prizes FOR ALL USING (true) WITH CHECK (true);
    END IF;

    -- lottery_participants
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'lottery_participants' AND policyname = 'Allow all for service role') THEN
        CREATE POLICY "Allow all for service role" ON lottery_participants FOR ALL USING (true) WITH CHECK (true);
    END IF;

    -- lottery_results
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'lottery_results' AND policyname = 'Allow all for service role') THEN
        CREATE POLICY "Allow all for service role" ON lottery_results FOR ALL USING (true) WITH CHECK (true);
    END IF;

    -- lottery_admin_logs
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'lottery_admin_logs' AND policyname = 'Allow all for service role') THEN
        CREATE POLICY "Allow all for service role" ON lottery_admin_logs FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- =============================================
-- Comments for documentation
-- =============================================
COMMENT ON TABLE lottery_campaigns IS '刮刮樂活動表 - Scratch card lottery campaigns for Shopline stores';
COMMENT ON TABLE lottery_prizes IS '獎品表 - Available prizes for each lottery campaign';
COMMENT ON TABLE lottery_participants IS '參與者記錄 - Track users who participated in lottery campaigns';
COMMENT ON TABLE lottery_results IS '刮獎結果 - Individual scratch results and redemption records';
COMMENT ON TABLE lottery_admin_logs IS '管理日誌 - Admin action audit logs for lottery management';

COMMENT ON COLUMN lottery_prizes.probability IS '中獎機率 (0.0000 to 1.0000)';
COMMENT ON COLUMN lottery_prizes.prize_type IS '獎品類型: physical (實體商品), coupon (折價券), points (點數), free_shipping (免運), discount (折扣), none (未中獎)';
COMMENT ON COLUMN lottery_results.redemption_code IS '兌換碼 - Unique code for prize redemption verification';
COMMENT ON COLUMN lottery_participants.shopline_customer_id IS 'Shopline 會員 ID';

-- =============================================
-- 執行完成提示
-- =============================================
SELECT '刮刮樂資料表建立完成！' as message;
