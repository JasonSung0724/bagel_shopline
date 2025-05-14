import pandas as pd
from src.tcat_scraping import Tcat
import io

class ExcelReader:
    def __init__(self, excel_data):
        excel_file = io.BytesIO(excel_data)
        self.data = pd.read_excel(excel_file)

    def get_data(self):
        return self.data
