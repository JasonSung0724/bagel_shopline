import pandas as pd
import datetime

from gmail_fetch import GmailConnect
from excel_hadle import ExcelReader
from google_drive import C2CGoogleSheet
from tcat_scraping import Tcat

# today = datetime.datetime.now().strftime("%d-%b-%Y")
# script = GmailConnect(email="bagelshop2025@gmail.com", password="ciyc avqe zlsu bfcg")
# messages = script.search_emails(today)
# for message in messages:
#     data = script.parse_email(message)
#     if data:
#         print(data)


def delivery_excel_handle():
    order = ExcelReader("order_excel/A442出貨單資料20250426_250425200051.xls")
    data_frame = order.get_data()
    processed = []
    order_status = {}
    for index, row in data_frame.iterrows():
        tcat_number = row["查貨號碼"]
        order_number = row["訂單號碼"].split("#")[1] if "#" in row["訂單號碼"] else row["訂單號碼"]
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
    drive.open_sheet(list(sheets.keys())[0])
    worksheet = drive.get_worksheet(0)
    all_values = drive.get_worksheet_all_values(worksheet)
    for row in all_values[1:]:
        if any(cell.strip() for cell in row):
            print("處理資料:", row)


if __name__ == "__main__":
    order_status = delivery_excel_handle()
    print(order_status)
    google_sheet_handle(order_status)
