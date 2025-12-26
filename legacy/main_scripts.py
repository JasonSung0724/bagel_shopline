from c2c_main import fetch_email_by_date, delivery_excel_handle, GoogleSheetHandle, ShopLineOrderScripts, MessageSender, ConfigManager
import datetime
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
    "logs/app.log",  # 單一檔案名稱
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="100 MB",  # 當檔案超過100MB時輪轉
    retention="14 days",  # 保留14天（兩個禮拜）
    compression="zip",  # 壓縮舊日誌檔案
    encoding="utf-8",
)

if __name__ == "__main__":
    CONFIG = ConfigManager()
    msg = MessageSender()
    date = datetime.datetime.now() - datetime.timedelta(days=1)
    result = fetch_email_by_date(msg, CONFIG.flowtide_sender_email, date)
    c2c_order_status = delivery_excel_handle(result, msg, platform="c2c")
    sheet_handel = GoogleSheetHandle(c2c_order_status)
    sheet_handel.process_data_scripts(msg)

    shopline_order_scripts = ShopLineOrderScripts(mail_result=result, msg_instance=msg, notify=True)
    shopline_order_scripts.run_scripts()

    msg.line_push_message()
