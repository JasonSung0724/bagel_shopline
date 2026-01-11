-- Add defective stock columns to inventory tables
-- This migration adds columns to track defective/damaged inventory separately

-- Add defective stock totals to inventory_snapshots table
ALTER TABLE inventory_snapshots
ADD COLUMN IF NOT EXISTS total_bread_defective INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_box_defective INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_bag_defective INTEGER DEFAULT 0;

-- Add defective stock to inventory_items table
ALTER TABLE inventory_items
ADD COLUMN IF NOT EXISTS defective_stock INTEGER DEFAULT 0;

-- Add comments for documentation
COMMENT ON COLUMN inventory_snapshots.total_bread_defective IS 'Total defective bread stock (items in defective warehouse)';
COMMENT ON COLUMN inventory_snapshots.total_box_defective IS 'Total defective box stock (items in defective warehouse)';
COMMENT ON COLUMN inventory_snapshots.total_bag_defective IS 'Total defective bag stock in rolls (items in defective warehouse)';
COMMENT ON COLUMN inventory_items.defective_stock IS 'Defective stock count for this item (from warehouse code containing 不良品)';
