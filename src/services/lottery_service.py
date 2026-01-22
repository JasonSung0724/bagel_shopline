"""
Lottery (Scratch Card) Service - Business Logic Layer
"""

import random
from typing import Optional, Dict, List, Any
from datetime import datetime
from loguru import logger

from src.repositories.lottery_repository import LotteryRepository


class LotteryService:
    """
    Business logic for lottery (scratch card) operations.

    Features:
        - Campaign management (CRUD)
        - Prize management with probability-based drawing
        - Participant tracking (Shopline customer integration)
        - Redemption code verification
        - Statistics and reporting
    """

    def __init__(self):
        self.repo = LotteryRepository()

    # =========================================================================
    # Campaign Management (活動管理)
    # =========================================================================

    def create_campaign(self, data: Dict[str, Any]) -> Dict:
        """
        Create a new lottery campaign.

        Args:
            data: Campaign data

        Returns:
            {"success": True, "campaign": {...}} or {"success": False, "error": "..."}
        """
        try:
            # Validate required fields
            required = ["name", "start_date", "end_date"]
            for field in required:
                if not data.get(field):
                    return {"success": False, "error": f"Missing required field: {field}"}

            # Validate dates
            start = datetime.fromisoformat(data["start_date"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(data["end_date"].replace("Z", "+00:00"))

            if end <= start:
                return {"success": False, "error": "End date must be after start date"}

            campaign = self.repo.create_campaign(data)

            if campaign:
                self.repo.log_admin_action(
                    action="create_campaign",
                    campaign_id=campaign["id"],
                    details={"name": data.get("name")},
                )
                return {"success": True, "campaign": campaign}

            return {"success": False, "error": "Failed to create campaign"}

        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            return {"success": False, "error": str(e)}

    def get_campaign(self, campaign_id: str) -> Optional[Dict]:
        """Get a campaign by ID with prizes."""
        return self.repo.get_campaign(campaign_id)

    def list_campaigns(self, status: Optional[str] = None) -> List[Dict]:
        """List all campaigns."""
        return self.repo.list_campaigns(status)

    def update_campaign(self, campaign_id: str, data: Dict[str, Any]) -> Dict:
        """Update a campaign."""
        try:
            # Validate status transition
            if "status" in data:
                current = self.repo.get_campaign(campaign_id)
                if not current:
                    return {"success": False, "error": "Campaign not found"}

                valid_transitions = {
                    "draft": ["active", "ended"],
                    "active": ["paused", "ended"],
                    "paused": ["active", "ended"],
                    "ended": [],  # Cannot change from ended
                }

                current_status = current.get("status", "draft")
                new_status = data["status"]

                if new_status != current_status and new_status not in valid_transitions.get(current_status, []):
                    return {
                        "success": False,
                        "error": f"Invalid status transition: {current_status} -> {new_status}"
                    }

            campaign = self.repo.update_campaign(campaign_id, data)

            if campaign:
                self.repo.log_admin_action(
                    action="update_campaign",
                    campaign_id=campaign_id,
                    details=data,
                )
                return {"success": True, "campaign": campaign}

            return {"success": False, "error": "Failed to update campaign"}

        except Exception as e:
            logger.error(f"Error updating campaign: {e}")
            return {"success": False, "error": str(e)}

    def delete_campaign(self, campaign_id: str) -> Dict:
        """Delete a campaign."""
        try:
            campaign = self.repo.get_campaign(campaign_id)
            if not campaign:
                return {"success": False, "error": "Campaign not found"}

            # Only allow deleting draft campaigns
            if campaign.get("status") != "draft":
                return {"success": False, "error": "Can only delete draft campaigns"}

            if self.repo.delete_campaign(campaign_id):
                self.repo.log_admin_action(
                    action="delete_campaign",
                    details={"campaign_id": campaign_id, "name": campaign.get("name")},
                )
                return {"success": True}

            return {"success": False, "error": "Failed to delete campaign"}

        except Exception as e:
            logger.error(f"Error deleting campaign: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Prize Management (獎品管理)
    # =========================================================================

    def add_prize(self, campaign_id: str, data: Dict[str, Any]) -> Dict:
        """
        Add a prize to a campaign.

        Args:
            campaign_id: Campaign ID
            data: Prize data

        Returns:
            {"success": True, "prize": {...}} or {"success": False, "error": "..."}
        """
        try:
            # Validate campaign exists
            campaign = self.repo.get_campaign(campaign_id)
            if not campaign:
                return {"success": False, "error": "Campaign not found"}

            # Validate required fields
            required = ["name", "total_quantity", "probability"]
            for field in required:
                if field not in data:
                    return {"success": False, "error": f"Missing required field: {field}"}

            # Validate probability
            probability = float(data.get("probability", 0))
            if probability < 0 or probability > 1:
                return {"success": False, "error": "Probability must be between 0 and 1"}

            # Check total probability doesn't exceed 1
            existing_prizes = self.repo.get_prizes(campaign_id)
            total_probability = sum(p.get("probability", 0) for p in existing_prizes)

            if total_probability + probability > 1:
                return {
                    "success": False,
                    "error": f"Total probability would exceed 1.0 (current: {total_probability}, adding: {probability})"
                }

            prize = self.repo.add_prize(campaign_id, data)

            if prize:
                self.repo.log_admin_action(
                    action="add_prize",
                    campaign_id=campaign_id,
                    details={"prize_name": data.get("name"), "quantity": data.get("total_quantity")},
                )
                return {"success": True, "prize": prize}

            return {"success": False, "error": "Failed to add prize"}

        except Exception as e:
            logger.error(f"Error adding prize: {e}")
            return {"success": False, "error": str(e)}

    def update_prize(self, prize_id: str, data: Dict[str, Any]) -> Dict:
        """Update a prize."""
        try:
            prize = self.repo.update_prize(prize_id, data)

            if prize:
                self.repo.log_admin_action(
                    action="update_prize",
                    campaign_id=prize.get("campaign_id"),
                    details={"prize_id": prize_id, **data},
                )
                return {"success": True, "prize": prize}

            return {"success": False, "error": "Failed to update prize"}

        except Exception as e:
            logger.error(f"Error updating prize: {e}")
            return {"success": False, "error": str(e)}

    def delete_prize(self, prize_id: str) -> Dict:
        """Delete a prize."""
        try:
            if self.repo.delete_prize(prize_id):
                self.repo.log_admin_action(
                    action="delete_prize",
                    details={"prize_id": prize_id},
                )
                return {"success": True}

            return {"success": False, "error": "Failed to delete prize"}

        except Exception as e:
            logger.error(f"Error deleting prize: {e}")
            return {"success": False, "error": str(e)}

    def get_prizes(self, campaign_id: str) -> List[Dict]:
        """Get all prizes for a campaign."""
        return self.repo.get_prizes(campaign_id)

    # =========================================================================
    # Scratch Card Logic (刮刮樂核心邏輯)
    # =========================================================================

    def scratch(
        self,
        campaign_id: str,
        shopline_customer_id: str,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """
        Process a scratch card attempt.

        Args:
            campaign_id: Campaign ID
            shopline_customer_id: Shopline customer ID
            customer_email: Customer email (optional)
            customer_name: Customer name (optional)
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)

        Returns:
            {
                "success": True,
                "result": {
                    "is_winner": True/False,
                    "prize": {...} or None,
                    "redemption_code": "XXXX-XXXX-XXXX" or None,
                    "message": "恭喜中獎!" or "很可惜，未中獎"
                }
            }
            or
            {"success": False, "error": "...", "error_code": "..."}
        """
        try:
            # 1. Validate campaign is active
            campaign = self.repo.get_active_campaign(campaign_id)
            if not campaign:
                # Check if campaign exists but is not active
                any_campaign = self.repo.get_campaign(campaign_id)
                if not any_campaign:
                    return {"success": False, "error": "活動不存在", "error_code": "CAMPAIGN_NOT_FOUND"}

                status = any_campaign.get("status", "draft")
                if status == "draft":
                    return {"success": False, "error": "活動尚未開始", "error_code": "CAMPAIGN_NOT_STARTED"}
                elif status == "ended":
                    return {"success": False, "error": "活動已結束", "error_code": "CAMPAIGN_ENDED"}
                elif status == "paused":
                    return {"success": False, "error": "活動暫停中", "error_code": "CAMPAIGN_PAUSED"}
                else:
                    return {"success": False, "error": "活動目前無法參與", "error_code": "CAMPAIGN_INACTIVE"}

            # 2. Check login requirement
            if campaign.get("require_login") and not shopline_customer_id:
                return {"success": False, "error": "請先登入會員", "error_code": "LOGIN_REQUIRED"}

            # 3. Get or create participant
            participant = self.repo.get_or_create_participant(
                campaign_id=campaign_id,
                shopline_customer_id=shopline_customer_id,
                customer_email=customer_email,
                customer_name=customer_name
            )

            if not participant:
                return {"success": False, "error": "無法建立參與記錄", "error_code": "PARTICIPANT_ERROR"}

            # 4. Check attempt limit
            max_attempts = campaign.get("max_attempts_per_user", 1)
            current_attempts = participant.get("attempt_count", 0)

            if current_attempts >= max_attempts:
                return {
                    "success": False,
                    "error": f"您已使用完所有刮獎機會 ({max_attempts}次)",
                    "error_code": "MAX_ATTEMPTS_REACHED"
                }

            # 5. Draw prize
            prizes = campaign.get("prizes", [])
            won_prize = self._draw_prize(prizes)

            # 6. If won, decrement prize quantity
            if won_prize:
                if not self.repo.decrement_prize_quantity(won_prize["id"]):
                    # Prize ran out between check and decrement, treat as no win
                    won_prize = None

            # 7. Increment attempt count
            self.repo.increment_attempt_count(participant["id"])

            # 8. Create result record
            result = self.repo.create_result(
                campaign_id=campaign_id,
                participant_id=participant["id"],
                prize_id=won_prize["id"] if won_prize else None,
                prize_name=won_prize["name"] if won_prize else None,
                prize_type=won_prize["prize_type"] if won_prize else None,
                is_winner=won_prize is not None,
                ip_address=ip_address,
                user_agent=user_agent
            )

            if not result:
                return {"success": False, "error": "無法記錄刮獎結果", "error_code": "RESULT_ERROR"}

            # 9. Build response
            if won_prize:
                return {
                    "success": True,
                    "result": {
                        "is_winner": True,
                        "prize": {
                            "name": won_prize["name"],
                            "description": won_prize.get("description"),
                            "prize_type": won_prize["prize_type"],
                            "prize_value": won_prize.get("prize_value"),
                            "image_url": won_prize.get("image_url"),
                        },
                        "redemption_code": result.get("redemption_code"),
                        "message": f"恭喜您獲得 {won_prize['name']}！",
                        "attempts_remaining": max_attempts - current_attempts - 1,
                    }
                }
            else:
                return {
                    "success": True,
                    "result": {
                        "is_winner": False,
                        "prize": None,
                        "redemption_code": None,
                        "message": "很可惜，這次沒有中獎，下次再接再厲！",
                        "attempts_remaining": max_attempts - current_attempts - 1,
                    }
                }

        except Exception as e:
            logger.error(f"Error processing scratch: {e}")
            return {"success": False, "error": "系統錯誤，請稍後再試", "error_code": "SYSTEM_ERROR"}

    def _draw_prize(self, prizes: List[Dict]) -> Optional[Dict]:
        """
        Draw a prize based on probabilities.

        Args:
            prizes: List of active prizes with remaining quantity > 0

        Returns:
            Winning prize or None (no win)
        """
        # Filter available prizes (active and has remaining quantity)
        available_prizes = [
            p for p in prizes
            if p.get("is_active") and p.get("remaining_quantity", 0) > 0 and p.get("prize_type") != "none"
        ]

        if not available_prizes:
            return None

        # Random draw
        rand = random.random()
        cumulative = 0.0

        for prize in available_prizes:
            probability = float(prize.get("probability", 0))
            cumulative += probability

            if rand < cumulative:
                return prize

        # No win (probability didn't hit any prize)
        return None

    def check_eligibility(
        self,
        campaign_id: str,
        shopline_customer_id: Optional[str] = None
    ) -> Dict:
        """
        Check if a user is eligible to participate in a campaign.

        Args:
            campaign_id: Campaign ID
            shopline_customer_id: Shopline customer ID (optional)

        Returns:
            {
                "eligible": True/False,
                "reason": "..." (if not eligible),
                "campaign": {...},
                "attempts_used": 0,
                "attempts_remaining": 1
            }
        """
        try:
            # Check campaign exists and is active
            campaign = self.repo.get_active_campaign(campaign_id)

            if not campaign:
                any_campaign = self.repo.get_campaign(campaign_id)
                if not any_campaign:
                    return {"eligible": False, "reason": "活動不存在"}

                status = any_campaign.get("status", "draft")
                if status == "draft":
                    return {"eligible": False, "reason": "活動尚未開始", "campaign": any_campaign}
                elif status == "ended":
                    return {"eligible": False, "reason": "活動已結束", "campaign": any_campaign}
                elif status == "paused":
                    return {"eligible": False, "reason": "活動暫停中", "campaign": any_campaign}
                else:
                    return {"eligible": False, "reason": "活動目前無法參與", "campaign": any_campaign}

            # Check login requirement
            if campaign.get("require_login") and not shopline_customer_id:
                return {
                    "eligible": False,
                    "reason": "請先登入會員",
                    "campaign": self._sanitize_campaign_for_public(campaign),
                    "attempts_used": 0,
                    "attempts_remaining": 0
                }

            # Check attempt limit
            max_attempts = campaign.get("max_attempts_per_user", 1)
            attempts_used = 0

            if shopline_customer_id:
                attempts_used = self.repo.get_participant_attempts(campaign_id, shopline_customer_id)

            attempts_remaining = max(0, max_attempts - attempts_used)

            if attempts_remaining == 0:
                return {
                    "eligible": False,
                    "reason": f"您已使用完所有刮獎機會 ({max_attempts}次)",
                    "campaign": self._sanitize_campaign_for_public(campaign),
                    "attempts_used": attempts_used,
                    "attempts_remaining": 0
                }

            return {
                "eligible": True,
                "campaign": self._sanitize_campaign_for_public(campaign),
                "attempts_used": attempts_used,
                "attempts_remaining": attempts_remaining
            }

        except Exception as e:
            logger.error(f"Error checking eligibility: {e}")
            return {"eligible": False, "reason": "系統錯誤"}

    def _sanitize_campaign_for_public(self, campaign: Dict) -> Dict:
        """Remove sensitive fields from campaign for public API."""
        safe_fields = [
            "id", "name", "description", "start_date", "end_date",
            "status", "max_attempts_per_user", "require_login"
        ]

        sanitized = {k: campaign.get(k) for k in safe_fields}

        # Sanitize prizes (don't expose remaining quantities or probabilities)
        if "prizes" in campaign:
            sanitized["prizes"] = [
                {
                    "name": p.get("name"),
                    "description": p.get("description"),
                    "prize_type": p.get("prize_type"),
                    "image_url": p.get("image_url"),
                }
                for p in campaign.get("prizes", [])
                if p.get("is_active") and p.get("prize_type") != "none"
            ]

        return sanitized

    # =========================================================================
    # Redemption (兌獎)
    # =========================================================================

    def verify_redemption_code(self, redemption_code: str) -> Dict:
        """
        Verify a redemption code.

        Args:
            redemption_code: The redemption code to verify

        Returns:
            {
                "valid": True/False,
                "redeemed": True/False,
                "result": {...} (if valid)
            }
        """
        try:
            result = self.repo.get_result_by_code(redemption_code)

            if not result:
                return {"valid": False, "error": "兌換碼無效"}

            if not result.get("is_winner"):
                return {"valid": False, "error": "此碼非中獎碼"}

            return {
                "valid": True,
                "redeemed": result.get("is_redeemed", False),
                "result": {
                    "prize_name": result.get("prize_name"),
                    "prize_type": result.get("prize_type"),
                    "scratched_at": result.get("scratched_at"),
                    "redeemed_at": result.get("redeemed_at"),
                    "customer_name": result.get("lottery_participants", {}).get("customer_name"),
                    "customer_email": result.get("lottery_participants", {}).get("customer_email"),
                    "campaign_name": result.get("lottery_campaigns", {}).get("name"),
                }
            }

        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            return {"valid": False, "error": "驗證失敗"}

    def redeem_prize(self, redemption_code: str, redeemed_by: Optional[str] = None) -> Dict:
        """
        Redeem a prize.

        Args:
            redemption_code: The redemption code
            redeemed_by: Admin/staff processing the redemption

        Returns:
            {"success": True, "result": {...}} or {"success": False, "error": "..."}
        """
        try:
            # First verify
            verification = self.verify_redemption_code(redemption_code)

            if not verification.get("valid"):
                return {"success": False, "error": verification.get("error", "兌換碼無效")}

            if verification.get("redeemed"):
                return {"success": False, "error": "此獎品已兌換過"}

            # Redeem
            result = self.repo.redeem_prize(redemption_code, redeemed_by)

            if result:
                self.repo.log_admin_action(
                    action="redeem_prize",
                    campaign_id=result.get("campaign_id"),
                    details={
                        "redemption_code": redemption_code,
                        "prize_name": result.get("prize_name"),
                    },
                    performed_by=redeemed_by
                )
                return {"success": True, "result": result}

            return {"success": False, "error": "兌換失敗"}

        except Exception as e:
            logger.error(f"Error redeeming prize: {e}")
            return {"success": False, "error": "兌換失敗"}

    # =========================================================================
    # Statistics (統計)
    # =========================================================================

    def get_campaign_stats(self, campaign_id: str) -> Dict:
        """Get comprehensive statistics for a campaign."""
        return self.repo.get_campaign_stats(campaign_id)

    def get_results(
        self,
        campaign_id: str,
        winners_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get results for a campaign."""
        return self.repo.get_results_by_campaign(campaign_id, winners_only, limit, offset)

    def get_user_results(self, campaign_id: str, shopline_customer_id: str) -> List[Dict]:
        """Get a specific user's results for a campaign."""
        participant = self.repo.get_or_create_participant(campaign_id, shopline_customer_id)
        if not participant:
            return []
        return self.repo.get_results_by_participant(participant["id"])
