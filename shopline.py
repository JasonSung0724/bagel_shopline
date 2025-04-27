import requests
import json

class ShopLine:

    def __init__(self):
        with open("config.json", "r") as f:
            config = json.load(f)
        self.token = config["ShopLineToken"]
        print(self.token)
        self.header = {
            "authorization": f"Bearer {self.token}",
            "accept": "application/json",
        }

    def get_order(self, order_id):
        url = f"https://open.shopline.io/v1/orders/{order_id}"
        response = requests.get(url=url, headers=self.header)
        print(response)
        return 
    
shop = ShopLine()
shop.get_order("20250421163858010")