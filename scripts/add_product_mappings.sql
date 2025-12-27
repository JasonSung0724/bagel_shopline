-- =============================================
-- Migration: Add product_mappings table
-- 產品對照表 (麵包與塑膠袋的對應關係)
-- =============================================
-- 請在 Supabase SQL Editor 執行此腳本

-- 建立對照表
CREATE TABLE IF NOT EXISTS product_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bread_name TEXT NOT NULL,              -- 麵包品名
    bag_name TEXT NOT NULL,                -- 對應的塑膠袋品名
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(bread_name, bag_name)           -- 確保不重複對應
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_mappings_bread ON product_mappings(bread_name);
CREATE INDEX IF NOT EXISTS idx_mappings_bag ON product_mappings(bag_name);

-- 啟用 RLS
ALTER TABLE product_mappings ENABLE ROW LEVEL SECURITY;

-- 建立權限政策
DO $$
BEGIN
    -- 檢查政策是否存在，不存在才建立
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'product_mappings' AND policyname = 'Allow all for authenticated') THEN
        CREATE POLICY "Allow all for authenticated" ON product_mappings
            FOR ALL TO authenticated USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'product_mappings' AND policyname = 'Allow all for service role') THEN
        CREATE POLICY "Allow all for service role" ON product_mappings
            FOR ALL TO service_role USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'product_mappings' AND policyname = 'Allow read for anon') THEN
        CREATE POLICY "Allow read for anon" ON product_mappings
            FOR SELECT TO anon USING (true);
    END IF;
END $$;

-- =============================================
-- 插入初始對照資料
-- 請根據實際品名調整
-- =============================================
INSERT INTO product_mappings (bread_name, bag_name) VALUES
    -- 範例對照 (請根據實際情況修改)
    ('低糖草莓乳酪貝果', '塑膠袋-低糖草莓乳酪貝果'),
    ('西西里開心果乳酪貝果', '塑膠袋-開心果乳酪貝果'),
    ('伯爵高蛋白奶酥能量貝果', '塑膠袋-伯爵奶酥貝果')
    -- 在這裡繼續新增其他對照...
ON CONFLICT (bread_name, bag_name) DO NOTHING;

-- =============================================
-- 查詢現有的麵包和塑膠袋品名 (幫助建立對照)
-- =============================================
-- 執行以下查詢來查看所有品名：

-- 查看所有麵包品名
-- SELECT DISTINCT name FROM inventory_items WHERE category = 'bread' ORDER BY name;

-- 查看所有塑膠袋品名
-- SELECT DISTINCT name FROM inventory_items WHERE category = 'bag' ORDER BY name;

-- 查看目前的對照關係
-- SELECT * FROM product_mappings ORDER BY bread_name;
