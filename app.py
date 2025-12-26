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
            "/api/inventory": "Get latest inventory snapshot with items",
            "/api/inventory/sync": "Trigger inventory sync from email",
            "/api/inventory/backfill": "Backfill historical data",
            "/api/inventory/history": "Get historical snapshots (for trends)",
            "/api/inventory/changes": "Get inventory changes (restock logs)",
            "/api/inventory/raw-items": "Get raw Excel items (with batch details)",
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


@app.route("/api/inventory/history", methods=["GET"])
def get_inventory_history():
    """
    Get historical inventory snapshots for trend analysis.

    Query params:
        days: Number of days to look back (default: 30)

    Returns:
        JSON with list of snapshots (summary only, no items)
    """
    try:
        from datetime import datetime, timedelta
        days = request.args.get("days", 30, type=int)

        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        snapshots = workflow.inventory_repo.get_snapshots_by_date_range(start_date, end_date)

        return jsonify({
            "success": True,
            "data": snapshots,
            "count": len(snapshots)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/changes", methods=["GET"])
def get_inventory_changes():
    """
    Get recent inventory changes (restock logs).

    Query params:
        limit: Number of records (default: 20)

    Returns:
        JSON with list of changes
    """
    try:
        limit = request.args.get("limit", 20, type=int)

        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        changes = workflow.inventory_repo.get_recent_changes(limit=limit)

        return jsonify({
            "success": True,
            "data": changes,
            "count": len(changes)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/raw-items", methods=["GET"])
def get_raw_items():
    """
    Get raw inventory items for a specific snapshot.

    Query params:
        snapshot_id: UUID of snapshot (optional, defaults to latest)
        product_name: Filter by product name (optional)

    Returns:
        JSON with raw item details
    """
    try:
        snapshot_id = request.args.get("snapshot_id")
        product_name = request.args.get("product_name")

        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        # Get latest snapshot if no ID provided
        if not snapshot_id:
            latest = workflow.inventory_repo.get_latest_snapshot()
            if latest:
                snapshot_id = latest.get('id')

        if not snapshot_id:
            return jsonify({
                "success": True,
                "data": [],
                "message": "No snapshot available"
            }), 200

        # Query raw items
        client = workflow.inventory_repo.client
        query = client.table("inventory_raw_items").select("*").eq("snapshot_id", snapshot_id)

        if product_name:
            query = query.eq("product_name", product_name)

        result = query.order("product_name").execute()

        return jsonify({
            "success": True,
            "data": result.data or [],
            "count": len(result.data) if result.data else 0
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/trend", methods=["GET"])
def get_inventory_trend():
    """
    Get daily stock trend for items (for charts).

    Query params:
        days: Number of days (default: 30)
        category: Filter by category - 'bread', 'box', 'bag' (optional)
        item: Filter by specific item name (optional)

    Returns:
        JSON with items and their daily stock values
    """
    try:
        days = request.args.get("days", 30, type=int)
        category = request.args.get("category")
        item_name = request.args.get("item")

        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        if item_name:
            # Single item history
            data = workflow.inventory_repo.get_item_history(item_name, days)
            # Transform to consistent format
            trend_data = [{
                'name': item_name,
                'category': data[0]['category'] if data else None,
                'data': [
                    {
                        'date': row.get('inventory_snapshots', {}).get('snapshot_date', '')[:10],
                        'stock': row['current_stock']
                    }
                    for row in data if row.get('inventory_snapshots')
                ]
            }] if data else []
        else:
            # All items trend
            trend_data = workflow.inventory_repo.get_items_trend(category, days)

        return jsonify({
            "success": True,
            "data": trend_data,
            "count": len(trend_data)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
