import os
from flask import Flask, request
from c2c_main import fetch_email_by_date, google_sheet_handle, delivery_excel_handle

app = Flask(__name__)

@app.route('/task', methods=['POST'])
def run_task():
    custom_header = request.headers.get('X-Auth')
    if custom_header != 'BagelShopC2C':
        return 'Unauthorized', 401
    fetch_email_by_date()
    order_status = delivery_excel_handle()
    google_sheet_handle(order_status)
    return 'Task completed', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
