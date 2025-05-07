import pygsheets
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
import datetime
from loguru import logger
import json

config = json.load(open("config/field_config.json", "r", encoding="utf-8"))

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
        date_format = "%Y%m"
        target_sheets = []
        for sheet_name in list(sheets.keys()):
            if sheet_name.startswith(config["flowtide"]["sheet_name_format"]):
                target_sheets.append(sheet_name)
        logger.info(target_sheets)
        return target_sheets

    def update_worksheet(self, worksheet, df):
        try:
            headers = worksheet.get_row(1)
            headers = [col for col in headers if col != ""]
            if not headers:
                raise ValueError("工作表為空，無法獲取標題")

            protected_columns = 12
            unprotected_headers = headers[protected_columns:]
            if not unprotected_headers:
                raise ValueError("無可更新的未受保護欄位")
            df = df[unprotected_headers]
            data_without_headers = []
            for index, row in df.iterrows():
                if row[config["c2c"]["delivery_number"]] == "":
                    data_without_headers.append([""] * len(unprotected_headers))
                else:
                    data_without_headers.append(row.tolist())
            num_rows = len(data_without_headers) + 1
            num_cols = len(df.columns)  
            start_col_letter = chr(64 + protected_columns + 1)
            end_col_letter = chr(64 + protected_columns + num_cols)
            worksheet.update_values(
                crange=f"{start_col_letter}2:{end_col_letter}{num_rows}",
                values=data_without_headers
            )
            logger.success("成功更新 Google Sheet")
        except Exception as e:
            logger.error(f"更新 Google Sheet 時發生錯誤: {str(e)}")
            raise
