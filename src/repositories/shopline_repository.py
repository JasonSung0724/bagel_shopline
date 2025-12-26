"""
ShopLine API repository for order operations.
"""
import json
import requests
from typing import Optional, Dict, List, Any
from loguru import logger

from src.config.config import SettingsManager


class ShopLineRepository:
    """
    Repository for ShopLine API operations.
    """

    # Delivery method IDs
    CUSTOM_DELIVERY_METHOD = "68281a2f3451b7000c4f5d7b"
    SHOPLINE_TCAT_DELIVERY_METHOD = "653a404c30939a000e82c000"

    def __init__(self, token: Optional[str] = None):
        """
        Initialize ShopLine repository.

        Args:
            token: ShopLine API token (uses config if not provided)
        """
        settings = SettingsManager()
        self.token = token or settings.shopline_token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        self.base_url = "https://open.shopline.io"

    def _handle_response(self, response: requests.Response) -> Optional[Dict]:
        """
        Handle API response.

        Args:
            response: Response object

        Returns:
            Parsed JSON or None on error
        """
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.error("JSON 解碼錯誤")
                return None

        elif response.status_code == 401:
            logger.error(f"Token 錯誤或 IP 未授權: {response.text}")
            return None

        elif response.status_code == 404:
            logger.warning(f"資源不存在: {response.text}")
            return None

        elif response.status_code == 410:
            logger.warning(f"資源已封存: {response.text}")
            return None

        else:
            logger.error(f"API 錯誤 {response.status_code}: {response.text}")
            return None

    def get_order(self, order_id: str) -> Optional[Dict]:
        """
        Get order by ID.

        Args:
            order_id: ShopLine order ID

        Returns:
            Order data or None
        """
        url = f"{self.base_url}/v1/orders/{order_id}"
        response = requests.get(url=url, headers=self.headers)
        return self._handle_response(response)

    def search_orders(self, conditions: Dict[str, Any]) -> Optional[Dict]:
        """
        Search orders with conditions.

        Args:
            conditions: Search conditions dict

        Returns:
            Search results or None
        """
        url = f"{self.base_url}/v1/orders/search"

        # Build query string
        query_params = []
        for key, value in conditions.items():
            if value is not None:
                if isinstance(value, list):
                    for item in value:
                        query_params.append(f"{key}={item}")
                else:
                    query_params.append(f"{key}={value}")

        query_string = "&".join(query_params)
        full_url = f"{url}?{query_string}"

        logger.debug(f"Search URL: {full_url}")
        response = requests.get(url=full_url, headers=self.headers)
        return self._handle_response(response)

    def query_order_by_number(self, order_number: str) -> Optional[Dict]:
        """
        Query order by order number.

        Args:
            order_number: Order number (without #)

        Returns:
            Order data or None
        """
        # Remove split suffix if present
        if "-" in order_number:
            order_number = order_number.split("-")[0]

        result = self.search_orders({"query": order_number})
        if result and result.get("items"):
            return result["items"][0]
        return None

    def get_outstanding_orders(
        self,
        page: int = 1,
        per_page: int = 200
    ) -> Optional[Dict]:
        """
        Get outstanding orders with custom delivery method.

        Args:
            page: Page number
            per_page: Items per page

        Returns:
            Search results with pagination
        """
        conditions = {
            "per_page": per_page,
            "page": page,
            "delivery_option_id": self.CUSTOM_DELIVERY_METHOD,
            "status": "confirmed",
            "delivery_statuses[]": ["pending", "shipping", "shipped", "returning"],
        }
        return self.search_orders(conditions)

    def get_all_outstanding_orders(self) -> List[Dict]:
        """
        Get all outstanding orders (handles pagination).

        Returns:
            List of all outstanding orders
        """
        all_orders = []
        page = 1
        total_count = None

        while True:
            result = self.get_outstanding_orders(page=page)

            if not result or "pagination" not in result:
                logger.error(f"第 {page} 頁 API 響應無效")
                break

            if page == 1:
                total_count = result["pagination"]["total_count"]
                logger.info(f"待處理訂單總數: {total_count}")

            items = result.get("items", [])
            if items:
                all_orders.extend(items)
                logger.debug(f"第 {page} 頁獲取 {len(items)} 筆訂單")

            if len(all_orders) >= total_count:
                break

            page += 1

        logger.info(f"總共獲取 {len(all_orders)} 筆待處理訂單")
        return all_orders

    def update_delivery_status(
        self,
        order_id: str,
        status: str,
        notify: bool = False
    ) -> bool:
        """
        Update order delivery status.

        Args:
            order_id: ShopLine order ID
            status: New status (pending, shipping, shipped, arrived, collected, returned, returning)
            notify: Whether to send email notification

        Returns:
            True if successful
        """
        url = f"{self.base_url}/v1/orders/{order_id}/order_delivery_status"
        payload = {
            "id": order_id,
            "status": status,
            "mail_notify": notify
        }

        response = requests.patch(url=url, headers=self.headers, data=json.dumps(payload))
        result = self._handle_response(response)
        return result is not None

    def update_order_status(
        self,
        order_id: str,
        status: str,
        notify: bool = False
    ) -> bool:
        """
        Update order status.

        Args:
            order_id: ShopLine order ID
            status: New status (pending, confirmed, completed, cancelled)
            notify: Whether to send email notification

        Returns:
            True if successful
        """
        url = f"{self.base_url}/v1/orders/{order_id}/status"
        payload = {
            "id": order_id,
            "status": status,
            "mail_notify": notify
        }

        response = requests.patch(url=url, headers=self.headers, data=json.dumps(payload))
        result = self._handle_response(response)
        return result is not None

    def update_tracking_info(
        self,
        order_id: str,
        tracking_number: str,
        tracking_url: str,
        provider_name: str = "黑貓宅急便"
    ) -> bool:
        """
        Update order tracking information.

        Args:
            order_id: ShopLine order ID
            tracking_number: Tracking number
            tracking_url: Tracking URL
            provider_name: Delivery provider name

        Returns:
            True if successful
        """
        url = f"{self.base_url}/v1/orders/{order_id}"
        payload = {
            "tracking_number": tracking_number,
            "tracking_url": tracking_url,
            "delivery_provider_name": {
                "zh-hant": provider_name,
            },
        }

        response = requests.patch(url=url, headers=self.headers, data=json.dumps(payload))
        result = self._handle_response(response)
        return result is not None

    def is_custom_delivery(self, order: Dict) -> bool:
        """
        Check if order uses custom delivery method.

        Args:
            order: Order data dict

        Returns:
            True if custom delivery method
        """
        delivery_option_id = order.get("order_delivery", {}).get("delivery_option_id")
        return delivery_option_id == self.CUSTOM_DELIVERY_METHOD

    def get_tracking_number(self, order: Dict) -> Optional[str]:
        """
        Get tracking number from order.

        Args:
            order: Order data dict

        Returns:
            Tracking number or None
        """
        return order.get("delivery_data", {}).get("tracking_number")

    def get_delivery_status(self, order: Dict) -> Optional[str]:
        """
        Get delivery status from order.

        Args:
            order: Order data dict

        Returns:
            Delivery status string
        """
        return order.get("order_delivery", {}).get("status")
