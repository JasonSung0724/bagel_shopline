import requests
import json
from loguru import logger
from src.config.config import ConfigManager, SettingsManager
import os


class ShopLine:

    def __init__(self, order_number=None):
        self.settings = SettingsManager()
        self.token = self.settings.shopline_token
        self.header = {
            "Authorization": f"Bearer {self.token}",
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        self.domain = "https://open.shopline.io"
        self.order_number = order_number
        self.order_detail = {}
        self.order_id = ""
        self.custome_delivery_method = "68281a2f3451b7000c4f5d7b"
        self.shopline_tcat_delivery_method = "653a404c30939a000e82c000"
        self.setup()

    def setup(self):
        try:
            if "-" in self.order_number:
                self.order_number = self.order_number.split("-")[0]
            if self.order_number:
                self.order_detail = self.query_order(self.order_number)["items"][0]
                self.order_id = self.order_detail["id"]
            else:
                return None
        except (TypeError, IndexError) as e:
            logger.error(f"Order {self.order_number} 不存在")
            return None

    def get_public_ip(self):
        try:
            response = requests.get("https://api.ipify.org?format=json")
            return response.json()["ip"]
        except Exception as e:
            logger.error(f"獲取 IP 地址時發生錯誤: {e}")
            return "無法獲取 IP 地址"

    def response_handler(self, response):
        if response.status_code == 200:
            try:
                response_data = response.json()
                logger.debug("Request Succeed")
                return response_data
            except json.JSONDecodeError:
                logger.error("JSON 解碼錯誤")
        elif response.status_code == 401:
            current_ip = self.get_public_ip()
            logger.error(f"Response: {response.text}")
            logger.error(f"Token 錯誤 - 當前 IP: {current_ip}")
            return None
        else:
            logger.error(f"{response.status_code} : {response.text}")
            return None

    def get_token_info(self):
        url = f"{self.domain}/v1/token/info"
        response = requests.get(url=url, headers=self.header)
        return self.response_handler(response)

    def get_order(self, order_id=None):
        if not order_id:
            order_id = self.order_id
        url = f"{self.domain}/v1/orders/{order_id}"
        response = requests.get(url=url, headers=self.header)
        if response.status_code == 410:
            logger.error(f"{self.order_id} 此 Order 封存")
        elif response.status_code == 404:
            logger.error(f"{self.order_id} 此 Order 不存在")
        else:
            return self.response_handler(response)

    def update_delivery_status(self, status, order_id=None, notify=False):
        # pending, shipping, shipped, arrived, collected, returned, returning
        if not order_id:
            order_id = self.order_id
        url = f"{self.domain}/v1/orders/{order_id}/order_delivery_status"
        payload = {"id": order_id, "status": status, "mail_notify": notify}
        response = requests.patch(url=url, headers=self.header, data=json.dumps(payload))
        return self.response_handler(response)

    def update_order_status(self, status, order_id=None, notify=False):
        # pending, confirmed, completed, cancelled
        if not order_id:
            order_id = self.order_id
        url = f"{self.domain}/v1/orders/{order_id}/status"
        payload = {"id": order_id, "mail_notify": notify, "status": status}
        response = requests.patch(url=url, headers=self.header, data=json.dumps(payload))
        return self.response_handler(response)

    def update_order_tracking_info(self, tracking_number, tracking_url):
        url = f"{self.domain}/v1/orders/{self.order_id}"

        payload = {
            "tracking_number": tracking_number,
            "tracking_url": tracking_url,
            "delivery_provider_name": {
                "zh-hant": "黑貓宅急便",
            },
        }
        response = requests.patch(url=url, headers=self.header, data=json.dumps(payload))
        return self.response_handler(response)

    def search_order(self, specific_conditions: dict):
        """
        ::param specific_conditions: dict
        specific_conditions = {
            "previous_id": "",
            "per_page":"",
            "page":"",
            "statuses":[],
            "delivery_option_type":"",
            "delivery_statuses":[],
            "created_after":DateTime,
            "created_before":DateTime,
        }
        """
        url = f"{self.domain}/v1/orders/search"
        query_params = []
        for key, value in specific_conditions.items():
            if value:
                if isinstance(value, list):
                    for option in value:
                        query_params.append(f"{key}={option}")
                else:
                    query_params.append(f"{key}={value}")
        query_string = "&".join(query_params)
        full_url = f"{url}?{query_string}"
        logger.info(f"Full Search URL: {full_url}")
        response = requests.get(url=full_url, headers=self.header)
        return self.response_handler(response)

    def get_order_delivery(self):
        url = f"{self.domain}/v1/order_deliveries/{self.order_id}"
        response = requests.get(url=url, headers=self.header)
        return self.response_handler(response)

    def query_order(self, query):
        return self.search_order({"query": query})

    def update_delivery_options(self):
        url = f"{self.domain}/v1/delivery_options/{self.order_id}/stores_info"

    def get_outstanding_orders(self, page=None):
        search_params = {
            "per_page": 200,
            "delivery_option_id": self.custome_delivery_method,
            "status": "confirmed",
            "delivery_statuses[]": ["pending", "shipping", "shipped", "returning"],
        }
        if page:
            search_params["page"] = page
        logger.info(f"Search Params: {search_params}")
        return self.search_order(search_params)

    def get_outstanding_shopline_delivery_order(self):
        search_params = {
            "per_page": 10,
            "delivery_option_id": self.shopline_tcat_delivery_method,
            "delivery_statuse": "pending",
            "payment_status": "completed",
            "created_after": "2024-12-01 00:00:00",
            "created_before": "2025-05-01 00:00:00",
        }
        return self.search_order(search_params)

    def get_outstanding_shopline_delivery_order2(self):
        search_params = {
            "per_page": 10,
            "delivery_option_id": self.shopline_tcat_delivery_method,
            "delivery_statuse": "pending",
            "status": "cancelled",
            "payment_statues[]": ["failed", "expired"],
            "created_after": "2024-12-01 00:00:00",
            "created_before": "2025-05-01 00:00:00",
        }
        return self.search_order(search_params)

    def get_outstanding_shopline_delivery_order3(self):
        search_params = {
            "per_page": 10,
            "delivery_option_id": self.shopline_tcat_delivery_method,
            "delivery_statuse": "pending",
            "payment_status": "completed",
            "created_after": "2025-05-01 00:00:00",
            "created_before": "2025-05-21 00:00:00",
        }
        return self.search_order(search_params)

    def check_order_delivery_option(self):
        if self.order_detail:
            order_detail = self.order_detail
        else:
            order_detail = self.get_order()

        if order_detail["order_delivery"]["delivery_option_id"] == self.custome_delivery_method:
            return order_detail
        return None

    def update_order_tag(self, order_id):
        url = f"{self.domain}/v1/orders/{order_id}/tags"
        payload = {"tags": ["Edited Delivery Method Automation"]}
        response = requests.put(url=url, headers=self.header, data=json.dumps(payload))
        return self.response_handler(response)
