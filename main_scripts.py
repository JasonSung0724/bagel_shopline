"""
Main daily script for processing Flowtide orders.

This script:
1. Fetches Flowtide Excel from email
2. Updates C2C orders in Google Sheet
3. Updates ShopLine orders via API
4. Sends LINE notification

Usage:
    python main_scripts.py                           # 執行今日任務
    python main_scripts.py --date 2026-01-10        # 執行指定日期
    python main_scripts.py --from 2026-01-05 --to 2026-01-10  # 執行日期範圍
"""
import argparse
from datetime import datetime, timedelta
from src.utils.logger import setup_logger
from src.orchestrator.daily_workflow import DailyWorkflow
from loguru import logger


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def get_date_range(args) -> list[datetime]:
    """
    Get list of dates to process based on arguments.
    
    Returns:
        List of datetime objects to process
    """
    if args.date:
        # 單一日期
        return [parse_date(args.date)]
    elif args.from_date and args.to_date:
        # 日期範圍
        start = parse_date(args.from_date)
        end = parse_date(args.to_date)
        
        if start > end:
            start, end = end, start
            logger.warning("起始日期大於結束日期，已自動交換")
        
        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)
        return dates
    else:
        # 預設今日
        return [datetime.now()]


def main():
    """Run the daily order processing workflow."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="執行每日訂單處理任務",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python main_scripts.py                           # 執行今日任務
  python main_scripts.py --date 2026-01-10        # 執行指定日期
  python main_scripts.py --from 2026-01-05 --to 2026-01-10  # 執行日期範圍
        """
    )
    parser.add_argument(
        "--date", "-d",
        type=str,
        help="指定執行日期 (格式: YYYY-MM-DD)"
    )
    parser.add_argument(
        "--from", "-f",
        dest="from_date",
        type=str,
        help="起始日期 (格式: YYYY-MM-DD)，需搭配 --to 使用"
    )
    parser.add_argument(
        "--to", "-t",
        dest="to_date",
        type=str,
        help="結束日期 (格式: YYYY-MM-DD)，需搭配 --from 使用"
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="不發送客戶通知 (批次補執行時建議使用)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if (args.from_date and not args.to_date) or (args.to_date and not args.from_date):
        parser.error("--from 和 --to 必須同時使用")
    
    if args.date and (args.from_date or args.to_date):
        parser.error("--date 不能與 --from/--to 同時使用")
    
    # Setup logging
    setup_logger(log_file="logs/app.log")
    
    # Get dates to process
    dates = get_date_range(args)
    total_dates = len(dates)
    notify_customers = not args.no_notify
    
    logger.info("=" * 50)
    logger.info("開始執行 main_scripts.py")
    if total_dates > 1:
        logger.info(f"批次執行模式: 共 {total_dates} 天")
        logger.info(f"日期範圍: {dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}")
    else:
        logger.info(f"目標日期: {dates[0].strftime('%Y-%m-%d')}")
    logger.info(f"客戶通知: {'啟用' if notify_customers else '停用'}")
    logger.info("=" * 50)
    
    # Run workflow for each date
    workflow = DailyWorkflow(notify_customers=notify_customers)
    success_count = 0
    fail_count = 0
    
    for i, target_date in enumerate(dates, 1):
        date_str = target_date.strftime("%Y-%m-%d")
        
        if total_dates > 1:
            logger.info(f"\n{'=' * 30}")
            logger.info(f"處理進度: {i}/{total_dates} - {date_str}")
            logger.info(f"{'=' * 30}")
        
        success = workflow.run(target_date=target_date)
        
        if success:
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    logger.info("=" * 50)
    if total_dates > 1:
        logger.info(f"批次執行完成: 成功 {success_count} 天, 失敗 {fail_count} 天")
    
    if fail_count == 0:
        logger.success("main_scripts.py 執行完成")
    else:
        logger.warning("main_scripts.py 執行完成（有警告）")
    
    return fail_count == 0


if __name__ == "__main__":
    main()
