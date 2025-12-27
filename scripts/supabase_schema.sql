-- =============================================
-- Supabase Schema for Inventory Management
-- =============================================
-- Run this in Supabase SQL Editor to create the required tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- Table: inventory_snapshots
-- 庫存快照主表 (每個 Excel 檔案一筆)
-- =============================================
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_date TIMESTAMPTZ NOT NULL,
    source_file TEXT,
    source_email_date TIMESTAMPTZ,
    total_bread_stock INTEGER DEFAULT 0,
    total_box_stock INTEGER DEFAULT 0,
    total_bag_rolls INTEGER DEFAULT 0,
    low_stock_count INTEGER DEFAULT 0,
    raw_item_count INTEGER DEFAULT 0,  -- 原始資料筆數
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for date queries
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON inventory_snapshots(snapshot_date DESC);

-- =============================================
-- Table: inventory_raw_items
-- Excel 原始資料 (每一列完整保留)
-- =============================================
CREATE TABLE IF NOT EXISTS inventory_raw_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_id UUID NOT NULL REFERENCES inventory_snapshots(id) ON DELETE CASCADE,

    -- Excel 原始欄位 (完整保留)
    product_name TEXT NOT NULL,           -- 品名
    spec TEXT,                            -- 主檔規格
    box_quantity INTEGER,                 -- 主檔箱入數
    expiry_date TEXT,                     -- 效期 (保留原始格式)
    warehouse_date TEXT,                  -- 入倉日期
    unit TEXT,                            -- 單位
    opening_stock NUMERIC DEFAULT 0,      -- 期初
    stock_in NUMERIC DEFAULT 0,           -- 入庫
    stock_out NUMERIC DEFAULT 0,          -- 出庫
    closing_stock NUMERIC DEFAULT 0,      -- 期末
    unbilled_quantity NUMERIC DEFAULT 0,  -- 未扣帳量
    pending_shipment NUMERIC DEFAULT 0,   -- 待出貨量
    available_stock NUMERIC DEFAULT 0,    -- 預計可用量
    warehouse_code TEXT,                  -- 庫別
    customer_accept_days INTEGER,         -- 客戶端允收天數
    customer_accept_date TEXT,            -- 客戶端允收日期
    customer_receivable_days INTEGER,     -- 客戶端可收天數
    expiry_warning TEXT,                  -- 效期警示
    initial_stock_id TEXT,                -- 初始庫存編號
    initial_warehouse_order TEXT,         -- 初始入倉單號
    initial_warehouse_date TEXT,          -- 初始入倉日期
    initial_warehouse_quantity NUMERIC,   -- 初始入倉數量
    stock_id TEXT,                        -- 庫存編號
    product_batch TEXT,                   -- 商品批號
    storage_location TEXT,                -- 儲位
    pallet_number TEXT,                   -- 板號
    last_warehouse_order TEXT,            -- 最後入倉單號
    last_warehouse_date TEXT,             -- 最後入倉日期
    last_warehouse_quantity NUMERIC,      -- 最後入倉數量
    data_date TEXT,                       -- 資料日期

    -- 額外欄位 (系統用)
    row_number INTEGER,                   -- Excel 原始列號
    raw_data JSONB,                       -- 完整原始資料 (備用，未來欄位變更可用)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw items
