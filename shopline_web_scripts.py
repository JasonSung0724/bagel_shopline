from selenium.webdriver.common.by import By
import time
import os
import subprocess
from src.shopline_pom import ShopLinePOM
from src.shopline import ShopLine
import json
from loguru import logger

# -Control an opened Chrome browser-
# Enter the command in cmd terminal.
# Step 1:
# cd C:\Program Files\Google\Chrome\Application
# Step 2:
# chrome.exe --remote-debugging-port=9527 --user-data-dir="C:\selenium\NewProfile"


def open_debug_chrome():
    original_path = os.getcwd()
    try:
        chrome_path = r"C:\Program Files\Google\Chrome\Application"
        os.chdir(chrome_path)
        command = r'chrome.exe --remote-debugging-port=9527 --user-data-dir="C:\selenium\NewProfile"'
        process = subprocess.Popen(command, shell=True)
        print(f"Chrome launched with PID: {process.pid}")
        time.sleep(3)
        process.terminate()
        print(f"Terminated Chrome process with PID: {process.pid}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        os.chdir(original_path)
        print(f"Returned to original path: {original_path}")


class ShopLineScripts(ShopLinePOM):

    def __init__(self):
        super().__init__()
        self.shop = ShopLine()

    def get_pending_orders(self):
        return self.shop.get_outstanding_shopline_delivery_order3()

    def open_order_detail_view(self, order_id):
        # order_id = self.order_detail()
        url = f"https://admin.shoplineapp.com/admin/carbs/orders/{order_id}"
        self.open_url(url)

    def edit_delivery_info_scripts(self):
        postal_code = self.fetch_info("postal_code")
        region = self.fetch_info("region")
        address = self.fetch_info("address")
        delivery_date_time = self.fetch_delivery_date_time()
        city = self.mapping_city(postal_code)
        self.click(self.edit_delivery_detail_button)
        self.click(self.delivery_method_dropdown)
        self.click(self.custom_delivery_method_option)
        self.wait_for_element(self.modal_content)
        self.select_phone_code()
        self.select_city(city)
        self.select_region(postal_code=postal_code, region=region)
        self.input(loc=self.input_recipient_address, value=address)
        self.select_delivery_time(delivery_date_time)
        self.save_delivery_info()
        self.wait_for_element(loc=self.update_success_notify, wait_type="visibility")
        return True

    def run(self):
        remain_count = 1
        try:
            while remain_count > 0:
                search = self.get_pending_orders()
                orders = search["items"]
                remain_count = search["pagination"]["total_count"]
                
                logger.info(f"剩餘訂單數: {remain_count}")
                for order in orders:
                    order_id = order["id"]
                    logger.info(f"Processing Order ID: {order_id}")
                    self.open_order_detail_view(order_id)
                    if self.edit_delivery_info_scripts():
                        self.shop.update_order_tag(order_id=order_id)
                        self.shop.update_delivery_status(order_id=order_id, status="collected", notify=False)
                        self.shop.update_order_status(order_id=order_id, status="completed", notify=False)
        except Exception as e:
            logger.error(f"Error: {e}")
            self.open_url("https://admin.shoplineapp.com/admin/carbs/overview/pos")
            self.run()


if __name__ == "__main__":
    # open_debug_chrome()
    scripts = ShopLineScripts()
    orders = scripts.run()
    # order_id = "67d1ae0a26cb81000a090262"
    # scripts.shop.update_order_tag(order_id=order_id)
    # scripts.shop.update_delivery_status(order_id=order_id, status="collected", notify=False)
    # scripts.shop.update_order_status(order_id=order_id, status="completed", notify=False)
