"""
Inventory sync script.

This script:
1. Fetches inventory Excel from email (A442庫存明細)
2. Parses and aggregates inventory data
3. Saves to Supabase database
4. Sends LINE notification

Usage:
    # Daily sync (latest email)
    python inventory_scripts.py

    # Backfill historical data
    python inventory_scripts.py --backfill --days 365

    # Dry run (don't save to database)
    python inventory_scripts.py --backfill --days 30 --dry-run
"""
# Load .env FIRST before any other imports
from pathlib import Path
from dotenv import load_dotenv
_project_root = Path(__file__).resolve().parent
load_dotenv(_project_root / ".env")

import argparse
from src.utils.logger import setup_logger
from src.orchestrator.inventory_workflow import InventoryWorkflow
from loguru import logger


def main():
    """Run inventory sync or backfill."""
    parser = argparse.ArgumentParser(description="Inventory sync script")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Run backfill mode (import all historical data)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days to look back for backfill (default: 365)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (don't save to database)"
    )
    parser.add_argument(
        "--sender",
        type=str,
        default=None,
        help="Filter by sender email address"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logger(log_file="logs/inventory.log")

    logger.info("=" * 50)
    logger.info("開始執行 inventory_scripts.py")
    logger.info("=" * 50)

    workflow = InventoryWorkflow(target_sender=args.sender)

    if args.backfill:
        # Backfill mode
        logger.info(f"模式: 歷史資料回填 (回溯 {args.days} 天)")
        if args.dry_run:
            logger.info("Dry run 模式，不會保存到資料庫")

        count = workflow.run_backfill(
            days_back=args.days,
            dry_run=args.dry_run
        )

        if count > 0:
            logger.success(f"回填完成，共匯入 {count} 筆資料")
        else:
            logger.warning("回填完成，沒有匯入任何資料")

    else:
        # Daily sync mode
        logger.info("模式: 每日同步")
        success = workflow.run_daily_sync()

        if success:
            logger.success("inventory_scripts.py 執行完成")
        else:
            logger.warning("inventory_scripts.py 執行完成（有警告）")

        return success


if __name__ == "__main__":
    main()
