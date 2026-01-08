-- ============================================================
-- Migration: 001 - Create Sales Tables
-- Date: 2026-01-08
-- Description: 建立銷量系統資料表，記錄來自逢泰 A442_QC Excel 的實際銷量
-- ============================================================

-- 1. 銷量商品主檔（自適應新增商品）
-- ============================================================
CREATE TABLE IF NOT EXISTS master_sales_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_name VARCHAR UNIQUE NOT NULL,
    category VARCHAR,  -- 'bread' or 'box'
    first_seen_date DATE,  -- 第一次出現在 Excel 的日期
    last_seen_date DATE,   -- 最後一次出現在 Excel 的日期
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE master_sales_products IS '銷量商品主檔：自動記錄所有曾經出現在銷售 Excel 中的商品';
COMMENT ON COLUMN master_sales_products.product_name IS '商品名稱（來自 Excel「品名」欄位）';
COMMENT ON COLUMN master_sales_products.category IS '分類：bread（麵包）或 box（盒子）';
COMMENT ON COLUMN master_sales_products.first_seen_date IS '第一次出現在銷售記錄的日期';
COMMENT ON COLUMN master_sales_products.last_seen_date IS '最後一次出現在銷售記錄的日期';

-- 2. 每日銷量記錄
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_sales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sale_date DATE NOT NULL,
    product_name VARCHAR NOT NULL,
    category VARCHAR,  -- 'bread' or 'box'
    quantity FLOAT NOT NULL DEFAULT 0,  -- 允許為 0（表示當天沒有銷售）
    source VARCHAR DEFAULT 'flowtide_qc',  -- 資料來源
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_sale_date_product UNIQUE(sale_date, product_name)
);

COMMENT ON TABLE daily_sales IS '每日銷量記錄：記錄每天每個商品的實際銷量';
COMMENT ON COLUMN daily_sales.sale_date IS '銷售日期（來自 Excel「出貨日」欄位）';
COMMENT ON COLUMN daily_sales.product_name IS '商品名稱（來自 Excel「品名」欄位）';
COMMENT ON COLUMN daily_sales.quantity IS '銷量（來自 Excel「訂單實出」欄位，可以是 0）';
COMMENT ON COLUMN daily_sales.source IS '資料來源標記';

-- 3. 建立索引提升查詢效能
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_daily_sales_date ON daily_sales(sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_sales_product ON daily_sales(product_name);
CREATE INDEX IF NOT EXISTS idx_daily_sales_category ON daily_sales(category);
CREATE INDEX IF NOT EXISTS idx_master_sales_products_category ON master_sales_products(category);
CREATE INDEX IF NOT EXISTS idx_master_sales_products_active ON master_sales_products(is_active);

-- 4. 啟用 Row Level Security (RLS)
-- ============================================================
ALTER TABLE master_sales_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_sales ENABLE ROW LEVEL SECURITY;

-- 5. 建立 RLS 策略（允許所有操作，因為使用 service_role）
-- ============================================================
DROP POLICY IF EXISTS "Allow all for service role" ON master_sales_products;
CREATE POLICY "Allow all for service role" ON master_sales_products
FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all for service role" ON daily_sales;
CREATE POLICY "Allow all for service role" ON daily_sales
FOR ALL USING (true) WITH CHECK (true);
