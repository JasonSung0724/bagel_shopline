-- ============================================
-- Migration: 新增獎品顯示設定欄位
-- 日期: 2026-01-31
-- 說明:
--   1. show_on_frontend: 控制該獎品是否在前端顯示名稱和圖片
--   2. win_message: 中獎時顯示的自訂訊息
-- ============================================

-- 新增 show_on_frontend 欄位
ALTER TABLE lottery_prizes
ADD COLUMN IF NOT EXISTS show_on_frontend BOOLEAN DEFAULT false;

-- 新增 win_message 欄位
ALTER TABLE lottery_prizes
ADD COLUMN IF NOT EXISTS win_message TEXT;

-- 更新欄位註解
COMMENT ON COLUMN lottery_prizes.show_on_frontend IS '是否在前端顯示該獎品名稱和圖片';
COMMENT ON COLUMN lottery_prizes.win_message IS '中獎時顯示的自訂訊息';
