import os
import requests
from flask import Flask, request
from c2c_main import fetch_email_by_date, GoogleSheetHandle, delivery_excel_handle, MessageSender, ShopLineOrderScripts
from src.config.config import ConfigManager
from loguru import logger

app = Flask(__name__)

proxy_url = os.environ.get("QUOTAGUARDSTATIC_URL")
proxies = {
    "http": proxy_url,
    "https": proxy_url,
}

@app.route("/flowtide_excel_handle", methods=["POST"])
def flowtide_excel_handle():
    custom_header = request.headers.get("X-Auth")
    if custom_header != "BagelShopC2C":
        return "Unauthorized", 401
    try:
        CONFIG = ConfigManager()
        msg = MessageSender()

        result = fetch_email_by_date(msg, CONFIG.flowtide_sender_email)
        c2c_order_status = delivery_excel_handle(result, msg, platform="c2c")
        sheet_handel = GoogleSheetHandle(c2c_order_status)
        sheet_handel.process_data_scripts(msg)

        shopline_order_scripts = ShopLineOrderScripts(mail_result=result, msg_instance=msg)
        shopline_order_scripts.run_scripts()

        msg.line_push_message()

        return "Task completed", 200

    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {e}", 500


@app.route("/shopline_outstanding_order_update", methods=["POST"])
def shopline_outstanding_order_update():
    custom_header = request.headers.get("X-Auth")
    if custom_header != "BagelShopC2C":
        return "Unauthorized", 401
    try:
        msg = MessageSender()
        shopline_order_scripts = ShopLineOrderScripts(msg_instance=msg)
        shopline_order_scripts.run_update_outstanding_shopline_order()

        return "Task completed", 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {e}", 500

@app.route("/return_ip", methods=["GET"])
def get_ip():
    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxies)
        return f"Server IP is: {response.json()['origin']}"
    except requests.RequestException as e:
        logger.error(f"Error fetching IP: {e}")
        return f"Error fetching IP: {e}", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
