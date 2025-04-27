import requests
from bs4 import BeautifulSoup


class Tcat:

    @classmethod
    def order_status(cls, order_id):
        url = f"https://www.t-cat.com.tw/Inquire/Trace.aspx?method=result&billID={order_id}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        order_status = soup.find("strong")
        if order_status:
            status_text = order_status.text.strip()
            print(f"訂單 {order_id} 狀態 : {status_text}")
            return status_text
        else:
            print(f"訂單 {order_id} 狀態 : 暫無資料")
            return "Order not found"
