-- Add frontend_notice column to lottery_campaigns table
-- This field allows admins to set a notice that will be displayed
-- on the Shopline scratch card page for all prizes

ALTER TABLE lottery_campaigns
ADD COLUMN IF NOT EXISTS frontend_notice TEXT;

COMMENT ON COLUMN lottery_campaigns.frontend_notice IS 'Notice text to display on the Shopline scratch card frontend page';
