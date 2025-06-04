import pandas as pd
import datetime
import json
from src.gmail_fetch import GmailConnect
from src.excel_hadle import ExcelReader
from src.google_drive import C2CGoogleSheet
from src.config.config import ConfigManager, SettingsManager
from src.tcat_scraping import Tcat
from loguru import logger
from src.shopline import ShopLine
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.messaging import TextMessage, PushMessageRequest

CONFIG = ConfigManager()
SETTINGS = SettingsManager()


class MessageSender:

    def __init__(self):
        self.settings = SettingsManager()
        self.line_access_token = SETTINGS.line_access_token
        self.group_id = SETTINGS.group_id
        self.message = None

    def line_push_message(self):
        configuration = Configuration(access_token=self.line_access_token)
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            try:
                push_message_request = PushMessageRequest(to=self.group_id, messages=[TextMessage(text=self.message)])
                response = line_bot_api.push_message(push_message_request)
                logger.success(f"訊息已成功發送: {response}")
                return True
            except Exception as e:
                logger.warning(f"發送訊息時發生錯誤: {e}")
                return False

    def add_message(self, message):
        self.message = self.message + "\n" + str(message) if self.message else str(message)

    def clear_message(self):
        self.message = None


def fetch_email_by_date(msg_instance, target_sender_email):
    script = GmailConnect(email=SETTINGS.bot_gmail, password=SETTINGS.bot_app_password)
    result = script.get_attachments(target_sender_email)
    has_flowtide_excel = "今天有收到逢泰Excel\n" if result else "今天(沒有)收到逢泰Excel\n"
    msg_instance.add_message(has_flowtide_excel)
    return result


def delivery_excel_handle(excel_data, msg_instance, platform="c2c"):

    def _check_platform_order(row):
        if platform == "c2c":
            return row[CONFIG.flowtide_mark_field].startswith(CONFIG.flowtide_c2c_mark)
        elif platform == "shopline":
            return row[CONFIG.flowtide_order_number].startswith("#") and row[CONFIG.flowtide_delivery_company] == "TCAT"

    def _get_platform_order_number(row):
        if platform == "c2c":
            return row[CONFIG.flowtide_order_number]
        elif platform == "shopline":
            return row[CONFIG.flowtide_order_number].split("#")[1]

    try:
        processed = []
        order_status = {}
        order_count = 0
        for data in excel_data:
            _file = data["attachments"][0]["file"]
            order = ExcelReader(_file)
            data_frame = order.get_data()
            for index, row in data_frame.iterrows():
                if _check_platform_order(row):
                    order_count += 1
                    tcat_number = row[CONFIG.flowtide_tcat_number]
                    order_number = _get_platform_order_number(row)
                    if not pd.isna(tcat_number):
                        tcat_number = str(int(tcat_number))
                        if tcat_number not in processed:
                            processed.append(tcat_number)
                            status = Tcat.order_status(tcat_number)
                            order_status[order_number] = {"status": status, "tcat_number": tcat_number}
        if excel_data and not processed:
            logger.warning(f"逢泰Excel中沒有 {platform.upper()} 訂單")
            msg_instance.add_message(f"逢泰Excel中沒有 {platform.upper()} 訂單\n")
            return {}
        msg_instance.add_message(f"{platform.upper()}訂單-總計 {order_count} 筆\n黑貓託運單號共 {len(processed)} 筆")
        logger.info(f"Get Order Info\n{order_status}")
        return order_status
    except Exception as e:
        logger.error(e)
        return {}


