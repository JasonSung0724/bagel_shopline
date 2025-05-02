import requests
import json
from loguru import logger


class ShopLine:

    def __init__(self, order_number):
        with open("config.json", "r") as f:
            config = json.load(f)
        self.token = config["ShopLineToken"]
        self.header = {
            "Authorization": f"Bearer {self.token}",
            "accept": "application/json",
        }
        self.domain = "https://open.shopline.io"
        self.order_number = order_number
        self.order_detail = {}
        self.order_id = ""
        self.setup()

    def setup(self):
        self.order_detail = self.query_order(self.order_number)
        self.order_id = self.order_detail["items"][0]["id"]

    def response_handler(self, response):
        if response.status_code == 200:
            try:
                response_data = response.json()
                logger.debug(response_data)
                return response_data
            except json.JSONDecodeError:
                logger.error("JSON 解碼錯誤")
        elif response.status_code == 401:
            logger.error("Token 錯誤")
        else:
            logger.error(f"{response.status_code} : {response.text}")

    def get_token_info(self):
        url = f"{self.domain}/v1/token/info"
        response = requests.get(url=url, headers=self.header)
        return self.response_handler(response)

    def get_order(self):
        url = f"{self.domain}/v1/orders/:{self.order_id}"
        response = requests.get(url=url, headers=self.header)
        if response.status_code == 410:
            logger.error(f"{self.order_id} 此 Order 封存")
        elif response.status_code == 404:
            logger.error(f"{self.order_id} 此 Order 不存在")
        else:
            return self.response_handler(response)

    def update_delivery_status(self, status, notify):
        # pending, shipping, shipped, arrived, collected, returned, returning
        url = f"{self.domain}/v1/orders/{self.order_id}/order_delivery_status"
        payload = {"id": self.order_id, "status": status, "mail_notify": notify}
        response = requests.put(url=url, headers=self.header, data=payload)
        return self.response_handler(response)

    def update_order_status(self, status):
        # pending, confirmed, completed, cancelled
        url = f"{self.domain}/v1/orders/{self.order_id}/status"
        payload = {"id": self.order_id, "mail_notify": False, "status": status}
        response = requests.patch(url=url, headers=self.header, data=payload)
        return self.response_handler(response)

    def update_order(self):
        url = f"{self.domain}/v1/orders/{self.order_id}/status"
        payload = {"mail_notify": False, "status": "completed"}
        response = requests.patch(url=url, headers=self.header, data=payload)
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
                    value = ",".join(value)
                query_params.append(f"{key}={value}")
        query_string = "&".join(query_params)
        full_url = f"{url}?{query_string}"
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


shop = ShopLine("20250425025210474")
with open("result.json", "w") as f:
    json.dump(shop.order_detail, f, indent=4, ensure_ascii=False)
