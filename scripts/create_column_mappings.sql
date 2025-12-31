-- Create unified column_mappings table (replaces platform_configs)
-- This table stores field-to-aliases mappings that apply to ALL platforms

CREATE TABLE IF NOT EXISTS column_mappings (
    field_name TEXT PRIMARY KEY,
    aliases JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert unified mappings (combining all platform aliases)
-- order_id
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'order_id',
    '["訂單號碼", "order_id", "*銷售單號", "平台訂單編號"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- order_date
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'order_date',
    '["訂單日期", "order_date", "建立時間", "訂單日期(年月日)"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- receiver_name
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'receiver_name',
    '["收件人姓名", "receiver_name", "收件人", "顧客姓名"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- receiver_phone
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'receiver_phone',
    '["收件人電話號碼", "receiver_phone", "收件人電話", "收件人手機", "電話"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- receiver_address
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'receiver_address',
    '["收件人地址", "receiver_address", "送貨地址", "地址", "Address", "收件地址"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- delivery_method
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'delivery_method',
    '["送貨方式", "delivery_method", "配送方式"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- store_name
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'store_name',
    '["門市名稱", "store_name", "取貨門市"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- product_code
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'product_code',
    '["商品貨號", "product_code", "商品編號", "貨號"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- product_name
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'product_name',
    '["商品名稱", "product_name", "選項", "品名/規格", "商品樣式"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- quantity
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'quantity',
    '["訂購數量", "product_quantity", "數量", "qty"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- order_mark
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'order_mark',
    '["送貨備註", "order_mark", "備註", "出貨備註", "客戶備註", "訂單備註"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- arrival_time
INSERT INTO column_mappings (field_name, aliases)
VALUES (
    'arrival_time',
    '["到貨時段", "arrival_time", "配送時段"]'
) ON CONFLICT (field_name) DO UPDATE SET aliases = EXCLUDED.aliases, updated_at = NOW();

-- Remove old platform_configs table (no longer needed)
DROP TABLE IF EXISTS platform_configs;
