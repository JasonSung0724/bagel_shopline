import requests
from bs4 import BeautifulSoup
from loguru import logger
import datetime
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.config.config import ConfigManager

CONFIG = ConfigManager()


class Tcat:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
    }

    @classmethod
    def get_query_url(cls, order_id):
        return f"https://www.t-cat.com.tw/Inquire/Trace.aspx?method=result&billID={order_id}"

    @classmethod
    def _create_session(cls):
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    @classmethod
    def order_status(cls, order_id):
        url = cls.get_query_url(order_id)
        session = cls._create_session()
        try:
            response = session.get(url, timeout=10, headers=cls.headers)
            response.raise_for_status()
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
                return CONFIG.c2c_status_no_data
        except Exception as e:
            logger.error(f"查詢訂單 {order_id} 狀態時發生錯誤: {str(e)}")
            return CONFIG.c2c_status_no_data
        finally:
            session.close()

    @classmethod
    def current_state_update_time(cls, order_id):
        url = f"https://www.t-cat.com.tw/Inquire/Trace.aspx?method=result&billID={order_id}"
        session = cls._create_session()
        try:
            response = session.get(url, timeout=10, headers=cls.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            list_box = soup.find("ul", class_="order-list")
            if list_box:
                status_element = list_box.find_all("div", class_="col-2")
                update_time = status_element[2]
                if update_time:
                    update_time_text = update_time.text.strip()
                    try:
                        dt = datetime.datetime.strptime(update_time_text, "%Y/%m/%d %H:%M")
                        formatted_date = dt.strftime("%Y%m%d")
                        return formatted_date
                    except ValueError as e:
                        logger.error(f"時間格式轉換錯誤: {e}")
                        return ""
            logger.warning(f"無法爬蟲到該訂單的更新時間 {order_id}")
            return ""
        except Exception as e:
            logger.error(f"查詢訂單 {order_id} 更新時間時發生錯誤: {str(e)}")
            return ""
        finally:
            session.close()

    @classmethod
    def order_detail_find_collected_time(cls, order_id, retry=2, current_state=None):

        url = f"https://www.t-cat.com.tw/Inquire/TraceDetail.aspx?BillID={order_id}"
        session = cls._create_session()
        try:
            if CONFIG.c2c_status_collected == current_state:
                return cls.current_state_update_time(order_id)
            response = session.get(url, timeout=10, headers=cls.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            table = soup.find("table", id="resultTable")
            if table:
                table_data = table.find_all("tr")
                timeline = []

                def _parse_time(time: str):
                    date = time.split(" ")[0]
                    return date.replace("/", "")

                for block in table_data:
                    arrived = block.find("strong")
                    arrive_time = block.find_all("span", class_="bl12")
                    if arrived and arrive_time:
                        timeline.append({"status": arrived.text.strip(), "time": _parse_time(arrive_time[1].text.strip())})
                    else:
                        record = block.find_all("span", class_="bl12")
                        if record:
                            timeline.append({"status": record[0].text.strip(), "time": _parse_time(record[1].text.strip())})

                for s in timeline:
                    if s["status"] == CONFIG.c2c_status_collected:
                        return s["time"]
                return timeline[-1]["time"]

            logger.warning(f"無法爬蟲到該訂單的集貨時間 {order_id}")
            return ""
        except Exception as e:
            logger.error(f"查詢訂單 {order_id} 收件時間時發生錯誤: {str(e)}")
            if retry > 0:
                time.sleep(1)
                return cls.order_detail_find_collected_time(order_id, retry - 1)
            logger.error(f"查詢訂單 {order_id} 超時,錯誤次數太多")
            return ""
        finally:
            session.close()
