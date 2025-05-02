import pygsheets
from googleapiclient.discovery import build
from google.oauth2 import service_account


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
            print("No files found.")
        else:
            file_dict = {}
            for file in files:
                print(f"Name: {file['name']}, ID: {file['id']}")
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
