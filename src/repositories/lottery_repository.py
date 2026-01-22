"""
Lottery (Scratch Card) Repository for database operations.
"""

import os
import uuid
import secrets
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from dotenv import load_dotenv

_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not installed. Run: pip install supabase")


class LotteryRepository:
    """
    Repository for lottery (scratch card) database operations.

    Tables:
        - lottery_campaigns: 刮刮樂活動
        - lottery_prizes: 獎品設定
        - lottery_participants: 參與者記錄
        - lottery_results: 刮刮樂結果
        - lottery_admin_logs: 管理操作日誌
    """

    TABLE_CAMPAIGNS = "lottery_campaigns"
    TABLE_PRIZES = "lottery_prizes"
    TABLE_PARTICIPANTS = "lottery_participants"
    TABLE_RESULTS = "lottery_results"
    TABLE_ADMIN_LOGS = "lottery_admin_logs"

    def __init__(self):
        """Initialize Supabase client."""
        self.client: Optional[Client] = None

        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase client not available")
            return

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            logger.warning("Supabase credentials not configured")
            return

        try:
            self.client = create_client(url, key)
            logger.info("Lottery repository initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase for lottery: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if Supabase client is available."""
        return self.client is not None

    # =========================================================================
    # Campaign Management (活動管理)
    # =========================================================================

    def create_campaign(self, data: Dict[str, Any]) -> Optional[Dict]:
        """
        Create a new lottery campaign.

        Args:
            data: Campaign data including:
                - name: 活動名稱
                - description: 活動說明
                - start_date: 開始時間
                - end_date: 結束時間
                - max_attempts_per_user: 每人可刮次數 (default: 1)
                - require_login: 是否需要登入 (default: true)

        Returns:
            Created campaign data or None
        """
        if not self.is_connected:
            return None

        try:
            campaign_data = {
                "name": data.get("name"),
                "description": data.get("description"),
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "status": data.get("status", "draft"),
                "max_attempts_per_user": data.get("max_attempts_per_user", 1),
                "require_login": data.get("require_login", True),
            }

            result = self.client.table(self.TABLE_CAMPAIGNS).insert(campaign_data).execute()

            if result.data:
                logger.success(f"Created campaign: {result.data[0]['id']}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to create campaign: {e}")
            return None

    def get_campaign(self, campaign_id: str) -> Optional[Dict]:
        """Get a campaign by ID with prizes."""
        if not self.is_connected:
            return None

        try:
            result = self.client.table(self.TABLE_CAMPAIGNS).select("*").eq("id", campaign_id).execute()

            if not result.data:
                return None

            campaign = result.data[0]

            # Get prizes for this campaign
            prizes_result = self.client.table(self.TABLE_PRIZES).select("*").eq("campaign_id", campaign_id).order("display_order").execute()
            campaign["prizes"] = prizes_result.data or []

            return campaign

        except Exception as e:
            logger.error(f"Failed to get campaign: {e}")
            return None

    def get_active_campaign(self, campaign_id: str) -> Optional[Dict]:
        """Get an active campaign (status=active and within date range)."""
        if not self.is_connected:
            return None

        try:
            now = datetime.now().isoformat()

            result = (
                self.client.table(self.TABLE_CAMPAIGNS)
                .select("*")
                .eq("id", campaign_id)
                .eq("status", "active")
                .lte("start_date", now)
                .gte("end_date", now)
                .execute()
            )

            if not result.data:
                return None

            campaign = result.data[0]

            # Get active prizes
            prizes_result = (
                self.client.table(self.TABLE_PRIZES)
                .select("*")
                .eq("campaign_id", campaign_id)
                .eq("is_active", True)
                .order("display_order")
                .execute()
            )
            campaign["prizes"] = prizes_result.data or []

            return campaign

        except Exception as e:
            logger.error(f"Failed to get active campaign: {e}")
            return None

    def list_campaigns(self, status: Optional[str] = None) -> List[Dict]:
        """List all campaigns, optionally filtered by status."""
        if not self.is_connected:
            return []

        try:
            query = self.client.table(self.TABLE_CAMPAIGNS).select("*")

            if status:
                query = query.eq("status", status)

            result = query.order("created_at", desc=True).execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to list campaigns: {e}")
            return []

    def update_campaign(self, campaign_id: str, data: Dict[str, Any]) -> Optional[Dict]:
        """Update a campaign."""
        if not self.is_connected:
            return None

        try:
            data["updated_at"] = datetime.now().isoformat()

            result = (
                self.client.table(self.TABLE_CAMPAIGNS)
                .update(data)
                .eq("id", campaign_id)
                .execute()
            )

            if result.data:
                logger.info(f"Updated campaign: {campaign_id}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to update campaign: {e}")
            return None

    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign (cascades to prizes, participants, results)."""
        if not self.is_connected:
            return False

        try:
            self.client.table(self.TABLE_CAMPAIGNS).delete().eq("id", campaign_id).execute()
            logger.info(f"Deleted campaign: {campaign_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete campaign: {e}")
            return False

    # =========================================================================
    # Prize Management (獎品管理)
    # =========================================================================

    def add_prize(self, campaign_id: str, data: Dict[str, Any]) -> Optional[Dict]:
        """
        Add a prize to a campaign.

        Args:
            campaign_id: Campaign ID
            data: Prize data including:
                - name: 獎品名稱
                - description: 獎品說明
                - prize_type: 類型 (physical/coupon/points/free_shipping/discount/none)
                - prize_value: 獎品價值/折扣碼等
                - total_quantity: 總數量
                - probability: 中獎機率 (0.0000 ~ 1.0000)
                - display_order: 顯示順序

        Returns:
            Created prize data or None
        """
        if not self.is_connected:
            return None

        try:
            prize_data = {
                "campaign_id": campaign_id,
                "name": data.get("name"),
                "description": data.get("description"),
                "prize_type": data.get("prize_type", "physical"),
                "prize_value": data.get("prize_value"),
                "image_url": data.get("image_url"),
                "total_quantity": data.get("total_quantity", 0),
                "remaining_quantity": data.get("total_quantity", 0),  # 初始 = 總數
                "probability": data.get("probability", 0),
                "display_order": data.get("display_order", 0),
                "is_active": data.get("is_active", True),
            }

            result = self.client.table(self.TABLE_PRIZES).insert(prize_data).execute()

            if result.data:
                logger.success(f"Added prize: {result.data[0]['id']}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to add prize: {e}")
            return None

    def get_prizes(self, campaign_id: str, active_only: bool = False) -> List[Dict]:
        """Get all prizes for a campaign."""
        if not self.is_connected:
            return []

        try:
            query = self.client.table(self.TABLE_PRIZES).select("*").eq("campaign_id", campaign_id)

            if active_only:
                query = query.eq("is_active", True)

            result = query.order("display_order").execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get prizes: {e}")
            return []

    def update_prize(self, prize_id: str, data: Dict[str, Any]) -> Optional[Dict]:
        """Update a prize."""
        if not self.is_connected:
            return None

        try:
            data["updated_at"] = datetime.now().isoformat()

            result = (
                self.client.table(self.TABLE_PRIZES)
                .update(data)
                .eq("id", prize_id)
                .execute()
            )

            if result.data:
                logger.info(f"Updated prize: {prize_id}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to update prize: {e}")
            return None

    def delete_prize(self, prize_id: str) -> bool:
        """Delete a prize."""
        if not self.is_connected:
            return False

        try:
            self.client.table(self.TABLE_PRIZES).delete().eq("id", prize_id).execute()
            logger.info(f"Deleted prize: {prize_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete prize: {e}")
            return False

    def decrement_prize_quantity(self, prize_id: str) -> bool:
        """
        Decrease remaining quantity of a prize by 1.
        Returns False if quantity is already 0.
        """
        if not self.is_connected:
            return False

        try:
            # Get current quantity
            result = self.client.table(self.TABLE_PRIZES).select("remaining_quantity").eq("id", prize_id).execute()

            if not result.data:
                return False

            current = result.data[0]["remaining_quantity"]
            if current <= 0:
                return False

            # Update
            self.client.table(self.TABLE_PRIZES).update({
                "remaining_quantity": current - 1,
                "updated_at": datetime.now().isoformat()
            }).eq("id", prize_id).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to decrement prize quantity: {e}")
            return False

    # =========================================================================
    # Participant Management (參與者管理)
    # =========================================================================

    def get_or_create_participant(
        self,
        campaign_id: str,
        shopline_customer_id: str,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get existing participant or create new one.

        Args:
            campaign_id: Campaign ID
            shopline_customer_id: Shopline customer ID
            customer_email: Customer email (optional)
            customer_name: Customer name (optional)

        Returns:
            Participant data
        """
        if not self.is_connected:
            return None

        try:
            # Try to find existing participant
            result = (
                self.client.table(self.TABLE_PARTICIPANTS)
                .select("*")
                .eq("campaign_id", campaign_id)
                .eq("shopline_customer_id", shopline_customer_id)
                .execute()
            )

            if result.data:
                return result.data[0]

            # Create new participant
            participant_data = {
                "campaign_id": campaign_id,
                "shopline_customer_id": shopline_customer_id,
                "customer_email": customer_email,
                "customer_name": customer_name,
                "attempt_count": 0,
            }

            insert_result = self.client.table(self.TABLE_PARTICIPANTS).insert(participant_data).execute()

            if insert_result.data:
                return insert_result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get/create participant: {e}")
            return None

    def increment_attempt_count(self, participant_id: str) -> bool:
        """Increment the attempt count for a participant."""
        if not self.is_connected:
            return False

        try:
            # Get current count
            result = self.client.table(self.TABLE_PARTICIPANTS).select("attempt_count").eq("id", participant_id).execute()

            if not result.data:
                return False

            current = result.data[0]["attempt_count"] or 0
            now = datetime.now().isoformat()

            # Update
            update_data = {
                "attempt_count": current + 1,
                "last_attempt_at": now,
                "updated_at": now,
            }

            # Set first_attempt_at if this is the first attempt
            if current == 0:
                update_data["first_attempt_at"] = now

            self.client.table(self.TABLE_PARTICIPANTS).update(update_data).eq("id", participant_id).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to increment attempt count: {e}")
            return False

    def get_participant_attempts(self, campaign_id: str, shopline_customer_id: str) -> int:
        """Get the number of attempts a participant has made."""
        if not self.is_connected:
            return 0

        try:
            result = (
                self.client.table(self.TABLE_PARTICIPANTS)
                .select("attempt_count")
                .eq("campaign_id", campaign_id)
                .eq("shopline_customer_id", shopline_customer_id)
                .execute()
            )

            if result.data:
                return result.data[0]["attempt_count"] or 0
            return 0

        except Exception as e:
            logger.error(f"Failed to get participant attempts: {e}")
            return 0

    # =========================================================================
    # Result Management (結果管理)
    # =========================================================================

    def create_result(
        self,
        campaign_id: str,
        participant_id: str,
        prize_id: Optional[str],
        prize_name: Optional[str],
        prize_type: Optional[str],
        is_winner: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create a lottery result record.

        Args:
            campaign_id: Campaign ID
            participant_id: Participant ID
            prize_id: Prize ID (None if not winner)
            prize_name: Prize name for record
            prize_type: Prize type for record
            is_winner: Whether the participant won
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created result data with redemption_code if winner
        """
        if not self.is_connected:
            return None

        try:
            # Generate unique redemption code for winners
            redemption_code = None
            if is_winner and prize_id:
                redemption_code = self._generate_redemption_code()

            result_data = {
                "campaign_id": campaign_id,
                "participant_id": participant_id,
                "prize_id": prize_id,
                "prize_name": prize_name,
                "prize_type": prize_type,
                "redemption_code": redemption_code,
                "is_winner": is_winner,
                "is_redeemed": False,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "scratched_at": datetime.now().isoformat(),
            }

            result = self.client.table(self.TABLE_RESULTS).insert(result_data).execute()

            if result.data:
                logger.info(f"Created result: {result.data[0]['id']}, winner: {is_winner}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to create result: {e}")
            return None

    def _generate_redemption_code(self) -> str:
        """Generate a unique redemption code."""
        # Format: XXXX-XXXX-XXXX (12 characters)
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Exclude confusing chars: I, O, 0, 1
        code = ''.join(secrets.choice(chars) for _ in range(12))
        return f"{code[:4]}-{code[4:8]}-{code[8:12]}"

    def get_result_by_code(self, redemption_code: str) -> Optional[Dict]:
        """Get a result by redemption code."""
        if not self.is_connected:
            return None

        try:
            result = (
                self.client.table(self.TABLE_RESULTS)
                .select("*, lottery_campaigns(name), lottery_participants(customer_email, customer_name)")
                .eq("redemption_code", redemption_code)
                .execute()
            )

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get result by code: {e}")
            return None

    def redeem_prize(self, redemption_code: str, redeemed_by: Optional[str] = None) -> Optional[Dict]:
        """
        Mark a prize as redeemed.

        Args:
            redemption_code: The redemption code
            redeemed_by: Admin/staff who processed the redemption

        Returns:
            Updated result data or None if invalid/already redeemed
        """
        if not self.is_connected:
            return None

        try:
            # Check if code exists and is not redeemed
            existing = self.get_result_by_code(redemption_code)

            if not existing:
                logger.warning(f"Redemption code not found: {redemption_code}")
                return None

            if existing.get("is_redeemed"):
                logger.warning(f"Code already redeemed: {redemption_code}")
                return None

            if not existing.get("is_winner"):
                logger.warning(f"Code is not a winning ticket: {redemption_code}")
                return None

            # Mark as redeemed
            update_data = {
                "is_redeemed": True,
                "redeemed_at": datetime.now().isoformat(),
                "redeemed_by": redeemed_by,
                "updated_at": datetime.now().isoformat(),
            }

            result = (
                self.client.table(self.TABLE_RESULTS)
                .update(update_data)
                .eq("redemption_code", redemption_code)
                .execute()
            )

            if result.data:
                logger.success(f"Redeemed code: {redemption_code}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to redeem prize: {e}")
            return None

    def get_results_by_campaign(
        self,
        campaign_id: str,
        winners_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get all results for a campaign."""
        if not self.is_connected:
            return []

        try:
            query = (
                self.client.table(self.TABLE_RESULTS)
                .select("*, lottery_participants(customer_email, customer_name, shopline_customer_id)")
                .eq("campaign_id", campaign_id)
            )

            if winners_only:
                query = query.eq("is_winner", True)

            result = query.order("scratched_at", desc=True).range(offset, offset + limit - 1).execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get results by campaign: {e}")
            return []

    def get_results_by_participant(self, participant_id: str) -> List[Dict]:
        """Get all results for a participant."""
        if not self.is_connected:
            return []

        try:
            result = (
                self.client.table(self.TABLE_RESULTS)
                .select("*")
                .eq("participant_id", participant_id)
                .order("scratched_at", desc=True)
                .execute()
            )
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get results by participant: {e}")
            return []

    # =========================================================================
    # Statistics (統計)
    # =========================================================================

    def get_campaign_stats(self, campaign_id: str) -> Dict:
        """
        Get statistics for a campaign.

        Returns:
            {
                "total_participants": 總參與人數,
                "total_attempts": 總刮獎次數,
                "total_winners": 中獎人數,
                "total_redeemed": 已兌換數,
                "prizes_stats": [
                    {"name": "獎品名", "total": 100, "remaining": 50, "won": 50, "redeemed": 30}
                ]
            }
        """
        if not self.is_connected:
            return {}

        try:
            # Get participant count
            participants_result = (
                self.client.table(self.TABLE_PARTICIPANTS)
                .select("id", count="exact")
                .eq("campaign_id", campaign_id)
                .execute()
            )
            total_participants = participants_result.count or 0

            # Get results stats
            results_result = (
                self.client.table(self.TABLE_RESULTS)
                .select("*")
                .eq("campaign_id", campaign_id)
                .execute()
            )
            results = results_result.data or []

            total_attempts = len(results)
            total_winners = len([r for r in results if r.get("is_winner")])
            total_redeemed = len([r for r in results if r.get("is_redeemed")])

            # Get prizes stats
            prizes = self.get_prizes(campaign_id)
            prizes_stats = []

            for prize in prizes:
                prize_id = prize["id"]
                won = len([r for r in results if r.get("prize_id") == prize_id])
                redeemed = len([r for r in results if r.get("prize_id") == prize_id and r.get("is_redeemed")])

                prizes_stats.append({
                    "id": prize_id,
                    "name": prize["name"],
                    "total": prize["total_quantity"],
                    "remaining": prize["remaining_quantity"],
                    "won": won,
                    "redeemed": redeemed,
                })

            return {
                "total_participants": total_participants,
                "total_attempts": total_attempts,
                "total_winners": total_winners,
                "total_redeemed": total_redeemed,
                "prizes_stats": prizes_stats,
            }

        except Exception as e:
            logger.error(f"Failed to get campaign stats: {e}")
            return {}

    # =========================================================================
    # Admin Logs (管理日誌)
    # =========================================================================

    def log_admin_action(
        self,
        action: str,
        campaign_id: Optional[str] = None,
        details: Optional[Dict] = None,
        performed_by: Optional[str] = None
    ) -> bool:
        """Log an admin action."""
        if not self.is_connected:
            return False

        try:
            log_data = {
                "action": action,
                "campaign_id": campaign_id,
                "details": details,
                "performed_by": performed_by,
            }

            self.client.table(self.TABLE_ADMIN_LOGS).insert(log_data).execute()
            return True

        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
            return False