CREATE INDEX IF NOT EXISTS idx_raw_items_snapshot ON inventory_raw_items(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_raw_items_product ON inventory_raw_items(product_name);
CREATE INDEX IF NOT EXISTS idx_raw_items_warehouse ON inventory_raw_items(warehouse_code);

-- =============================================
-- Table: inventory_items
-- 彙總後的庫存項目 (按品名彙總)
-- =============================================
CREATE TABLE IF NOT EXISTS inventory_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_id UUID NOT NULL REFERENCES inventory_snapshots(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('bread', 'box', 'bag', 'other')),
    current_stock INTEGER NOT NULL DEFAULT 0,
    available_stock INTEGER NOT NULL DEFAULT 0,
    unit TEXT NOT NULL DEFAULT '個',
    min_stock INTEGER NOT NULL DEFAULT 0,
    items_per_roll INTEGER,
    stock_status TEXT CHECK (stock_status IN ('high', 'medium', 'low')),
    batch_count INTEGER DEFAULT 1,  -- 此品名有幾批貨
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for snapshot queries
CREATE INDEX IF NOT EXISTS idx_items_snapshot ON inventory_items(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_items_category ON inventory_items(category);
CREATE INDEX IF NOT EXISTS idx_items_name ON inventory_items(name);

-- =============================================
-- Table: inventory_changes
-- 庫存變動記錄
-- =============================================
CREATE TABLE IF NOT EXISTS inventory_changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    item_name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('bread', 'box', 'bag', 'other')),
    previous_stock INTEGER NOT NULL DEFAULT 0,
    new_stock INTEGER NOT NULL DEFAULT 0,
    change_amount INTEGER NOT NULL DEFAULT 0,
    source TEXT DEFAULT 'email',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for date queries
CREATE INDEX IF NOT EXISTS idx_changes_date ON inventory_changes(date DESC);
CREATE INDEX IF NOT EXISTS idx_changes_item ON inventory_changes(item_name);

-- =============================================
-- Row Level Security (RLS)
-- =============================================
-- Enable RLS on all tables
ALTER TABLE inventory_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_raw_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_changes ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users (or service role)
-- For development, allow all operations
CREATE POLICY "Allow all for authenticated" ON inventory_snapshots
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for authenticated" ON inventory_raw_items
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for authenticated" ON inventory_items
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for authenticated" ON inventory_changes
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- For service role (used by backend)
CREATE POLICY "Allow all for service role" ON inventory_snapshots
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON inventory_raw_items
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON inventory_items
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON inventory_changes
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- For anon access (read-only for frontend)
CREATE POLICY "Allow read for anon" ON inventory_snapshots
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow read for anon" ON inventory_raw_items
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow read for anon" ON inventory_items
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow read for anon" ON inventory_changes
    FOR SELECT TO anon USING (true);

-- =============================================
-- Table: master_breads
-- 麵包主檔 (所有麵包品項)
-- =============================================
CREATE TABLE IF NOT EXISTS master_breads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,             -- 麵包品名
    code TEXT,                             -- 編號 (可為空)
    is_active BOOLEAN DEFAULT true,        -- 是否啟用
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_master_breads_name ON master_breads(name);
CREATE INDEX IF NOT EXISTS idx_master_breads_code ON master_breads(code);

ALTER TABLE master_breads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for authenticated" ON master_breads
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON master_breads
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow read for anon" ON master_breads
    FOR SELECT TO anon USING (true);

-- =============================================
-- Table: master_bags
-- 塑膠袋主檔 (所有塑膠袋品項)
-- =============================================
CREATE TABLE IF NOT EXISTS master_bags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,             -- 塑膠袋品名
    code TEXT,                             -- 編號 (可為空)
    is_active BOOLEAN DEFAULT true,        -- 是否啟用
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_master_bags_name ON master_bags(name);
CREATE INDEX IF NOT EXISTS idx_master_bags_code ON master_bags(code);

ALTER TABLE master_bags ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for authenticated" ON master_bags
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON master_bags
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow read for anon" ON master_bags
    FOR SELECT TO anon USING (true);

-- =============================================
-- Table: master_boxes
-- 箱子主檔 (所有箱子品項)
-- =============================================
CREATE TABLE IF NOT EXISTS master_boxes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,             -- 箱子品名
    code TEXT,                             -- 編號 (可為空)
    is_active BOOLEAN DEFAULT true,        -- 是否啟用
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_master_boxes_name ON master_boxes(name);
CREATE INDEX IF NOT EXISTS idx_master_boxes_code ON master_boxes(code);

ALTER TABLE master_boxes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for authenticated" ON master_boxes
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON master_boxes
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Allow read for anon" ON master_boxes
    FOR SELECT TO anon USING (true);

-- =============================================
-- Table: product_mappings
-- 產品對照表 (麵包與塑膠袋的對應關係)
-- 使用外鍵關聯到主檔
-- =============================================
CREATE TABLE IF NOT EXISTS product_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bread_id UUID REFERENCES master_breads(id) ON DELETE CASCADE,
    bag_id UUID REFERENCES master_bags(id) ON DELETE CASCADE,
    bread_name TEXT NOT NULL,              -- 麵包品名 (冗餘欄位，方便查詢)
    bag_name TEXT NOT NULL,                -- 對應的塑膠袋品名 (冗餘欄位)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(bread_name, bag_name)           -- 確保不重複對應
);

-- Indexes for product mappings
CREATE INDEX IF NOT EXISTS idx_mappings_bread ON product_mappings(bread_name);
CREATE INDEX IF NOT EXISTS idx_mappings_bag ON product_mappings(bag_name);
CREATE INDEX IF NOT EXISTS idx_mappings_bread_id ON product_mappings(bread_id);
CREATE INDEX IF NOT EXISTS idx_mappings_bag_id ON product_mappings(bag_id);

-- Enable RLS
ALTER TABLE product_mappings ENABLE ROW LEVEL SECURITY;

-- Policies for product_mappings
CREATE POLICY "Allow all for authenticated" ON product_mappings
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON product_mappings
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow read for anon" ON product_mappings
    FOR SELECT TO anon USING (true);

-- =============================================
-- Helper Functions
-- =============================================

-- Function to get latest snapshot with aggregated items
CREATE OR REPLACE FUNCTION get_latest_inventory()
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'snapshot', row_to_json(s),
        'bread_items', (
            SELECT json_agg(row_to_json(i))
            FROM inventory_items i
            WHERE i.snapshot_id = s.id AND i.category = 'bread'
        ),
        'box_items', (
            SELECT json_agg(row_to_json(i))
            FROM inventory_items i
            WHERE i.snapshot_id = s.id AND i.category = 'box'
        ),
        'bag_items', (
            SELECT json_agg(row_to_json(i))
            FROM inventory_items i
            WHERE i.snapshot_id = s.id AND i.category = 'bag'
        )
    ) INTO result
    FROM inventory_snapshots s
    ORDER BY s.snapshot_date DESC
    LIMIT 1;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to get raw items for a specific product
CREATE OR REPLACE FUNCTION get_product_batches(p_product_name TEXT, p_snapshot_id UUID DEFAULT NULL)
RETURNS JSON AS $$
DECLARE
    result JSON;
    target_snapshot_id UUID;
BEGIN
    -- Use provided snapshot_id or get latest
    IF p_snapshot_id IS NULL THEN
        SELECT id INTO target_snapshot_id
        FROM inventory_snapshots
        ORDER BY snapshot_date DESC
        LIMIT 1;
    ELSE
        target_snapshot_id := p_snapshot_id;
    END IF;

    SELECT json_agg(row_to_json(r))
    INTO result
    FROM inventory_raw_items r
    WHERE r.snapshot_id = target_snapshot_id
      AND r.product_name = p_product_name
    ORDER BY r.expiry_date;

    RETURN result;
END;
$$ LANGUAGE plpgsql;