class ShopLineOrderScripts:

    def __init__(self, msg_instance: MessageSender = None, mail_result: list = None):
        self.msg_instance = msg_instance
        self.tracking_info_updated_count = 0
        self.updated_delivery_status_count = 0
        self.mail_result = mail_result
        with open("src/config/status_map.json", "r", encoding="utf-8") as f:
            self.status_map = json.load(f)

    def _check_shopline_status(self, tcat_status: str):
        for key, value in self.status_map.items():
            if tcat_status in value:
                return key
        logger.warning(f"未找到 {tcat_status} 的對應狀態")
        return None

    def _update_order_status(self, order_id: str, order_number: str, tcat_status: str, original_delivery_status: str, shop: ShopLine):
        cur_delivery_status = self._check_shopline_status(tcat_status)
        if cur_delivery_status and original_delivery_status != cur_delivery_status:
            if shop.update_delivery_status(status=cur_delivery_status, order_id=order_id):
                self.updated_delivery_status_count += 1
                logger.info(f"更新 {order_number} 的訂單狀態 - ShopLine Id : {order_id}")
                if cur_delivery_status == "arrived":
                    shop.update_order_status(status="completed", order_id=order_id)
                if cur_delivery_status == "returned":
                    shop.update_order_status(status="cancelled", order_id=order_id)

    def shopline_update_order_scripts(self, update_orders: dict):
        for order_number, order_info in update_orders.items():
            shop = ShopLine(order_number)
            order_detail = shop.check_order_delivery_option()
            if order_detail:
                tcat_number = order_info["tcat_number"]
                tcat_status = order_info["status"]
                tcat_tracking_number = order_detail["delivery_data"]["tracking_number"]
                original_delivery_status = order_detail["order_delivery"]["status"]
                order_id = order_detail["id"]
                if not tcat_tracking_number:
                    shop.update_order_tracking_info(tracking_number=tcat_number, tracking_url=Tcat.get_query_url(tcat_number))
                    self.tracking_info_updated_count += 1
                self._update_order_status(
                    order_id=order_id, order_number=order_number, tcat_status=tcat_status, original_delivery_status=original_delivery_status, shop=shop
                )

    def _process_outstanding_order(self, orders, shop: ShopLine):
        for order in orders:
            tracking_number = order["delivery_data"]["tracking_number"]
            original_delivery_status = order["order_delivery"]["status"]
            order_id = order["id"]
            order_number = order["order_number"]
            if tracking_number:
                tcat_status = Tcat.order_status(tracking_number)
                self._update_order_status(
                    order_id=order_id, order_number=order_number, tcat_status=tcat_status, original_delivery_status=original_delivery_status, shop=shop
                )
            else:
                self.msg_instance.add_message(f"未找到 {order['order_number']} 的托運單號")
                logger.warning(f"未找到 {order['order_number']} 的托運單號")

    def update_outstanding_shopline_order(self):
        shop = ShopLine()
        process_page = 1
        all_orders = []
        total_pages = None
        while True:
            orders = shop.get_outstanding_orders(page=process_page)
            logger.info(f"待處理訂單總數: {orders['pagination']['total_count']}")
            process_page += 1
            if orders["items"]:
                all_orders.extend(orders["items"])
            if not total_pages:
                total_pages = orders["pagination"]["total_pages"]
            if process_page >= total_pages:
                break
        self._process_outstanding_order(all_orders, shop)

    def run_scripts(self):
        shopline_order_status = delivery_excel_handle(self.mail_result, self.msg_instance, platform="shopline")
        self.shopline_update_order_scripts(shopline_order_status)
        logger.success(f"更新追蹤資訊 {self.tracking_info_updated_count} 筆, 更新訂單狀態 {self.updated_delivery_status_count} 筆")
        self.msg_instance.add_message(f"ShopLine訂單-更新追蹤資訊 {self.tracking_info_updated_count} 筆, 更新訂單狀態 {self.updated_delivery_status_count} 筆")

    def run_update_outstanding_shopline_order(self):
        self.update_outstanding_shopline_order()
        logger.success(f"更新訂單狀態 {self.updated_delivery_status_count} 筆")


