import os
from flask import Flask, request
from c2c_main import fetch_email_by_date, GoogleSheetHandle, delivery_excel_handle, MessageSender

app = Flask(__name__)

@app.route('/task', methods=['POST'])
def run_task():
    custom_header = request.headers.get('X-Auth')
    if custom_header != 'BagelShopC2C':
        return 'Unauthorized', 401
    msg = MessageSender()
    result = fetch_email_by_date()
    order_status = delivery_excel_handle(result)
    sheet_handel = GoogleSheetHandle(order_status)
    sheet_handel.process_data_scripts(msg)
    return 'Task completed', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
