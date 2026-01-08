"""
Sales sync script (銷量同步腳本).

This script:
1. Fetches sales Excel from email (A442_QC)
2. Parses and aggregates sales data (訂單實出)
3. Saves to Supabase database (daily_sales, master_sales_products)
4. Sends LINE notification

Usage:
    # Daily sync (latest email)
    python sales_scripts.py

    # Backfill historical data
    python sales_scripts.py --backfill --days 365

    # Dry run (don't save to database)
    python sales_scripts.py --backfill --days 30 --dry-run
"""
# Load .env FIRST before any other imports
from pathlib import Path
from dotenv import load_dotenv
_project_root = Path(__file__).resolve().parent
load_dotenv(_project_root / ".env")

import argparse
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from src.utils.logger import setup_logger
from src.services.email_service import EmailService
from src.services.sales_service import SalesService
from src.services.notification_service import NotificationService


class SalesWorkflow:
    """銷量資料同步工作流程"""

    def __init__(self, target_sender: Optional[str] = None):
        """
        初始化

        Args:
            target_sender: 過濾郵件寄件者
        """
        self.email_service = EmailService()
        self.sales_service = SalesService()
        self.notification = NotificationService()
        self.target_sender = target_sender or "service@flowtide.com.tw"

    def run_daily_sync(self) -> bool:
        """
        執行每日同步（抓取最新的銷售資料）

        Returns:
            True if successful
        """
        try:
            logger.info("開始每日銷量同步...")

            # 抓取今天的郵件
            target_date = datetime.now()
            emails = self.email_service.fetch_flowtide_emails(target_date)

            if not emails:
                logger.warning(f"今天沒有收到逢泰 Excel")
                self.notification.add_message("銷量同步-沒有收到逢泰 Excel")
                self.notification.send_and_clear()
                return False

            # 處理銷量資料
            success_count, fail_count = self.sales_service.process_sales_from_emails(emails)

            # 發送通知
            if success_count > 0:
                self.notification.add_message(f"銷量同步-成功處理 {success_count} 個檔案")
            if fail_count > 0:
                self.notification.add_message(f"銷量同步-處理失敗 {fail_count} 個檔案")

            self.notification.send_and_clear()

            return success_count > 0

        except Exception as e:
            logger.error(f"每日銷量同步失敗: {e}")
            self.notification.add_message(f"銷量同步失敗: {e}")
            self.notification.send_and_clear()
            return False

    def run_backfill(
        self,
        days_back: int = 365,
        dry_run: bool = False,
        start_days_ago: int = 0
    ) -> int:
        """
        回填歷史銷量資料

        Args:
            days_back: 回溯天數
            dry_run: True = 不保存到資料庫
            start_days_ago: 從 N 天前開始回溯

        Returns:
            成功匯入的檔案數量
        """
        try:
            logger.info("開始回填歷史銷量資料...")

            # 計算日期範圍
            end_date = datetime.now() - timedelta(days=start_days_ago)
            start_date = end_date - timedelta(days=days_back)

            logger.info(f"日期範圍: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

            # 抓取郵件
            emails = self._fetch_emails_in_range(start_date, end_date)

            if not emails:
                logger.warning("沒有找到符合條件的郵件")
                return 0

            logger.info(f"找到 {len(emails)} 封郵件")

            # 處理每封郵件
            total_success = 0
            total_fail = 0

            for email in emails:
                try:
                    # 取得逢泰出貨 Excel
                    qc_attachments = email.get_flowtide_attachments()

                    for attachment in qc_attachments:
                        try:
                            logger.info(f"處理附件: {attachment.filename}")

                            if dry_run:
                                # Dry run: 只解析不保存
                                sale_date, sales_data = self.sales_service.parse_sales_excel(
                                    attachment.content,
                                    attachment.filename
                                )
                                logger.info(f"[DRY RUN] 解析成功: {sale_date.strftime('%Y-%m-%d')}, {len(sales_data)} 個品項")
                                total_success += 1
                            else:
                                # 實際保存
                                sale_date, sales_data = self.sales_service.parse_sales_excel(
                                    attachment.content,
                                    attachment.filename
                                )

                                if self.sales_service.save_daily_sales(sale_date, sales_data):
                                    total_success += 1
                                else:
                                    total_fail += 1

                        except Exception as e:
                            logger.error(f"處理附件失敗 {attachment.filename}: {e}")
                            total_fail += 1

                except Exception as e:
                    logger.error(f"處理郵件失敗: {e}")
                    total_fail += 1

            # 顯示結果
            logger.info("=" * 80)
            logger.info(f"回填完成: 成功 {total_success} 個, 失敗 {total_fail} 個")
            logger.info("=" * 80)

            return total_success

        except Exception as e:
            logger.error(f"回填歷史資料失敗: {e}")
            return 0

    def _fetch_emails_in_range(self, start_date: datetime, end_date: datetime):
        """
        抓取日期範圍內的所有郵件

        Args:
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            郵件列表
        """
        all_emails = []
        current_date = start_date

        while current_date <= end_date:
            try:
                emails = self.email_service.fetch_flowtide_emails(current_date)
                if emails:
                    all_emails.extend(emails)
                    logger.info(f"{current_date.strftime('%Y-%m-%d')}: 找到 {len(emails)} 封郵件")
            except Exception as e:
                logger.warning(f"{current_date.strftime('%Y-%m-%d')}: 抓取郵件失敗 - {e}")

            current_date += timedelta(days=1)

        return all_emails


def main():
    """Run sales sync or backfill."""
    parser = argparse.ArgumentParser(description="Sales sync script (銷量同步腳本)")
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
    parser.add_argument(
        "--sender",
        type=str,
        default=None,
        help="Filter by sender email address"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logger(log_file="logs/sales.log")

    logger.info("=" * 50)
    logger.info("開始執行 sales_scripts.py")
    logger.info("=" * 50)

    workflow = SalesWorkflow(target_sender=args.sender)

    if args.backfill:
        # Backfill mode
        if args.start_from > 0:
            logger.info(f"模式: 歷史資料回填 (從 {args.start_from} 天前開始，回溯 {args.days} 天)")
        else:
            logger.info(f"模式: 歷史資料回填 (回溯 {args.days} 天)")
        if args.dry_run:
            logger.info("Dry run 模式，不會保存到資料庫")

        count = workflow.run_backfill(
            days_back=args.days,
            dry_run=args.dry_run,
            start_days_ago=args.start_from
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
            logger.success("sales_scripts.py 執行完成")
        else:
            logger.warning("sales_scripts.py 執行完成（有警告）")

        return success


if __name__ == "__main__":
    main()
