-- Add 'link' prize type to lottery_prizes table
-- This allows prizes that redirect users to a URL to claim their reward

-- Drop the existing check constraint
ALTER TABLE lottery_prizes DROP CONSTRAINT IF EXISTS lottery_prizes_prize_type_check;

-- Add the new check constraint with 'link' type included
ALTER TABLE lottery_prizes ADD CONSTRAINT lottery_prizes_prize_type_check
    CHECK (prize_type IN ('physical', 'coupon', 'points', 'free_shipping', 'discount', 'none', 'link'));

-- Add comment for the new type
COMMENT ON COLUMN lottery_prizes.prize_type IS 'Type of prize: physical (實體商品), coupon (折價券), points (點數), free_shipping (免運), discount (折扣), link (兌獎連結), none (未中獎)';
