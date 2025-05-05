import requests
from bs4 import BeautifulSoup
from loguru import logger
import json
import datetime

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

    @classmethod
    def order_detail_find_collected_time(cls, order_id):
        url = f"https://www.t-cat.com.tw/Inquire/TraceDetail.aspx?BillID={order_id}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        template = soup.find("div", id="template")
        if template:
            span = soup.find("span", string=config["c2c"]["status_name"]["collected"])
            if span:
                tr = span.find_parent("tr")
                td = tr.find_all("td")
                update_time = td[1].text.strip()
                try:
                    dt = datetime.datetime.strptime(update_time, "%Y/%m/%d %H:%M")
                    formatted_date = dt.strftime("%Y%m%d")
                    return formatted_date
                except ValueError as e:
                    logger.error(f"時間格式轉換錯誤: {e}")
                    return ""
        return ""


print(Tcat.order_detail_find_collected_time("907093166271"))
