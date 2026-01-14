#!/bin/bash
# Frontend 重建腳本 - 解決 Server Action 錯誤

set -e

echo "🧹 清理 Frontend 構建快取..."

# 停止並刪除 frontend 容器
echo "停止 frontend 容器..."
docker-compose stop frontend || true
docker-compose rm -f frontend || true

# 刪除舊的 image
echo "刪除舊的 frontend image..."
docker rmi bagel/frontend:latest || true

# 清理本地構建快取
echo "清理本地 .next 目錄..."
rm -rf frontend/.next
rm -rf frontend/out
rm -rf frontend/.turbo
rm -rf frontend/node_modules/.cache

echo "🔨 重新構建 Frontend..."

# 重新構建（不使用快取）
docker-compose build --no-cache frontend

echo "🚀 啟動 Frontend..."
docker-compose up -d frontend

echo "✅ Frontend 重建完成！"
echo ""
echo "請執行以下步驟："
echo "1. 清除瀏覽器快取 (Ctrl+Shift+R 或 Cmd+Shift+R)"
echo "2. 或在無痕模式下開啟"
echo "3. 如果問題持續，請執行: docker-compose logs -f frontend"
