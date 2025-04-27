import pandas as pd
from tcat_scraping import Tcat

class ExcelReader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = pd.read_excel(file_path)
    
    def get_data(self):
        return self.data
    
order = ExcelReader("order_excel/A442出貨單資料20250426_250425200051.xls")
data_frame = order.get_data()
for index, row in data_frame.iterrows():
    tcat_number = row['查貨號碼']
    if not pd.isna(tcat_number):
        Tcat.order_status(int(tcat_number))
