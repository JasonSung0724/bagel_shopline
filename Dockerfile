# 使用 Python 3.12 基礎映像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 安裝 Playwright 所需的系統依賴
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    xvfb \
    # 清理 apt 快取以減少映像大小
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 複製並安裝 Python 依賴
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

CMD ["python", "app.py"]
