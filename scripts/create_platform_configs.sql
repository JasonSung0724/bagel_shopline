-- Create platform_configs table
CREATE TABLE IF NOT EXISTS platform_configs (
    platform TEXT PRIMARY KEY,
    mapping JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert Default Mappings
-- Shopline
INSERT INTO platform_configs (platform, mapping)
VALUES (
    'shopline',
    '{
        "order_id": ["訂單號碼", "order_id"],
        "order_date": ["訂單日期", "order_date"],
        "receiver_name": ["收件人姓名", "receiver_name"],
        "receiver_phone": ["收件人電話號碼", "receiver_phone"],
        "receiver_address": ["收件人地址", "receiver_address", "送貨地址", "地址", "Address"],
        "delivery_method": ["送貨方式", "delivery_method"],
        "store_name": ["門市名稱", "store_name"],
        "product_code": ["商品貨號", "product_code"],
        "product_name": ["商品名稱", "product_name", "選項"],
        "quantity": ["訂購數量", "product_quantity"],
        "order_mark": ["送貨備註", "order_mark"],
        "arrival_time": ["到貨時段", "arrival_time"]
    }'
) ON CONFLICT (platform) DO UPDATE SET mapping = EXCLUDED.mapping;

-- Mixx
INSERT INTO platform_configs (platform, mapping)
VALUES (
    'mixx',
    '{
        "order_id": ["*銷售單號"],
        "order_date": [], 
        "receiver_name": ["收件人姓名"],
        "receiver_phone": ["收件人電話"],
        "receiver_address": ["收件地址"],
        "product_name": ["品名/規格"],
        "quantity": ["數量"],
        "order_mark": ["備註"]
    }'
) ON CONFLICT (platform) DO UPDATE SET mapping = EXCLUDED.mapping;

-- C2C
INSERT INTO platform_configs (platform, mapping)
VALUES (
    'c2c',
    '{
        "order_id": ["平台訂單編號"],
        "order_date": ["建立時間"],
        "receiver_name": ["收件人姓名"],
        "receiver_phone": ["收件人手機"],
        "receiver_address": ["收件人地址"],
        "product_code": ["商品編號"],
        "product_name": ["商品樣式"],
        "quantity": ["訂購數量"],
        "order_mark": ["出貨備註"]
    }'
) ON CONFLICT (platform) DO UPDATE SET mapping = EXCLUDED.mapping;

-- Aoshi
INSERT INTO platform_configs (platform, mapping)
VALUES (
    'aoshi',
    '{
        "order_id": ["訂單號碼"],
        "order_date": ["訂單日期(年月日)"],
        "receiver_name": ["收件人姓名"],
        "receiver_phone": ["收件人電話"],
        "receiver_address": ["收件人地址"],
        "product_name": ["商品名稱"],
        "quantity": ["數量"],
        "order_mark": ["客戶備註"]
    }'
) ON CONFLICT (platform) DO UPDATE SET mapping = EXCLUDED.mapping;
