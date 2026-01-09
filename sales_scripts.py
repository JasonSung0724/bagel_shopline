"""
Sales sync script (銷量同步腳本).

This script is a CLI wrapper for SalesService.

Usage:
    # Daily sync (via main_scripts.py, not this script)
    python main_scripts.py

    # Backfill historical data
    python sales_scripts.py --backfill --days 30

    # Dry run (don't save to database)
    python sales_scripts.py --backfill --days 30 --dry-run
"""
# Load .env FIRST before any other imports
from pathlib import Path
from dotenv import load_dotenv
_project_root = Path(__file__).resolve().parent
load_dotenv(_project_root / ".env")

import argparse
from loguru import logger

from src.utils.logger import setup_logger
from src.services.sales_service import SalesService


def main():
    """Run sales backfill."""
    parser = argparse.ArgumentParser(description="Sales backfill script (銷量回填腳本)")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Run backfill mode (required)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back (default: 30)"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Start backfill from N days ago (default: 0 = today). "
             "Example: --start-from 30 --days 30 = backfill days 30~60"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (don't save to database)"
    )

    args = parser.parse_args()

    # Require --backfill flag
    if not args.backfill:
        print("此腳本專門用於回填歷史資料。")
        print("每日同步請使用 main_scripts.py\n")
        print("用法:")
        print("  python sales_scripts.py --backfill --days 30")
        print("  python sales_scripts.py --backfill --days 30 --dry-run")
        return

    # Setup logging
    setup_logger(log_file="logs/sales.log")

    logger.info("=" * 50)
    logger.info("開始執行 sales_scripts.py (回填模式)")
    logger.info("=" * 50)

    if args.start_from > 0:
        logger.info(f"從 {args.start_from} 天前開始，回溯 {args.days} 天")
    else:
        logger.info(f"回溯 {args.days} 天")

    if args.dry_run:
        logger.info("[DRY RUN] 不會保存到資料庫")

    # Run backfill via SalesService
    sales_service = SalesService()
    success_count, fail_count = sales_service.backfill(
        days_back=args.days,
        start_days_ago=args.start_from,
        dry_run=args.dry_run
    )

    if success_count > 0:
        logger.success(f"回填完成，成功 {success_count} 筆，失敗 {fail_count} 筆")
    else:
        logger.warning("回填完成，沒有匯入任何資料")


if __name__ == "__main__":
    main()
