import os
import requests
from flask import Flask, request
from c2c_main import fetch_email_by_date, GoogleSheetHandle, delivery_excel_handle, MessageSender, ShopLineOrderScripts
from src.config.config import ConfigManager

app = Flask(__name__)


@app.route("/flowtide_excel_handle", methods=["POST"])
def run_task():
    custom_header = request.headers.get("X-Auth")
    if custom_header != "BagelShopC2C":
        return "Unauthorized", 401
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

@app.route("/shopline_outstanding_order_update", methods=["POST"])
def run_task():
    custom_header = request.headers.get("X-Auth")
    if custom_header != "BagelShopC2C":
        return "Unauthorized", 401
    CONFIG = ConfigManager()
    
    shopline_order_scripts = ShopLineOrderScripts()
    shopline_order_scripts.run_update_outstanding_shopline_order()

    return "Task completed", 200

@app.route("/return_ip", methods=["GET"])
def get_ip():
    response = requests.get("https://httpbin.org/ip")
    return f"Your IP is: {response.json()['origin']}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
