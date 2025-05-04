import requests
from bs4 import BeautifulSoup
from loguru import logger
import json

config = json.load(open("config/field_config.json", "r", encoding="utf-8"))


class Tcat:

    @classmethod
    def order_status(cls, order_id):
        url = f"https://www.t-cat.com.tw/Inquire/Trace.aspx?method=result&billID={order_id}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        list_box = soup.find("ul", class_="order-list")
        if list_box:
            status_element = list_box.find_all("div", class_="col-2")
            order_status = status_element[1]
            if order_status:
                status_text = order_status.text.strip()
                logger.debug(f"訂單 {order_id} 狀態 : {status_text}")
                return status_text
        else:
            logger.warning(f"訂單 {order_id} 狀態 : 暫無資料")
            return config["c2c"]["status_name"]["no_data"]