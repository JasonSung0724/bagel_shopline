"""
Inventory workflow orchestrator.
Coordinates inventory data fetching, parsing, and storage.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger

from src.services.inventory_service import InventoryService
from src.repositories.supabase_repository import InventoryRepository
from src.services.notification_service import NotificationService
from src.models.inventory import InventorySnapshot


class InventoryWorkflow:
    """
    Orchestrates inventory update workflow.

    Modes:
    1. Daily sync: Fetch today's inventory email and update DB
    2. Backfill: Fetch all historical emails and import to DB
    """

    def __init__(self, target_sender: Optional[str] = None):
        """
        Initialize inventory workflow.

        Args:
            target_sender: Email sender to filter (optional)
        """
        self.inventory_service = InventoryService()
        self.inventory_repo = InventoryRepository()
        self.notification = NotificationService()
        self.target_sender = target_sender

    def run_daily_sync(self, target_date: Optional[datetime] = None) -> bool:
        """
        Run daily inventory sync.
        Fetches the latest inventory email and updates the database.

        Args:
            target_date: Date to sync (default: today)

        Returns:
            True if successful
        """
        try:
            if target_date is None:
                target_date = datetime.now()

            date_str = target_date.strftime("%Y-%m-%d")
            logger.info(f"開始庫存同步 - 目標日期: {date_str}")

            # Step 1: Fetch inventory emails (only today)
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            next_day = start_of_day + timedelta(days=1)

            emails = self.inventory_service.fetch_inventory_emails(
                since_date=start_of_day,
                before_date=next_day,
                target_sender=self.target_sender
            )

            if not emails:
                self.notification.add_message(f"庫存同步: 沒有找到庫存明細郵件 ({date_str})")
                logger.warning("沒有找到庫存明細郵件")
                return False

            # Step 2: Get the latest email (most recent)
            latest_email = max(emails, key=lambda e: e.date)
            logger.info(f"使用最新郵件: {latest_email.date}")

            # Step 3: Parse and save
            snapshot = self.inventory_service.process_email_attachment(latest_email)

            if not snapshot:
                self.notification.add_message("庫存同步: 解析郵件附件失敗")
                logger.error("解析郵件附件失敗")
                return False

            # Step 4: Save to database
            if self.inventory_repo.is_connected:
                snapshot_id = self.inventory_repo.save_snapshot(snapshot)
                if snapshot_id:
                    logger.success(f"庫存快照已保存: {snapshot_id}")
            else:
                logger.warning("Supabase 未連接，跳過資料庫保存")

            # Step 5: Send notification
            self._send_sync_notification(snapshot)

            logger.success("庫存同步完成")
            return True

        except Exception as e:
            logger.error(f"庫存同步失敗: {e}")
            self.notification.add_message(f"庫存同步失敗: {e}")
            self.notification.send_and_clear()
            return False

    def sync_specific_date(self, target_date: datetime, send_notification: bool = False) -> dict:
        """
        Sync inventory for a specific date (patch mode).
        Searches for emails on that specific date and imports to database.

        Args:
            target_date: The specific date to sync
            send_notification: Whether to send LINE notification

        Returns:
            dict with sync result details
        """
        result = {
            "success": False,
            "date": target_date.strftime("%Y-%m-%d"),
            "message": "",
            "snapshot_id": None,
            "email_count": 0,
            "snapshot_date": None,
        }

        try:
            date_str = target_date.strftime("%Y-%m-%d")
            logger.info(f"開始補同步指定日期 - 目標日期: {date_str}")

            # Step 1: Fetch emails for that specific date
            # IMAP SINCE is inclusive, BEFORE is exclusive
            # To get emails for "2025-12-25", use SINCE 25-Dec-2025 BEFORE 26-Dec-2025
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            next_day = start_of_day + timedelta(days=1)

            emails = self.inventory_service.fetch_inventory_emails(
                since_date=start_of_day,
                before_date=next_day,
                target_sender=self.target_sender
            )

            result["email_count"] = len(emails)

            if not emails:
                result["message"] = f"沒有找到 {date_str} 的庫存明細郵件"
                logger.warning(result["message"])
                return result

            # Step 2: Get the latest email for that day
            target_email = max(emails, key=lambda e: e.date)
            logger.info(f"找到郵件: {target_email.date}")

            # Step 3: Parse attachment
            snapshot = self.inventory_service.process_email_attachment(target_email)

            if not snapshot:
                result["message"] = "解析郵件附件失敗"
                logger.error(result["message"])
                return result

            result["snapshot_date"] = snapshot.snapshot_date.strftime("%Y-%m-%d %H:%M")

            # Step 4: Save to database
            if not self.inventory_repo.is_connected:
                result["message"] = "資料庫未連接"
                logger.error(result["message"])
                return result

            snapshot_id = self.inventory_repo.save_snapshot(snapshot)

            if snapshot_id:
                result["success"] = True
                result["snapshot_id"] = snapshot_id
                result["message"] = f"成功同步 {date_str} 的庫存資料"
                logger.success(result["message"])

                # Optional notification
                if send_notification:
                    self._send_sync_notification(snapshot)
            else:
                result["message"] = "保存到資料庫失敗"
                logger.error(result["message"])

            return result

        except Exception as e:
            result["message"] = f"同步失敗: {str(e)}"
            logger.error(result["message"])
            return result

    def sync_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        send_notification: bool = False
    ) -> dict:
        """
        Sync inventory for a date range (batch patch mode).
        Processes each day in the range sequentially.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            send_notification: Whether to send LINE notification after all done

        Returns:
            dict with batch sync result details
        """
        result = {
            "success": False,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "total_days": 0,
            "synced_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "details": [],
            "message": "",
        }

        try:
            # Calculate date range
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

            dates_to_sync = []
            while current_date <= end:
                dates_to_sync.append(current_date)
                current_date += timedelta(days=1)

            result["total_days"] = len(dates_to_sync)
            logger.info(f"開始批次同步 - {result['start_date']} ~ {result['end_date']} ({len(dates_to_sync)} 天)")

            # Process each date
            for target_date in dates_to_sync:
                day_result = self.sync_specific_date(target_date, send_notification=False)

                detail = {
                    "date": day_result["date"],
                    "success": day_result["success"],
                    "message": day_result["message"],
                    "snapshot_id": day_result.get("snapshot_id"),
                }
                result["details"].append(detail)

                if day_result["success"]:
                    result["synced_count"] += 1
                elif day_result["email_count"] == 0:
                    result["skipped_count"] += 1
                else:
                    result["failed_count"] += 1

            # Overall success if at least one synced
            result["success"] = result["synced_count"] > 0
            result["message"] = (
                f"批次同步完成: 成功 {result['synced_count']} 天, "
                f"跳過 {result['skipped_count']} 天, "
                f"失敗 {result['failed_count']} 天"
            )

            logger.success(result["message"])

            # Optional notification
            if send_notification and result["synced_count"] > 0:
                self.notification.add_message("=== 批次庫存同步完成 ===")
                self.notification.add_message(f"日期範圍: {result['start_date']} ~ {result['end_date']}")
                self.notification.add_message(result["message"])
                self.notification.send_and_clear()

            return result

        except Exception as e:
            result["message"] = f"批次同步失敗: {str(e)}"
            logger.error(result["message"])
            return result

    def run_backfill(
        self,
        days_back: int = 365,
        dry_run: bool = False,
        start_days_ago: int = 0
    ) -> int:
        """
        Backfill historical inventory data from emails.
        Searches all emails and imports to database.

        Args:
            days_back: How many days to look back (from start_days_ago)
            dry_run: If True, don't save to database
            start_days_ago: Start from N days ago (default: 0 = today)
                           e.g. start_days_ago=30, days_back=30 = 回溯第 30~60 天前的資料

        Returns:
            Number of snapshots imported
        """
        try:
            if start_days_ago > 0:
                logger.info(f"開始歷史資料回填 - 從 {start_days_ago} 天前開始，回溯 {days_back} 天")
            else:
                logger.info(f"開始歷史資料回填 - 回溯 {days_back} 天")

            # Step 1: Fetch all historical emails
            emails = self.inventory_service.fetch_all_inventory_emails(
                target_sender=self.target_sender,
                days_back=days_back + start_days_ago  # 總共要抓的天數
            )

            # Filter by start_days_ago if specified
            if start_days_ago > 0 and emails:
                cutoff_date = datetime.now() - timedelta(days=start_days_ago)
                emails = [e for e in emails if e.date < cutoff_date]
                logger.info(f"篩選後剩餘 {len(emails)} 封郵件 (排除近 {start_days_ago} 天)")

            if not emails:
                logger.warning("沒有找到歷史庫存郵件")
                return 0

            logger.info(f"找到 {len(emails)} 封歷史郵件")

            # Step 2: Process all emails
            snapshots = self.inventory_service.process_multiple_emails(emails)

            if not snapshots:
                logger.warning("沒有有效的庫存快照")
                return 0

            logger.info(f"成功解析 {len(snapshots)} 個庫存快照")

            if dry_run:
                logger.info("Dry run 模式，不保存到資料庫")
                self._print_backfill_summary(snapshots)
                return len(snapshots)

            # Step 3: Save all snapshots
            if not self.inventory_repo.is_connected:
                logger.error("Supabase 未連接，無法保存")
                return 0

            saved_count = 0
            for snapshot in snapshots:
                snapshot_id = self.inventory_repo.save_snapshot(snapshot)
                if snapshot_id:
                    saved_count += 1
                    logger.info(f"已保存: {snapshot.snapshot_date.date()} ({saved_count}/{len(snapshots)})")

            logger.success(f"歷史資料回填完成: 成功 {saved_count}/{len(snapshots)}")
            return saved_count

        except Exception as e:
            logger.error(f"歷史資料回填失敗: {e}")
            return 0

    def get_latest_inventory(self) -> Optional[dict]:
        """
        Get the latest inventory data.
        First tries database, falls back to local parsing.

        Returns:
            Inventory data dict or None
        """
        # Try database first
        if self.inventory_repo.is_connected:
            data = self.inventory_repo.get_latest_snapshot()
            if data:
                return data

        logger.info("資料庫無資料，返回空值")
        return None

    def _send_sync_notification(self, snapshot: InventorySnapshot) -> None:
        """Send LINE notification about sync result."""
        self.notification.add_message("=== 庫存同步完成 ===")
        self.notification.add_message(f"資料日期: {snapshot.snapshot_date.strftime('%Y-%m-%d %H:%M')}")
        self.notification.add_message(f"來源: {snapshot.source_file}")
        self.notification.add_message(f"麵包總量: {snapshot.total_bread_stock} 個")
        self.notification.add_message(f"盒子總量: {snapshot.total_box_stock} 個")
        self.notification.add_message(f"袋子總量: {snapshot.total_bag_rolls} 捲")

        if snapshot.low_stock_count > 0:
            self.notification.add_message(f"⚠️ 庫存不足項目: {snapshot.low_stock_count} 項")

            # List low stock items
            all_items = snapshot.bread_items + snapshot.box_items + snapshot.bag_items
            low_items = [item for item in all_items if item.stock_status == "low"]
            for item in low_items[:5]:  # 最多顯示 5 項
                self.notification.add_message(f"  - {item.name}: {item.current_stock} {item.unit}")

        # self.notification.send_and_clear()

    def _print_backfill_summary(self, snapshots: List[InventorySnapshot]) -> None:
        """Print summary of backfill results."""
        print("\n=== 回填摘要 (Dry Run) ===")
        print(f"總快照數: {len(snapshots)}")

        if snapshots:
            print(f"日期範圍: {snapshots[0].snapshot_date.date()} ~ {snapshots[-1].snapshot_date.date()}")

            for snapshot in snapshots[-5:]:  # 顯示最近 5 筆
                print(f"  {snapshot.snapshot_date.date()}: "
                      f"麵包 {snapshot.total_bread_stock}, "
                      f"盒子 {snapshot.total_box_stock}, "
                      f"袋子 {snapshot.total_bag_rolls} 捲")
