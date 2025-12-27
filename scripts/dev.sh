#!/bin/bash
# ===========================================
# 開發環境啟動/停止/重啟腳本
# Usage:
#   ./scripts/dev.sh start   - 啟動前後端
#   ./scripts/dev.sh stop    - 停止前後端
#   ./scripts/dev.sh restart - 重啟前後端
#   ./scripts/dev.sh status  - 查看狀態
# ===========================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
FLASK_PORT=8082
NEXT_PORT=3001
FLASK_LOG="/tmp/flask.log"
NEXT_LOG="/tmp/next.log"

# 顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_port() {
    lsof -i :$1 > /dev/null 2>&1
}

get_pid_on_port() {
    lsof -ti :$1 2>/dev/null
}

start_backend() {
    echo -e "${YELLOW}啟動後端 Flask (port $FLASK_PORT)...${NC}"
    if check_port $FLASK_PORT; then
        echo -e "${GREEN}後端已在運行中${NC}"
        return 0
    fi

    # 檢查虛擬環境
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}虛擬環境不存在: $VENV_DIR${NC}"
        echo -e "${YELLOW}請先建立虛擬環境: python3 -m venv venv${NC}"
        return 1
    fi

    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    PORT=$FLASK_PORT nohup python app.py > "$FLASK_LOG" 2>&1 &
    sleep 2
    if check_port $FLASK_PORT; then
        echo -e "${GREEN}後端啟動成功 - http://127.0.0.1:$FLASK_PORT${NC}"
    else
        echo -e "${RED}後端啟動失敗，查看日誌: $FLASK_LOG${NC}"
        tail -20 "$FLASK_LOG"
        return 1
    fi
}

start_frontend() {
    echo -e "${YELLOW}啟動前端 Next.js (port $NEXT_PORT)...${NC}"
    if check_port $NEXT_PORT; then
        echo -e "${GREEN}前端已在運行中${NC}"
        return 0
    fi
    cd "$PROJECT_DIR/frontend"
    nohup npm run dev > "$NEXT_LOG" 2>&1 &
    sleep 3
    if check_port $NEXT_PORT; then
        echo -e "${GREEN}前端啟動成功 - http://localhost:$NEXT_PORT${NC}"
    else
        echo -e "${RED}前端啟動失敗，查看日誌: $NEXT_LOG${NC}"
        tail -20 "$NEXT_LOG"
        return 1
    fi
}

stop_backend() {
    echo -e "${YELLOW}停止後端...${NC}"
    local pid=$(get_pid_on_port $FLASK_PORT)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null
        sleep 1
        if check_port $FLASK_PORT; then
            kill -9 $pid 2>/dev/null
        fi
        echo -e "${GREEN}後端已停止${NC}"
    else
        echo -e "${YELLOW}後端未在運行${NC}"
    fi
}

stop_frontend() {
    echo -e "${YELLOW}停止前端...${NC}"
    local pid=$(get_pid_on_port $NEXT_PORT)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null
        sleep 1
        if check_port $NEXT_PORT; then
            kill -9 $pid 2>/dev/null
        fi
        echo -e "${GREEN}前端已停止${NC}"
    else
        echo -e "${YELLOW}前端未在運行${NC}"
    fi
    # 確保 node 進程也被清理
    pkill -f "next dev" 2>/dev/null || true
}

show_status() {
    echo ""
    echo "=================================="
    echo "       服務狀態"
    echo "=================================="

    if check_port $FLASK_PORT; then
        echo -e "後端 Flask (port $FLASK_PORT): ${GREEN}運行中${NC}"
    else
        echo -e "後端 Flask (port $FLASK_PORT): ${RED}已停止${NC}"
    fi

    if check_port $NEXT_PORT; then
        echo -e "前端 Next.js (port $NEXT_PORT): ${GREEN}運行中${NC}"
    else
        echo -e "前端 Next.js (port $NEXT_PORT): ${RED}已停止${NC}"
    fi
    echo "=================================="
    echo ""
}

case "$1" in
    start)
        echo ""
        echo "=================================="
        echo "   啟動開發環境"
        echo "=================================="
        start_backend
        start_frontend
        show_status
        ;;
    stop)
        echo ""
        echo "=================================="
        echo "   停止開發環境"
        echo "=================================="
        stop_frontend
        stop_backend
        show_status
        ;;
    restart)
        echo ""
        echo "=================================="
        echo "   重啟開發環境"
        echo "=================================="
        stop_frontend
        stop_backend
        sleep 2
        start_backend
        start_frontend
        show_status
        ;;
    status)
        show_status
        ;;
    logs)
        echo "後端日誌 (最後 30 行):"
        echo "=================================="
        tail -30 "$FLASK_LOG" 2>/dev/null || echo "無日誌"
        echo ""
        echo "前端日誌 (最後 30 行):"
        echo "=================================="
        tail -30 "$NEXT_LOG" 2>/dev/null || echo "無日誌"
        ;;
    *)
        echo "使用方式: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "  start   - 啟動前後端服務"
        echo "  stop    - 停止前後端服務"
        echo "  restart - 重啟前後端服務"
        echo "  status  - 查看服務狀態"
        echo "  logs    - 查看日誌"
        exit 1
        ;;
esac
