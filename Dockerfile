# 使用 Python 3.12 基礎映像
FROM python:3.12

# 設置工作目錄
WORKDIR /app

# 複製需求文件到工作目錄
COPY requirements.txt .

# 安裝 Python 依賴包
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有源代碼到工作目錄
COPY . .

# 指定運行的主程序
CMD ["python", "c2c_main.py"]
