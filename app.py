"""
Flask application for Bagel Shop.

This is a minimal API for health checks and future extensions.
Order processing is handled by scheduled workers (main_scripts.py, sub_scripts.py).
"""
import os
import hashlib
import secrets
import threading
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, make_response, send_file, session
from flask_cors import CORS

from src.utils.logger import setup_logger
from src.orchestrator.inventory_workflow import InventoryWorkflow
from src.services.inventory_service import InventoryService
from src.services.sales_service import SalesService
from src.services.product_config_service import ProductConfigService
from src.services.platform_config_service import ColumnMappingService
from src.services.lottery_service import LotteryService

# Setup logging
setup_logger(log_file="logs/flask.log")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
CORS(app, origins="*", supports_credentials=False, expose_headers=[
    'Content-Disposition',
    'X-Report-Original-Rows',
    'X-Report-Total-Orders',
    'X-Report-Row-Count',
    'X-Report-Platform',
    'X-Report-Time-Taken',
    'X-Report-Error-Count',
    'X-Report-Errors'
])  # Enable CORS for all origins (required for Shopline integration)

# Inventory page password (from environment variable, required)
INVENTORY_PASSWORD = os.getenv("INVENTORY_PASSWORD")

# Background task storage (in-memory, will be lost on restart)
# For production, consider using Redis or database
background_tasks = {}


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
            "/api/inventory/diagnosis": "Get inventory diagnosis with all calculations (庫存診斷)",
            "/api/inventory/sync": "POST: Trigger today's sync, PATCH: Sync specific date",
            "/api/inventory/backfill": "Backfill historical data",
            "/api/inventory/history": "Get historical snapshots (for trends)",
            "/api/inventory/changes": "Get inventory changes (detected changes)",
            "/api/inventory/restock": "Get restock records (入庫紀錄)",
            "/api/inventory/raw-items": "Get raw Excel items (with batch details)",
            "/api/inventory/trend": "Get stock trend (庫存趨勢)",
            "/api/inventory/sales-trend": "Get sales trend based on 實出量 from daily_sales (銷量趨勢)",
            "/api/inventory/product-mappings": "Get/Add/Delete product mappings (麵包與塑膠袋對照)",
            "/api/sales/sync": "PATCH: Sync sales data for specific date range (補銷量)",
            "/api/auth/verify": "Verify inventory page password",
        }
    }), 200


# ===========================================
# Authentication Endpoints
# ===========================================

@app.route("/api/auth/verify", methods=["POST"])
def verify_password():
    """
    Verify password for inventory page access.

    Request body:
        {"password": "your_password"}

    Returns:
        {"success": true} if password matches
        {"success": false, "message": "..."} if password is incorrect or not configured
    """
    try:
        # Check if password is configured
        if not INVENTORY_PASSWORD:
            return jsonify({
                "success": False,
                "message": "系統密碼未設定，請聯繫管理員"
            }), 500

        data = request.get_json()
        password = data.get("password", "") if data else ""

        if password == INVENTORY_PASSWORD:
            return jsonify({"success": True}), 200
        else:
            return jsonify({
                "success": False,
                "message": "密碼錯誤"
            }), 401

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ===========================================
# Inventory API Endpoints
# ===========================================

