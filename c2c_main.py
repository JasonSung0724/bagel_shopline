import pandas as pd
import datetime
import json
from gmail_fetch import GmailConnect
from excel_hadle import ExcelReader
from google_drive import C2CGoogleSheet
from tcat_scraping import Tcat

config = json.load(open("config/field_config.json", "r", encoding="utf-8"))


def fetch_today_email():
    today = datetime.datetime.now().strftime("%d-%b-%Y")
    script = GmailConnect(email="bagelshop2025@gmail.com", password="ciyc avqe zlsu bfcg")
    messages = script.search_emails(today)
    for message in messages:
        data = script.parse_email(message)
        if data:
            print(data)


def delivery_excel_handle():
    today = datetime.datetime.now().strftime("%Y%m%d")
    order = ExcelReader(f"order_excel/A442出貨單資料{today}*.xls")
    data_frame = order.get_data()
    processed = []
    order_status = {}
    for index, row in data_frame.iterrows():
        tcat_number = row[config["flowtide"]["tcat_number"]]
        order_number = row[config["flowtide"]["customer_order_number"]]
        if not pd.isna(tcat_number):
            tcat_number = str(int(tcat_number))
            if tcat_number not in processed:
                processed.append(tcat_number)
                status = Tcat.order_status(tcat_number)
                order_status[order_number] = {"status": status, "tcat_number": tcat_number}
    return order_status


def google_sheet_handle(update_orders):
    drive = C2CGoogleSheet()
    sheets = drive.get_all_sheets()
    target_sheets = drive.find_c2c_track_sheet(sheets)
    for target_sheet in target_sheets:
        drive.open_sheet(target_sheet)
        worksheet = drive.get_worksheet(0)
        all_values = drive.get_worksheet_all_values(worksheet)
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        update_count = 0
        try:
            for index, row in df.iterrows():
                customer_order_number = row[config["c2c"]["customer_order_number"]]
                if not pd.isna(row[config["c2c"]["customer_order_number"]]) and row[config["c2c"]["customer_order_number"]].strip():
                    tcat_number = row[config["c2c"]["delivery_number"]] if not pd.isna(row[config["c2c"]["delivery_number"]]) else None
                    if not tcat_number and row[config["c2c"]["current_status"]] == config["c2c"]["status_name"]["success"]:
                        continue
                    elif tcat_number and row[config["c2c"]["current_status"]] != config["c2c"]["status_name"]["success"]:
                        update_status = Tcat.order_status(tcat_number)
                        df.loc[index, config["c2c"]["current_status"]] = update_status
                        if row[config["c2c"]["current_status"]] != update_status:
                            print(f"只更新該單號的狀態 {row[config['c2c']['customer_order_number']]}")
                            update_count += 1
                    elif not tcat_number:
                        if row[config["c2c"]["customer_order_number"]] in update_orders:
                            print(f"更新單號及狀態 {row[config['c2c']['customer_order_number']]}")
                            df.loc[index, config["c2c"]["delivery_number"]] = update_orders[row[config["c2c"]["customer_order_number"]]]["tcat_number"]
                            status = update_orders[row[config["c2c"]["customer_order_number"]]]["status"]
                            df.loc[index, config["c2c"]["current_status"]] = status if status else config["c2c"]["status_name"]["no_data"]
                            update_count += 1
                        else:
                            print(f"逢泰excel中未更新此單號 : {row[config['c2c']['customer_order_number']]}")
        except Exception as e:
            print(f"在Google Sheet處理 {customer_order_number} 訂單時發生錯誤: {e}")
            raise

        print(f"總共更新了 {update_count} 筆資料")
        if update_count > 0:
            print("正在更新 Google Sheet...")
            drive.update_worksheet(worksheet, df)
        else:
            print("沒有需要更新的資料")


if __name__ == "__main__":
    fetch_today_email()
    order_status = delivery_excel_handle()
    google_sheet_handle(order_status)
