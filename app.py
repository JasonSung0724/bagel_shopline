"""
Flask application for Bagel Shop.

This is a minimal API for health checks and future extensions.
Order processing is handled by scheduled workers (main_scripts.py, sub_scripts.py).
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS

from src.utils.logger import setup_logger
from src.orchestrator.inventory_workflow import InventoryWorkflow
from src.services.inventory_service import InventoryService

# Setup logging
setup_logger(log_file="logs/flask.log")

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route("/", methods=["GET"])
def index():
    """Root endpoint."""
    return jsonify({
        "service": "Bagel Shop API",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/api/inventory": "Get latest inventory",
            "/api/inventory/sync": "Trigger inventory sync",
            "/api/inventory/backfill": "Backfill historical data",
        }
    }), 200


# ===========================================
# Inventory API Endpoints
# ===========================================

@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    """
    Get the latest inventory data.

    Returns:
        JSON with inventory snapshot data
    """
    try:
        workflow = InventoryWorkflow()
        data = workflow.get_latest_inventory()

        if data:
            return jsonify({
                "success": True,
                "data": data
            }), 200
        else:
            # Return mock data if no real data available
            return jsonify({
                "success": True,
                "data": None,
                "message": "No inventory data available. Run sync first."
            }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/sync", methods=["POST"])
def sync_inventory():
    """
    Trigger inventory sync from latest email.

    Returns:
        JSON with sync result
    """
    try:
        workflow = InventoryWorkflow()
        success = workflow.run_daily_sync()

        return jsonify({
            "success": success,
            "message": "Inventory sync completed" if success else "Sync failed"
        }), 200 if success else 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/backfill", methods=["POST"])
def backfill_inventory():
    """
    Backfill historical inventory data from emails.

    Query params:
        days: Number of days to look back (default: 365)
        dry_run: If true, don't save to database (default: false)

    Returns:
        JSON with backfill result
    """
    try:
        days = request.args.get("days", 365, type=int)
        dry_run = request.args.get("dry_run", "false").lower() == "true"

        workflow = InventoryWorkflow()
        count = workflow.run_backfill(days_back=days, dry_run=dry_run)

        return jsonify({
            "success": count > 0,
            "imported_count": count,
            "days_back": days,
            "dry_run": dry_run
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/parse-local", methods=["POST"])
def parse_local_excel():
    """
    Parse a local Excel file (for testing).

    Body JSON:
        file_path: Path to Excel file

    Returns:
        JSON with parsed inventory data
    """
    try:
        data = request.get_json()
        file_path = data.get("file_path")

        if not file_path:
            return jsonify({
                "success": False,
                "error": "file_path is required"
            }), 400

        service = InventoryService()
        snapshot = service.parse_local_excel(file_path)

        return jsonify({
            "success": True,
            "data": snapshot.to_dict()
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
