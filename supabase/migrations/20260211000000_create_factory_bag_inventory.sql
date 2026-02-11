-- Create factory bag inventory tables for manual tracking of bags at factory
-- This tracks plastic bag inventory at the contract factory (代工廠)

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create factory_bag_inventory table (current inventory state)
CREATE TABLE IF NOT EXISTS factory_bag_inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bag_name VARCHAR NOT NULL UNIQUE,           -- 塑膠袋名稱 (from master_bags)
    quantity INT NOT NULL DEFAULT 0,            -- 目前數量（以卷為單位）
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create factory_bag_inventory_logs table (edit history)
CREATE TABLE IF NOT EXISTS factory_bag_inventory_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bag_name VARCHAR NOT NULL,                  -- 塑膠袋名稱
    quantity INT NOT NULL,                      -- 更新後的數量
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(), -- 記錄時間
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_factory_bag_inventory_bag_name ON factory_bag_inventory (bag_name);
CREATE INDEX IF NOT EXISTS ix_factory_bag_inventory_logs_bag_name ON factory_bag_inventory_logs (bag_name);
CREATE INDEX IF NOT EXISTS ix_factory_bag_inventory_logs_recorded_at ON factory_bag_inventory_logs (recorded_at);

-- Enable Row Level Security (RLS)
ALTER TABLE factory_bag_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE factory_bag_inventory_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies to allow all operations for service role
CREATE POLICY "Allow all for service role" ON factory_bag_inventory
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON factory_bag_inventory_logs
    FOR ALL USING (true) WITH CHECK (true);

-- Add comments for documentation
COMMENT ON TABLE factory_bag_inventory IS '代工廠塑膠袋庫存 - 人工輸入的代工廠塑膠袋數量（以卷為單位）';
COMMENT ON TABLE factory_bag_inventory_logs IS '代工廠塑膠袋庫存編輯歷程 - 記錄每次更新的時間與數量';
COMMENT ON COLUMN factory_bag_inventory.bag_name IS '塑膠袋名稱，對應 master_bags 表';
COMMENT ON COLUMN factory_bag_inventory.quantity IS '目前數量（以卷為單位）';
COMMENT ON COLUMN factory_bag_inventory_logs.quantity IS '更新後的數量（以卷為單位）';
COMMENT ON COLUMN factory_bag_inventory_logs.recorded_at IS '記錄時間';
