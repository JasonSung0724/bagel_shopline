import pygsheets
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
import datetime
from loguru import logger


class C2CGoogleSheet:

    def __init__(self):
        self.sht = None
        self.scopes = ["https://www.googleapis.com/auth/drive"]
        self.service_account_file = r"config/mybagel-458109-30f35338f350.json"
        self.credentials = service_account.Credentials.from_service_account_file(self.service_account_file, scopes=self.scopes)
        self.service = build("drive", "v3", credentials=self.credentials)
        self.gc = pygsheets.authorize(service_file=self.service_account_file)

    def get_all_sheets(self):
        results = self.service.files().list(q="mimeType='application/vnd.google-apps.spreadsheet'", fields="files(id, name)").execute()
        files = results.get("files", [])
        if not files:
            logger.warning("No files found.")
        else:
            file_dict = {}
            for file in files:
                logger.info(f"Name: {file['name']}, ID: {file['id']}")
                file_dict[file["name"]] = file["id"]
            return file_dict

    def open_sheet(self, name=None, url=None):
        if name:
            self.sht = self.gc.open(name)
        elif url:
            self.sht = self.gc.open_by_url(url)
        else:
            raise ValueError("Either 'name' or 'url' must be provided.")

    def get_worksheet(self, sheet_index):
        return self.sht[sheet_index]

    def get_worksheet_all_values(self, worksheet):
        return worksheet.get_all_values()

    def find_c2c_track_sheet(self, sheets):
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        previous_date = (datetime.datetime.now() - datetime.timedelta(days=31)).strftime("%Y%m%d")
        current_date_found = False
        previous_date_found = False
        target_sheets = []
        for sheet_name in list(sheets.keys()):
            if not current_date_found and not previous_date_found:
                if sheet_name.startswith(previous_date + "快電商"):
                    target_sheets.append(sheet_name)
                    previous_date_found = True
                elif sheet_name.startswith(current_date + "快電商"):
                    target_sheets.append(sheet_name)
                    current_date_found = True
            else:
                break
        return target_sheets

    def update_worksheet(self, worksheet, df):
        try:
            current_values = worksheet.get_all_values()
            if not current_values:
                raise ValueError("工作表為空")
            current_headers = current_values[0]
            df = df[current_headers]
            for col_idx, col_name in enumerate(current_headers):
                for row_idx in range(len(df)):
                    current_value = current_values[row_idx + 1][col_idx] if row_idx + 1 < len(current_values) else ""
                    new_value = str(df.iloc[row_idx, col_idx]) if not pd.isna(df.iloc[row_idx, col_idx]) else ""
                    if current_value != new_value:
                        cell = worksheet.cell((row_idx + 2, col_idx + 1))
                        cell.value = new_value
            logger.success("成功更新 Google Sheet")
        except Exception as e:
            logger.error(f"更新 Google Sheet 時發生錯誤: {str(e)}")
            raise
