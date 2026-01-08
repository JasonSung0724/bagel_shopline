-- Create sales tables for tracking daily sales data

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create master_sales_products table
CREATE TABLE IF NOT EXISTS master_sales_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_name VARCHAR NOT NULL UNIQUE,
    category VARCHAR,
    first_seen_date DATE,
    last_seen_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for master_sales_products
CREATE INDEX IF NOT EXISTS ix_master_sales_products_product_name ON master_sales_products (product_name);
CREATE INDEX IF NOT EXISTS ix_master_sales_products_category ON master_sales_products (category);
CREATE INDEX IF NOT EXISTS ix_master_sales_products_is_active ON master_sales_products (is_active);

-- Create daily_sales table
CREATE TABLE IF NOT EXISTS daily_sales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sale_date DATE NOT NULL,
    product_name VARCHAR NOT NULL,
    category VARCHAR,
    quantity FLOAT NOT NULL DEFAULT 0,
    source VARCHAR DEFAULT 'flowtide_qc',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_daily_sales_date_product UNIQUE (sale_date, product_name)
);

-- Create indexes for daily_sales
CREATE INDEX IF NOT EXISTS ix_daily_sales_sale_date ON daily_sales (sale_date);
CREATE INDEX IF NOT EXISTS ix_daily_sales_product_name ON daily_sales (product_name);
CREATE INDEX IF NOT EXISTS ix_daily_sales_category ON daily_sales (category);

-- Enable Row Level Security (RLS)
ALTER TABLE master_sales_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_sales ENABLE ROW LEVEL SECURITY;

-- Create RLS policies to allow all operations for service role
CREATE POLICY "Allow all for service role" ON master_sales_products
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON daily_sales
    FOR ALL USING (true) WITH CHECK (true);

-- Add comments for documentation
COMMENT ON TABLE master_sales_products IS 'Master product list for sales tracking with auto-adaptive updates';
COMMENT ON TABLE daily_sales IS 'Daily sales records from A442_QC Excel files, tracking 訂單實出 (actual shipment quantity)';
COMMENT ON COLUMN daily_sales.quantity IS 'Actual shipment quantity from 訂單實出 field, supports zero-quantity records for historical products';
