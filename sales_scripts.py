"""
Sales backfill script (銷量回填腳本).

This script is a CLI wrapper for SalesService.backfill().

Usage:
    # Backfill specific date range
    python sales_scripts.py --start 2026-01-01 --end 2026-01-05

    # Backfill single day
    python sales_scripts.py --start 2026-01-05 --end 2026-01-05

    # Dry run (don't save to database)
    python sales_scripts.py --start 2026-01-01 --end 2026-01-05 --dry-run

    # Daily sync is handled by main_scripts.py, not this script
"""
# Load .env FIRST before any other imports
from pathlib import Path
from dotenv import load_dotenv
_project_root = Path(__file__).resolve().parent
load_dotenv(_project_root / ".env")

import argparse
from datetime import datetime
from loguru import logger

from src.utils.logger import setup_logger
from src.services.sales_service import SalesService


def main():
    """Run sales backfill."""
    parser = argparse.ArgumentParser(description="Sales backfill script (銷量回填腳本)")
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Start date in YYYY-MM-DD format (required)"
    )
    parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="End date in YYYY-MM-DD format (required)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (don't save to database)"
    )

    args = parser.parse_args()

    # Parse dates
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError:
        print("錯誤: 日期格式必須是 YYYY-MM-DD")
        print("例如: python sales_scripts.py --start 2026-01-01 --end 2026-01-05")
        return

    # Validate date range
    if start_date > end_date:
        print("錯誤: 開始日期不能晚於結束日期")
        return

    # Setup logging
    setup_logger(log_file="logs/sales.log")

    logger.info("=" * 50)
    logger.info("開始執行 sales_scripts.py (回填模式)")
    logger.info("=" * 50)
    logger.info(f"日期範圍: {args.start} ~ {args.end}")

    if args.dry_run:
        logger.info("[DRY RUN] 不會保存到資料庫")

    # Run backfill via SalesService
    sales_service = SalesService()
    success_count, fail_count = sales_service.backfill(
        start_date=start_date,
        end_date=end_date,
        dry_run=args.dry_run
    )

    if success_count > 0:
        logger.success(f"回填完成，成功 {success_count} 筆，失敗 {fail_count} 筆")
    else:
        logger.warning("回填完成，沒有匯入任何資料")


if __name__ == "__main__":
    main()