@app.route("/api/inventory/init", methods=["GET"])
def get_inventory_init():
    """
    Get all initial data needed for inventory dashboard in ONE request.
    Combines inventory snapshot + diagnosis data for faster loading.

    Returns:
        JSON with both inventory and diagnosis data
    """
    try:
        workflow = InventoryWorkflow()

        # Get basic inventory data
        inventory_data = workflow.get_latest_inventory()

        # Get diagnosis data (includes all calculations)
        diagnosis_data = None
        if workflow.inventory_repo.is_connected:
            diagnosis_data = workflow.inventory_repo.get_inventory_diagnosis()

        return jsonify({
            "success": True,
            "data": {
                "inventory": inventory_data,
                "diagnosis": diagnosis_data
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


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


def _run_sync_task(task_id: str, start_date: datetime, end_date: datetime, send_notification: bool):
    """
    Background task to run inventory sync.
    Updates the task status in background_tasks dict.
    """
    try:
        background_tasks[task_id]["status"] = "running"
        background_tasks[task_id]["started_at"] = datetime.now().isoformat()

        workflow = InventoryWorkflow()

        if start_date == end_date:
            # Single date mode
            result = workflow.sync_specific_date(start_date, send_notification)
        else:
            # Date range mode
            result = workflow.sync_date_range(start_date, end_date, send_notification)

        background_tasks[task_id]["status"] = "completed"
        background_tasks[task_id]["result"] = result
        background_tasks[task_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        background_tasks[task_id]["status"] = "failed"
        background_tasks[task_id]["error"] = str(e)
        background_tasks[task_id]["completed_at"] = datetime.now().isoformat()


@app.route("/api/inventory/sync", methods=["PATCH"])
def patch_inventory_sync():
    """
    Sync inventory for a specific date or date range (補同步指定日期).

    Body JSON:
        Option 1 - Single date:
            date: Target date in YYYY-MM-DD format
            notify: Send LINE notification (optional, default: false)
            async: Run in background (optional, default: false)

        Option 2 - Date range:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            notify: Send LINE notification (optional, default: false)
            async: Run in background (optional, default: false)

    Returns:
        If async=false: JSON with sync result details (blocking)
        If async=true: JSON with task_id for status polling
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400

        send_notification = data.get("notify", False)
        run_async = data.get("async", False)

        # Parse dates
        if data.get("start_date") and data.get("end_date"):
            # Date range mode
            try:
                start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")
                end_date = datetime.strptime(data["end_date"], "%Y-%m-%d")
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": "Invalid date format. Use YYYY-MM-DD"
                }), 400

            # Validate date range
            if start_date > end_date:
                return jsonify({
                    "success": False,
                    "error": "start_date must be before or equal to end_date"
                }), 400

            # Limit to max 90 days
            days_diff = (end_date - start_date).days
            if days_diff > 90:
                return jsonify({
                    "success": False,
                    "error": f"Date range too large ({days_diff} days). Maximum is 90 days."
                }), 400

        elif data.get("date"):
            # Single date mode
            try:
                start_date = datetime.strptime(data["date"], "%Y-%m-%d")
                end_date = start_date
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": "Invalid date format. Use YYYY-MM-DD"
                }), 400
        else:
            return jsonify({
                "success": False,
                "error": "Either 'date' or 'start_date'+'end_date' is required"
            }), 400

        # Async mode: run in background thread
        if run_async:
            task_id = str(uuid.uuid4())
            background_tasks[task_id] = {
                "id": task_id,
                "type": "inventory_sync",
                "status": "pending",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
            }

            # Start background thread
            thread = threading.Thread(
                target=_run_sync_task,
                args=(task_id, start_date, end_date, send_notification),
                daemon=True
            )
            thread.start()

            return jsonify({
                "success": True,
                "async": True,
                "task_id": task_id,
                "message": f"同步任務已啟動，請使用 task_id 查詢進度",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            }), 202  # 202 Accepted

        # Sync mode: blocking execution (original behavior)
        workflow = InventoryWorkflow()

        if start_date == end_date:
            result = workflow.sync_specific_date(start_date, send_notification)
        else:
            result = workflow.sync_date_range(start_date, end_date, send_notification)

        status_code = 200 if result["success"] else 404
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ===========================================
# Sales API Endpoints (銷量資料)
# ===========================================

def _run_sales_sync_task(task_id: str, start_date: datetime, end_date: datetime):
    """
    Background task to run sales sync.
    Updates the task status in background_tasks dict.
    """
    try:
        background_tasks[task_id]["status"] = "running"
        background_tasks[task_id]["started_at"] = datetime.now().isoformat()

        sales_service = SalesService()
        success_count, fail_count = sales_service.backfill(
            start_date=start_date,
            end_date=end_date,
            dry_run=False
        )

        background_tasks[task_id]["status"] = "completed"
        background_tasks[task_id]["result"] = {
            "success": success_count > 0 or fail_count == 0,
            "success_count": success_count,
            "fail_count": fail_count,
            "message": f"成功處理 {success_count} 個檔案，失敗 {fail_count} 個"
        }
        background_tasks[task_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        background_tasks[task_id]["status"] = "failed"
        background_tasks[task_id]["error"] = str(e)
        background_tasks[task_id]["completed_at"] = datetime.now().isoformat()


@app.route("/api/sales/sync", methods=["PATCH"])
def patch_sales_sync():
    """
    Sync sales data for a specific date range (補銷量).

    Body JSON:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        async: Run in background (optional, default: true)

    Returns:
        If async=false: JSON with sync result details (blocking)
        If async=true: JSON with task_id for status polling
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400

        run_async = data.get("async", True)

        # Parse dates
        if not data.get("start_date") or not data.get("end_date"):
            return jsonify({
                "success": False,
                "error": "'start_date' and 'end_date' are required"
            }), 400

        try:
            start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(data["end_date"], "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Invalid date format. Use YYYY-MM-DD"
            }), 400

        # Validate date range
        if start_date > end_date:
            return jsonify({
                "success": False,
                "error": "start_date must be before or equal to end_date"
            }), 400

        # Limit to max 90 days
        days_diff = (end_date - start_date).days
        if days_diff > 90:
            return jsonify({
                "success": False,
                "error": f"Date range too large ({days_diff} days). Maximum is 90 days."
            }), 400

        # Async mode: run in background thread
        if run_async:
            task_id = str(uuid.uuid4())
            background_tasks[task_id] = {
                "id": task_id,
                "type": "sales_sync",
                "status": "pending",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
            }

            # Start background thread
            thread = threading.Thread(
                target=_run_sales_sync_task,
                args=(task_id, start_date, end_date),
                daemon=True
            )
            thread.start()

            return jsonify({
                "success": True,
                "async": True,
                "task_id": task_id,
                "message": f"銷量同步任務已啟動，請使用 task_id 查詢進度",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            }), 202  # 202 Accepted

        # Sync mode: blocking execution
        sales_service = SalesService()
        success_count, fail_count = sales_service.backfill(
            start_date=start_date,
            end_date=end_date,
            dry_run=False
        )

        return jsonify({
            "success": success_count > 0 or fail_count == 0,
            "success_count": success_count,
            "fail_count": fail_count,
            "message": f"成功處理 {success_count} 個檔案，失敗 {fail_count} 個"
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/sync/status/<task_id>", methods=["GET"])
def get_sync_task_status(task_id: str):
    """
    Get the status of a background sync task.

    Returns:
        JSON with task status and result (if completed)
    """
    task = background_tasks.get(task_id)

    if not task:
        return jsonify({
            "success": False,
            "error": "Task not found"
        }), 404

    return jsonify({
        "success": True,
        "task": task
    }), 200


@app.route("/api/inventory/sync/tasks", methods=["GET"])
def list_sync_tasks():
    """
    List all sync tasks (for debugging/monitoring).

    Returns:
        JSON with list of all tasks
    """
    # Return tasks sorted by created_at descending
    tasks = sorted(
        background_tasks.values(),
        key=lambda t: t.get("created_at", ""),
        reverse=True
    )

    return jsonify({
        "success": True,
        "tasks": tasks[:20],  # Limit to 20 most recent
        "total": len(background_tasks)
    }), 200


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


@app.route("/api/inventory/restock", methods=["GET"])
def get_restock_records():
    """
    Get restock records (入庫紀錄).

    Query params:
        days: Number of days to look back (default: 30)
        category: Filter by category - 'bread', 'box', 'bag' (optional)

    Returns:
        JSON with restock records
    """
    try:
        days = request.args.get("days", 30, type=int)
        category = request.args.get("category")

        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        restock_data = workflow.inventory_repo.get_restock_records(days=days, category=category)

        return jsonify({
            "success": True,
            "data": restock_data,
            "count": len(restock_data)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/sales-trend", methods=["GET"])
def get_sales_trend():
    """
    Get daily sales trend for items (based on stock_out).

    Query params:
        days: Number of days (default: 30)
        category: Filter by category - 'bread', 'box', 'bag' (optional)

    Returns:
        JSON with items and their daily sales (stock_out) values
    """
    try:
        days = request.args.get("days", 30, type=int)
        category = request.args.get("category")

        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        sales_data = workflow.inventory_repo.get_sales_trend(category, days)

        return jsonify({
            "success": True,
            "data": sales_data,
            "count": len(sales_data)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/analysis", methods=["GET"])
def get_inventory_analysis():
    """
    Get comprehensive trend analysis data for all time periods (7, 14, 30 days).
    This endpoint returns both sales trend and stock trend data in a single call,
    with pre-calculated statistics for each period.

    Query params:
        category: Filter by category - 'bread', 'box', 'bag' (optional, default: 'bread')

    Returns:
        JSON with sales and stock trend data for 7, 14, 30 day periods:
        {
            "success": true,
            "data": {
                "sales": {
                    "items": [...],  // All items with 30-day data
                    "stats": {
                        "7": { "itemName": { total, avg, max, min }, ... },
                        "14": { ... },
                        "30": { ... }
                    }
                },
                "stock": {
                    "items": [...],  // All items with 30-day data
                    "stats": {
                        "7": { "itemName": { latest, oldest, change }, ... },
                        "14": { ... },
                        "30": { ... }
                    }
                }
            }
        }
    """
    try:
        category = request.args.get("category", "bread")

        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        from datetime import datetime, timedelta

        # Get 30-day data (covers all periods)
        sales_data = workflow.inventory_repo.get_sales_trend(category, 30)
        stock_data = workflow.inventory_repo.get_items_trend(category, 30)

        # Use today as the reference date
        today = datetime.now().date()

        # Calculate cutoff dates based on today
        date_7 = (today - timedelta(days=7)).isoformat()
        date_14 = (today - timedelta(days=14)).isoformat()
        date_30 = (today - timedelta(days=30)).isoformat()

        # Calculate sales stats for each period
        sales_stats = {"7": {}, "14": {}, "30": {}}
        for item in sales_data:
            name = item['name']
            data = item.get('data', [])

            for period, cutoff in [("7", date_7), ("14", date_14), ("30", date_30)]:
                filtered = [d for d in data if d['date'] >= cutoff]
                if filtered:
                    sales_values = [d['sales'] for d in filtered]
                    total = sum(sales_values)
                    sales_stats[period][name] = {
                        "total": total,
                        "avg": round(total / len(filtered)) if filtered else 0,
                        "max": max(sales_values) if sales_values else 0,
                        "min": min(sales_values) if sales_values else 0,
                        "days": len(filtered)
                    }

        # Calculate stock stats for each period
        stock_stats = {"7": {}, "14": {}, "30": {}}
        for item in stock_data:
            name = item['name']
            data = item.get('data', [])

            for period, cutoff in [("7", date_7), ("14", date_14), ("30", date_30)]:
                filtered = [d for d in data if d['date'] >= cutoff]
                if filtered:
                    # Sort by date to get oldest and latest
                    sorted_data = sorted(filtered, key=lambda x: x['date'])
                    oldest = sorted_data[0]['stock'] if sorted_data else 0
                    latest = sorted_data[-1]['stock'] if sorted_data else 0
                    stock_stats[period][name] = {
                        "latest": latest,
                        "oldest": oldest,
                        "change": latest - oldest,
                        "days": len(filtered)
                    }

        return jsonify({
            "success": True,
            "data": {
                "sales": {
                    "items": sales_data,
                    "stats": sales_stats
                },
                "stock": {
                    "items": stock_data,
                    "stats": stock_stats
                }
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/diagnosis", methods=["GET"])
def get_inventory_diagnosis():
    """
    Get comprehensive inventory diagnosis with all calculations done server-side.

    Returns:
        JSON with diagnosis data for all items including:
        - Current stock
        - 30-day and 20-day sales (total and daily average)
        - Days of stock remaining
        - Reorder point
        - Health status (critical/healthy/overstock)
        - Matched bag for bread items
    """
    try:
        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        diagnosis = workflow.inventory_repo.get_inventory_diagnosis()

        if not diagnosis:
            return jsonify({
                "success": False,
                "error": "No inventory data available"
            }), 404

        return jsonify({
            "success": True,
            "data": diagnosis
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/product-mappings", methods=["GET"])
def get_product_mappings():
    """
    Get product mappings (bread to bag relationships).

    Returns:
        JSON with list of mappings
    """
    try:
        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        mappings = workflow.inventory_repo.get_product_mappings()

        return jsonify({
            "success": True,
            "data": mappings,
            "count": len(mappings)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/product-mappings", methods=["POST"])
def add_product_mapping():
    """
    Add a new product mapping.

    Body:
        bread_name: Name of the bread product
        bag_name: Name of the corresponding bag

    Returns:
        JSON with success status
    """
    try:
        data = request.get_json()
        bread_name = data.get("bread_name")
        bag_name = data.get("bag_name")

        if not bread_name or not bag_name:
            return jsonify({
                "success": False,
                "error": "bread_name and bag_name are required"
            }), 400

        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        success = workflow.inventory_repo.add_product_mapping(bread_name, bag_name)

        return jsonify({
            "success": success,
            "message": "Mapping added" if success else "Failed to add mapping"
        }), 200 if success else 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/inventory/product-mappings", methods=["DELETE"])
def delete_product_mapping():
    """
    Delete a product mapping.

    Body:
        bread_name: Name of the bread product
        bag_name: Name of the corresponding bag

    Returns:
        JSON with success status
    """
    try:
        data = request.get_json()
        bread_name = data.get("bread_name")
        bag_name = data.get("bag_name")

        if not bread_name or not bag_name:
            return jsonify({
                "success": False,
                "error": "bread_name and bag_name are required"
            }), 400

        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        success = workflow.inventory_repo.delete_product_mapping(bread_name, bag_name)

        return jsonify({
            "success": success,
            "message": "Mapping deleted" if success else "Failed to delete mapping"
        }), 200 if success else 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/report/generate", methods=["POST"])
def generate_report():
    """
    Generate Excel report from uploaded file.
    
    Form-data:
        file: Excel file
        platform: Platform name (shopline, mixx, c2c, aoshi)
    
    Returns:
        Excel file download or JSON error
    """
    try:
        from flask import send_file
        from src.services.report_service import ReportService
        
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400
            
        file = request.files['file']
        platform = request.form.get('platform')
        
        if not file.filename:
            return jsonify({"success": False, "error": "No file selected"}), 400
            
        if not platform:
            return jsonify({"success": False, "error": "Platform not specified"}), 400

        service = ReportService()
        
        # Read file into bytes
        file_content = file.read()
        
        # Generate report
        output_buffer, summary = service.generate_report(file_content, file.filename, platform)
        
        # If we want to return JSON summary + File, it's tricky in one response.
        # Usually we just return the file with headers. 
        # Or we can return JSON if 'preview'=true, but here we want download.
        # Format filename
        input_name = file.filename.rsplit('.', 1)[0]
        output_filename = f"{input_name}_output.xlsx"
        
        response = make_response(output_buffer.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        from urllib.parse import quote
        encoded_filename = quote(output_filename)
        response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"
        
        # Add custom headers for frontend stats
        response.headers['X-Report-Original-Rows'] = str(summary['original_rows'])
        response.headers['X-Report-Total-Orders'] = str(summary['total_orders'])
        response.headers['X-Report-Row-Count'] = str(summary['total_rows'])
        response.headers['X-Report-Platform'] = summary['platform']
        response.headers['X-Report-Time-Taken'] = f"{summary.get('time_taken', 0):.2f}"
        response.headers['X-Report-Error-Count'] = str(len(summary['errors']))

        # Encode errors as JSON in header (limit to first 20 for header size)
        import json
        errors_to_send = summary['errors'][:20]
        response.headers['X-Report-Errors'] = json.dumps(errors_to_send, ensure_ascii=False)
        
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500




# ===========================================
# Product Management Endpoints
# ===========================================

@app.route("/api/products", methods=["GET"])
def get_products():
    try:
        svc = ProductConfigService()
        return jsonify(svc.get_all_products()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/products", methods=["POST"])
def create_product():
    try:
        data = request.json
        svc = ProductConfigService()
        res = svc.create_product(data["code"], data.get("name", data["code"]), int(data.get("qty", 1)))
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/products/<code_id>", methods=["PUT"])
def update_product(code_id):
    try:
        data = request.json
        svc = ProductConfigService()
        res = svc.update_product_qty(code_id, int(data["qty"]))
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/products/<code_id>", methods=["DELETE"])
def delete_product(code_id):
    try:
        svc = ProductConfigService()
        res = svc.delete_product(code_id)
        return jsonify({"success": res}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/aliases", methods=["POST"])
def add_alias():
    try:
        data = request.json
        svc = ProductConfigService()
        res = svc.add_alias(data["product_code"], data["alias"])
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/aliases/<int:alias_id>", methods=["DELETE"])
def delete_alias(alias_id):
    try:
        svc = ProductConfigService()
        res = svc.delete_alias(alias_id)
        return jsonify({"success": res}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================================
# Master Data API Endpoints
# ===========================================

@app.route("/api/master/sync", methods=["POST"])
def sync_master_data():
    """
    Sync master data from historical inventory records.

    Returns:
        JSON with sync result counts
    """
    try:
        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        result = workflow.inventory_repo.sync_master_data_from_inventory()

        return jsonify({
            "success": True,
            "data": result,
            "message": f"Synced {result['breads']} breads, {result['bags']} bags, {result['boxes']} boxes"
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/master/breads", methods=["GET"])
def get_master_breads():
    """Get all bread master records."""
    try:
        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        data = workflow.inventory_repo.get_master_breads()

        return jsonify({
            "success": True,
            "data": data,
            "count": len(data)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/master/bags", methods=["GET"])
def get_master_bags():
    """Get all bag master records."""
    try:
        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        data = workflow.inventory_repo.get_master_bags()

        return jsonify({
            "success": True,
            "data": data,
            "count": len(data)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/master/boxes", methods=["GET"])
def get_master_boxes():
    """Get all box master records."""
    try:
        workflow = InventoryWorkflow()
        if not workflow.inventory_repo.is_connected:
            return jsonify({
                "success": False,
                "error": "Database not connected"
            }), 500

        data = workflow.inventory_repo.get_master_boxes()

        return jsonify({
            "success": True,
            "data": data,
            "count": len(data)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500



# ===========================================
# System Settings API (Unified Column Mappings)
# ===========================================

@app.route("/api/settings/mappings", methods=["GET"])
def get_column_mappings():
    """
    Get unified column mappings.
    Returns: { "order_id": ["訂單編號", ...], "receiver_name": [...], ... }
    """
    try:
        service = ColumnMappingService()
        mappings = service.get_mapping()
        return jsonify({
            "success": True,
            "data": mappings
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/settings/mappings", methods=["POST"])
def update_column_mappings():
    """
    Update unified column mappings.
    Body: { "order_id": ["訂單編號", ...], "receiver_name": [...], ... }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Mapping data is required"
            }), 400

        service = ColumnMappingService()
        success = service.update_mapping(data)

        if success:
            return jsonify({"success": True, "message": "Settings updated"}), 200
        else:
            return jsonify({"success": False, "error": "Failed to update settings"}), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/settings/mappings/<field_name>", methods=["PUT"])
def update_field_aliases(field_name: str):
    """
    Update aliases for a specific field.
    Body: { "aliases": ["訂單編號", "Order ID", ...] }
    """
    try:
        data = request.get_json()
        aliases = data.get("aliases")

        if not aliases or not isinstance(aliases, list):
            return jsonify({
                "success": False,
                "error": "aliases (list) is required"
            }), 400

        service = ColumnMappingService()
        success = service.update_field(field_name, aliases)

        if success:
            return jsonify({"success": True, "message": f"Field '{field_name}' updated"}), 200
        else:
            return jsonify({"success": False, "error": "Failed to update field"}), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ===========================================
# Lottery (Scratch Card) API Endpoints (刮刮樂)
# ===========================================

# Password for lottery admin (use same as inventory or separate)
LOTTERY_ADMIN_PASSWORD = os.getenv("LOTTERY_ADMIN_PASSWORD", INVENTORY_PASSWORD)


def verify_lottery_admin():
    """Verify admin password for lottery management."""
    auth_header = request.headers.get("X-Admin-Password")
    if not auth_header or auth_header != LOTTERY_ADMIN_PASSWORD:
        return False
    return True


# --- Public API (for Shopline frontend) ---

@app.route("/api/lottery/campaigns/<campaign_id>/check", methods=["GET"])
def check_lottery_eligibility(campaign_id):
    """
    Check if a user is eligible to participate in a lottery.

    Query params:
        customer_id: Shopline customer ID (required if campaign requires login)

    Returns:
        {
            "eligible": true/false,
            "reason": "..." (if not eligible),
            "campaign": {...},
            "attempts_used": 0,
            "attempts_remaining": 1
        }
    """
    try:
        customer_id = request.args.get("customer_id")

        service = LotteryService()
        result = service.check_eligibility(campaign_id, customer_id)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "eligible": False,
            "reason": str(e)
        }), 500


@app.route("/api/lottery/campaigns/<campaign_id>/scratch", methods=["POST"])
def scratch_lottery(campaign_id):
    """
    Process a scratch card attempt.

    Body:
        customer_id: Shopline customer ID (required)
        customer_email: Customer email (optional)
        customer_name: Customer name (optional)

    Returns:
        {
            "success": true,
            "result": {
                "is_winner": true/false,
                "prize": {...} or null,
                "redemption_code": "XXXX-XXXX-XXXX" or null,
                "message": "恭喜中獎!" or "很可惜，未中獎",
                "attempts_remaining": 0
            }
        }
    """
    try:
        data = request.get_json() or {}

        customer_id = data.get("customer_id")
        customer_email = data.get("customer_email")
        customer_name = data.get("customer_name")

        # Get client info for logging
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
        user_agent = request.headers.get("User-Agent")

        service = LotteryService()
        result = service.scratch(
            campaign_id=campaign_id,
            shopline_customer_id=customer_id,
            customer_email=customer_email,
            customer_name=customer_name,
            ip_address=ip_address,
            user_agent=user_agent
        )

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_code": "SYSTEM_ERROR"
        }), 500


@app.route("/api/lottery/campaigns/<campaign_id>/results", methods=["GET"])
def get_user_lottery_results(campaign_id):
    """
    Get a user's lottery results for a campaign.

    Query params:
        customer_id: Shopline customer ID (required)

    Returns:
        List of user's scratch results
    """
    try:
        customer_id = request.args.get("customer_id")

        if not customer_id:
            return jsonify({
                "success": False,
                "error": "customer_id is required"
            }), 400

        service = LotteryService()
        results = service.get_user_results(campaign_id, customer_id)

        return jsonify({
            "success": True,
            "data": results,
            "count": len(results)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/lottery/redeem/verify", methods=["POST"])
def verify_redemption_code():
    """
    Verify a redemption code (check if valid and not yet redeemed).

    Body:
        code: Redemption code (XXXX-XXXX-XXXX format)

    Returns:
        {
            "valid": true/false,
            "redeemed": true/false,
            "result": {...}
        }
    """
    try:
        data = request.get_json() or {}
        code = data.get("code", "").strip().upper()

        if not code:
            return jsonify({
                "valid": False,
                "error": "兌換碼不能為空"
            }), 400

        service = LotteryService()
        result = service.verify_redemption_code(code)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "valid": False,
            "error": str(e)
        }), 500


@app.route("/api/lottery/redeem", methods=["POST"])
def redeem_lottery_prize():
    """
    Redeem a lottery prize (mark as redeemed).
    Requires admin password.

    Body:
        code: Redemption code
        redeemed_by: Staff name (optional)

    Returns:
        {"success": true, "result": {...}}
    """
    try:
        if not verify_lottery_admin():
            return jsonify({
                "success": False,
                "error": "管理員密碼錯誤"
            }), 401

        data = request.get_json() or {}
        code = data.get("code", "").strip().upper()
        redeemed_by = data.get("redeemed_by")

        if not code:
            return jsonify({
                "success": False,
                "error": "兌換碼不能為空"
            }), 400

        service = LotteryService()
        result = service.redeem_prize(code, redeemed_by)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# --- Admin API (for backend management) ---

@app.route("/api/lottery/admin/campaigns", methods=["GET"])
def list_lottery_campaigns():
    """
    List all lottery campaigns.
    Requires admin password.

    Query params:
        status: Filter by status (draft/active/paused/ended)
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        status = request.args.get("status")

        service = LotteryService()
        campaigns = service.list_campaigns(status)

        return jsonify({
            "success": True,
            "data": campaigns,
            "count": len(campaigns)
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/campaigns", methods=["POST"])
def create_lottery_campaign():
    """
    Create a new lottery campaign.
    Requires admin password.

    Body:
        name: Campaign name (required)
        description: Description
        start_date: Start date ISO format (required)
        end_date: End date ISO format (required)
        max_attempts_per_user: Max attempts per user (default: 1)
        require_login: Require Shopline login (default: true)
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        data = request.get_json()

        service = LotteryService()
        result = service.create_campaign(data)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/campaigns/<campaign_id>", methods=["GET"])
def get_lottery_campaign(campaign_id):
    """
    Get a specific campaign with prizes.
    Requires admin password.
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        service = LotteryService()
        campaign = service.get_campaign(campaign_id)

        if campaign:
            return jsonify({"success": True, "data": campaign}), 200
        else:
            return jsonify({"success": False, "error": "Campaign not found"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/campaigns/<campaign_id>", methods=["PUT"])
def update_lottery_campaign(campaign_id):
    """
    Update a campaign.
    Requires admin password.

    Body: Fields to update (name, description, start_date, end_date, status, etc.)
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        data = request.get_json()

        service = LotteryService()
        result = service.update_campaign(campaign_id, data)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/campaigns/<campaign_id>", methods=["DELETE"])
def delete_lottery_campaign(campaign_id):
    """
    Delete a campaign (only draft campaigns can be deleted).
    Requires admin password.
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        service = LotteryService()
        result = service.delete_campaign(campaign_id)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/campaigns/<campaign_id>/prizes", methods=["GET"])
def get_lottery_prizes(campaign_id):
    """
    Get all prizes for a campaign.
    Requires admin password.
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        service = LotteryService()
        prizes = service.get_prizes(campaign_id)

        return jsonify({
            "success": True,
            "data": prizes,
            "count": len(prizes)
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/campaigns/<campaign_id>/prizes", methods=["POST"])
def add_lottery_prize(campaign_id):
    """
    Add a prize to a campaign.
    Requires admin password.

    Body:
        name: Prize name (required)
        description: Description
        prize_type: Type (physical/coupon/points/free_shipping/discount/none)
        prize_value: Value (e.g., coupon code, discount amount)
        total_quantity: Total quantity (required)
        probability: Win probability 0.0-1.0 (required)
        display_order: Display order
        image_url: Image URL
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        data = request.get_json()

        service = LotteryService()
        result = service.add_prize(campaign_id, data)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/prizes/<prize_id>", methods=["PUT"])
def update_lottery_prize(prize_id):
    """
    Update a prize.
    Requires admin password.
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        data = request.get_json()

        service = LotteryService()
        result = service.update_prize(prize_id, data)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/prizes/<prize_id>", methods=["DELETE"])
def delete_lottery_prize(prize_id):
    """
    Delete a prize.
    Requires admin password.
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        service = LotteryService()
        result = service.delete_prize(prize_id)

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/upload", methods=["POST"])
def upload_lottery_image():
    """
    Upload an image for lottery prizes.
    Requires admin password.

    Body: multipart/form-data with 'image' file

    Returns:
        {
            "success": true,
            "url": "https://..."
        }
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        if "image" not in request.files:
            return jsonify({"success": False, "error": "請上傳圖片檔案"}), 400

        file = request.files["image"]

        if file.filename == "":
            return jsonify({"success": False, "error": "請選擇檔案"}), 400

        # Validate file type
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        content_type = file.content_type

        if content_type not in allowed_types:
            return jsonify({"success": False, "error": "僅支援 JPG、PNG、GIF、WebP 格式"}), 400

        # Validate file size (max 5MB)
        file_data = file.read()
        if len(file_data) > 5 * 1024 * 1024:
            return jsonify({"success": False, "error": "檔案大小不得超過 5MB"}), 400

        from src.repositories.lottery_repository import LotteryRepository
        repo = LotteryRepository()
        url = repo.upload_image(file_data, file.filename, content_type)

        if url:
            return jsonify({"success": True, "url": url}), 200
        else:
            return jsonify({"success": False, "error": "上傳失敗"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/campaigns/<campaign_id>/stats", methods=["GET"])
def get_lottery_stats(campaign_id):
    """
    Get statistics for a campaign.
    Requires admin password.

    Returns:
        {
            "total_participants": 100,
            "total_attempts": 150,
            "total_winners": 30,
            "total_redeemed": 20,
            "prizes_stats": [
                {"name": "獎品", "total": 50, "remaining": 20, "won": 30, "redeemed": 20}
            ]
        }
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        service = LotteryService()
        stats = service.get_campaign_stats(campaign_id)

        return jsonify({
            "success": True,
            "data": stats
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/lottery/admin/campaigns/<campaign_id>/results", methods=["GET"])
def get_lottery_results(campaign_id):
    """
    Get all results for a campaign.
    Requires admin password.

    Query params:
        winners_only: Only show winners (default: false)
        limit: Number of records (default: 100)
        offset: Offset for pagination (default: 0)
    """
    try:
        if not verify_lottery_admin():
            return jsonify({"success": False, "error": "管理員密碼錯誤"}), 401

        winners_only = request.args.get("winners_only", "false").lower() == "true"
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        service = LotteryService()
        results = service.get_results(campaign_id, winners_only, limit, offset)

        return jsonify({
            "success": True,
            "data": results,
            "count": len(results)
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
