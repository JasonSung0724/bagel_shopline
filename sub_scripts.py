from c2c_main import ShopLineOrderScripts, MessageSender
from loguru import logger
import sys

# 配置日誌系統 - 按大小輪轉，只保留兩個禮拜的日誌
logger.remove()  # 移除預設的日誌處理器
logger.add(
    sys.stderr,  # 輸出到標準錯誤
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    "logs/sub.log",  # 單一檔案名稱
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="100 MB",  # 當檔案超過100MB時輪轉
    retention="14 days",  # 保留14天（兩個禮拜）
    compression="zip",  # 壓縮舊日誌檔案
    encoding="utf-8",
)

if __name__ == "__main__":
    msg = MessageSender()
    shopline_order_scripts = ShopLineOrderScripts(msg_instance=msg, notify=True)
    shopline_order_scripts.run_update_outstanding_shopline_order()
