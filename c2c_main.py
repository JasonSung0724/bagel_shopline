import pandas as pd
import datetime
import json
from gmail_fetch import GmailConnect
from excel_hadle import ExcelReader
from google_drive import C2CGoogleSheet
from tcat_scraping import Tcat
from loguru import logger
import glob
import requests
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.messaging import TextMessage, PushMessageRequest

config = json.load(open("config/field_config.json", "r", encoding="utf-8"))


def line_push_message(message):
    with open("config/config.json", "r") as f:
        settings = json.load(f)
    token = settings["line_access_token"]
    configuration = Configuration(access_token=token)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            push_message_request = PushMessageRequest(
                to=settings["group_id"],
                messages=[TextMessage(text=message)]
            )
            response = line_bot_api.push_message(push_message_request)
            print(f"訊息已成功發送: {response}")
            return True
        except Exception as e:
            print(f"發送訊息時發生錯誤: {e}")
            return False


def fetch_email_by_date():
    today = datetime.datetime.now()
    previous_day = today - datetime.timedelta(days=1)
    date_format = "%d-%b-%Y"
    previous_day_str = previous_day.strftime(date_format)
    today_str = today.strftime(date_format)
    script = GmailConnect(email="bagelshop2025@gmail.com", password="ciyc avqe zlsu bfcg")
    messages = script.search_emails(today_str)
    result = []
    if messages:
        for message in messages:
            data = script.parse_email(message)
            if data and "attachments" in data and data["attachments"]:
                logger.info(data["attachments"][0]["filename"])
                result.append(data)
    return result


def delivery_excel_handle(excel_data):
    try:
        processed = []
        order_status = {}
        for data in excel_data:
            _file = data["attachments"][0]["file"]
            order = ExcelReader(_file)
            data_frame = order.get_data()
            for index, row in data_frame.iterrows():
                if row[config["flowtide"]["mark_field"]].startswith(config["flowtide"]["c2c_mark"]):
                    tcat_number = row[config["flowtide"]["tcat_number"]]
                    order_number = row[config["flowtide"]["customer_order_number"]]
                    if not pd.isna(tcat_number):
                        tcat_number = str(int(tcat_number))
                        if tcat_number not in processed:
                            processed.append(tcat_number)
                            status = Tcat.order_status(tcat_number)
                            order_status[order_number] = {"status": status, "tcat_number": tcat_number}
        return order_status
    except Exception as e:
        logger.error(e)
        return {}


class GoogleSheetHandle:

    def __init__(self, update_orders):
        self.drive = C2CGoogleSheet()
        self.df = None
        self.sheets = self.drive.get_all_sheets()
        self.target_sheets = self.drive.find_c2c_track_sheet(self.sheets)
        self.current_time = datetime.datetime.now().strftime("%Y%m%d")
        self.update_orders = update_orders
        self.ship_date_field_name = config["c2c"]["shipping_date"]
        self.status_field_name = config["c2c"]["current_status"]
        self.platform_number_field_name = config["c2c"]["customer_order_number"]
        self.delivery_number_field_name = config["c2c"]["delivery_number"]
        self.delivery_succeed = config["c2c"]["status_name"]["success"]
        self.no_data_str = config["c2c"]["status_name"]["no_data"]
        self.collected_str = config["c2c"]["status_name"]["collected"]

    def status_update(self, index, row, new_status):
        if new_status != self.no_data_str:
            if row[self.status_field_name] != new_status or pd.isna(row[self.ship_date_field_name]) or row[self.ship_date_field_name].strip() == "":
                if row[self.status_field_name] != new_status:
                    self.df.loc[index, self.status_field_name] = new_status
                if pd.isna(row[self.ship_date_field_name]) or row[self.ship_date_field_name].strip() == "":
                    collected_time = Tcat.order_detail_find_collected_time(row[self.delivery_number_field_name], current_state=new_status)
                    self.df.loc[index, self.ship_date_field_name] = collected_time
                    logger.debug(f"更新 {row[self.delivery_number_field_name]} 的集貨時間 {collected_time}")
                return True
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
                self.status_update(index=index, row=row, new_status=status)
                return True
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


    def process_data_scripts(self):
        notify = False
        for target_sheet in self.target_sheets:

            backup_sheet_name = config["flowtide"]["backup_sheet_name_format"]
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
                    customer_order_number = row[config["c2c"]["customer_order_number"]]
                    if not pd.isna(row[self.platform_number_field_name]) and row[self.platform_number_field_name].strip():
                        tcat_number = row[self.delivery_number_field_name] if not pd.isna(row[self.delivery_number_field_name]) else None
                        update_count += 1 if self.update_data(row=row, index=index, tcat_number=tcat_number) else 0
            except Exception as e:
                logger.warning(f"在Google Sheet處理 {customer_order_number} 訂單時發生錯誤: {e}")
                line_push_message(message=f"在Google Sheet處理 {customer_order_number} 訂單時發生錯誤: {e}")
                raise

            logger.success(f"總共更新了 {update_count} 筆資料")
            if update_count > 0:
                logger.debug("正在更新 Google Sheet...")
                if self.drive.update_worksheet(original_worksheet, self.df):
                    result, message = self.check_result(target_sheet, backup_sheet_name)
                    has_flowtide_excel = "今天有收到逢泰Excel" if self.update_orders else "今天(沒有)收到逢泰Excel"
                    logger.success(f"成功更新了 {update_count} 筆資料\n{message}\n{has_flowtide_excel}")
                    notify = line_push_message(message=f"{has_flowtide_excel}\n成功更新了 {update_count} 筆資料\n{message}")
            else:
                if not notify:
                    notify = line_push_message(message="執行完畢 沒有更新任何資料")
                logger.debug("沒有需要更新的資料")
    
    


if __name__ == "__main__":
    result = fetch_email_by_date()
    order_status = delivery_excel_handle(result)
    sheet_handel = GoogleSheetHandle(order_status)
    sheet_handel.process_data_scripts()