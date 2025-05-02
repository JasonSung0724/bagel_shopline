import pandas as pd
from tcat_scraping import Tcat


class ExcelReader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = pd.read_excel(file_path)

    def get_data(self):
        return self.data
