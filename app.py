"""
Flask application for order processing API.

Endpoints:
- POST /flowtide_excel_handle - Run daily order processing
- POST /shopline_outstanding_order_update - Update outstanding orders
- GET /return_ip - Get server IP address
- GET /health - Health check endpoint
"""
import os
import requests
from flask import Flask, request, jsonify
from loguru import logger

from src.utils.logger import setup_logger
from src.orchestrator.daily_workflow import DailyWorkflow
from src.orchestrator.outstanding_workflow import OutstandingOrderWorkflow


# Setup logging
setup_logger(log_file="logs/flask.log")

app = Flask(__name__)

# Auth token for API endpoints
AUTH_TOKEN = "BagelShopC2C"


def check_auth():
    """Check API authentication."""
    custom_header = request.headers.get("X-Auth")
    return custom_header == AUTH_TOKEN


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route("/flowtide_excel_handle", methods=["POST"])
def flowtide_excel_handle():
    """
    Run the daily order processing workflow.

    Requires X-Auth header.
    """
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        logger.info("API 觸發: flowtide_excel_handle")

        workflow = DailyWorkflow(notify_customers=True)
        success = workflow.run()

        if success:
            return jsonify({"status": "success", "message": "Task completed"}), 200
        else:
            return jsonify({"status": "warning", "message": "Task completed with warnings"}), 200

    except Exception as e:
        logger.error(f"flowtide_excel_handle 錯誤: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/shopline_outstanding_order_update", methods=["POST"])
def shopline_outstanding_order_update():
    """
    Update outstanding ShopLine orders.

    Requires X-Auth header.
    """
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        logger.info("API 觸發: shopline_outstanding_order_update")

        workflow = OutstandingOrderWorkflow(notify_customers=True)
        success = workflow.run()

        if success:
            return jsonify({"status": "success", "message": "Task completed"}), 200
        else:
            return jsonify({"status": "warning", "message": "Task completed with warnings"}), 200

    except Exception as e:
        logger.error(f"shopline_outstanding_order_update 錯誤: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/return_ip", methods=["GET"])
def get_ip():
    """Get server public IP address."""
    try:
        response = requests.get("https://httpbin.org/ip", timeout=10)
        ip = response.json().get("origin", "Unknown")
        return jsonify({"ip": ip}), 200
    except requests.RequestException as e:
        logger.error(f"獲取 IP 失敗: {e}")
        return jsonify({"error": f"Failed to fetch IP: {e}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