class GoogleSheetHandle:

    def __init__(self, update_orders):
        self.drive = C2CGoogleSheet()
        self.df = None
        self.sheets = self.drive.get_all_sheets()
        self.target_sheets = self.drive.find_c2c_track_sheet(self.sheets)
        self.current_time = datetime.datetime.now().strftime("%Y%m%d")
        self.update_orders = update_orders
        self.ship_date_field_name = CONFIG.c2c_shipping_date
        self.status_field_name = CONFIG.c2c_current_status
        self.platform_number_field_name = CONFIG.c2c_order_number
        self.delivery_number_field_name = CONFIG.c2c_delivery_number
        self.delivery_succeed = CONFIG.c2c_status_success
        self.no_data_str = CONFIG.c2c_status_no_data
        self.collected_str = CONFIG.c2c_status_collected

    def status_update(self, index, row, new_status):
        if new_status != self.no_data_str:
            if row[self.status_field_name] != new_status or pd.isna(row[self.ship_date_field_name]) or row[self.ship_date_field_name].strip() == "":
                if row[self.status_field_name] != new_status:
                    self.df.loc[index, self.status_field_name] = new_status
                if pd.isna(row[self.ship_date_field_name]) or row[self.ship_date_field_name].strip() == "":
                    collected_time = Tcat.order_detail_find_collected_time(row[self.delivery_number_field_name], current_state=new_status)
                    if collected_time:
                        self.df.loc[index, self.ship_date_field_name] = collected_time
                        logger.debug(f"更新 {row[self.delivery_number_field_name]} 的集貨時間 {collected_time}")
                        return True
                    else:
                        logger.warning(f"未找到 {row[self.delivery_number_field_name]} 的集貨時間")
                        return False
            return False
        else:
            if row[self.ship_date_field_name]:
                self.df.loc[index, self.ship_date_field_name] = ""
        return False

    def update_data(self, row, index, tcat_number):
        row_current_status = row[self.status_field_name]
        row_platform_number = row[self.platform_number_field_name]
        if tcat_number and row_current_status == self.delivery_succeed:
            return self.status_update(index=index, row=row, new_status=self.delivery_succeed)
        elif tcat_number and row_current_status != self.delivery_succeed:
            update_status = Tcat.order_status(tcat_number)
            is_update = self.status_update(index=index, row=row, new_status=update_status)
            return is_update
        elif not tcat_number:
            if row_platform_number in self.update_orders:
                logger.debug(f"更新單號及狀態 {row_platform_number}")
                self.df.loc[index, self.delivery_number_field_name] = self.update_orders[row_platform_number]["tcat_number"]
                status = self.update_orders[row_platform_number]["status"]
                return self.status_update(index=index, row=row, new_status=status)
            else:
                logger.debug(f"逢泰excel中未更新此單號 : {row_platform_number}")

    def check_result(self, target_sheet, backup_sheet):
        self.drive.open_sheet(target_sheet)
        target_worksheet = self.drive.get_worksheet(0)
        target_sheet_data = target_worksheet.get_all_values()
        self.drive.open_sheet(backup_sheet)
        backup_worksheet = self.drive.get_worksheet(0)
        backup_data = backup_worksheet.get_all_values()
        target_sheet_data_filtered = [row for row in target_sheet_data if any(cell.strip() if isinstance(cell, str) else cell for cell in row)]
        backup_data_filtered = [row for row in backup_data if any(cell.strip() if isinstance(cell, str) else cell for cell in row)]
        target_rows = len(target_sheet_data_filtered)
        backup_rows = len(backup_data_filtered)
        if target_rows == backup_rows:
            message = f"有效行數相同, 正式表{target_rows}行, 備份表{backup_rows}行"
            logger.info(message)
            return True, message
        else:
            message = f"有效行數不同, 正式表{target_rows}行，備份表{backup_rows}行"
            logger.info(message)
            return False, message

    def process_data_scripts(self, msg_instance):
        for target_sheet in self.target_sheets:
            msg_instance.add_message(f"處理 {target_sheet}\n")
            backup_sheet_name = CONFIG.flowdite_backup_sheet
            self.drive.open_sheet(backup_sheet_name)
            backup_worksheet = self.drive.get_worksheet(0)

            self.drive.open_sheet(target_sheet)
            original_worksheet = self.drive.get_worksheet(0)
            all_values = self.drive.get_worksheet_all_values(original_worksheet)
            backup_worksheet.update_values(crange=f"A1:{chr(64 + len(all_values[0]))}{len(all_values)}", values=all_values)

            header = all_values[0]
            header = [col for col in header if col != ""]
            header_columns_count = len(header)
            data = [row[:header_columns_count] for row in all_values[1:]]
            self.df = pd.DataFrame(data, columns=header)
            self.df = self.df.reset_index(drop=True)
            update_count = 0
            try:
                for index, row in self.df.iterrows():
                    customer_order_number = row[CONFIG.c2c_order_number]
                    if not pd.isna(customer_order_number) and customer_order_number.strip():
                        logger.debug(f"處理 {customer_order_number} 訂單")
                        tcat_number = row[self.delivery_number_field_name] if not pd.isna(row[self.delivery_number_field_name]) else None
                        update_count += 1 if self.update_data(row=row, index=index, tcat_number=tcat_number) else 0
            except Exception as e:
                logger.warning(f"在Google Sheet處理 {customer_order_number} 訂單時發生錯誤: {e}")
                msg_instance.add_message(f"在Google Sheet處理 {customer_order_number} 訂單時發生錯誤: {e}")
                msg_instance.line_push_message()
                msg_instance.clear_message()
                raise

            logger.success(f"總共更新了 {update_count} 筆資料")
            if update_count > 0:
                logger.debug("正在更新 Google Sheet...")
                if self.drive.update_worksheet(original_worksheet, self.df):
                    result, message = self.check_result(target_sheet, backup_sheet_name)
                    logger.success(f"成功更新了 {update_count} 筆資料\n{message}\n")
                    msg_instance.add_message(f"成功更新了 {update_count} 筆資料\n{message}")
            else:
                msg_instance.add_message(f"執行完畢 沒有更新任何資料")
                logger.debug("沒有需要更新的資料")


# if __name__ == "__main__":
#     msg = MessageSender()
#     shopline_order_scripts = ShopLineOrderScripts(msg_instance=msg)
#     shopline_order_scripts.run_update_outstanding_shopline_order()
