from selenium.webdriver.common.by import By
import time
import os
import subprocess
from src.shopline_pom import ShopLinePOM
from src.shopline import ShopLine

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
        return self.shop.get_outstanding_shopline_delivery_order()["items"]

    def open_order_detail_view(self, order_id):
        # order_id = self.order_detail()
        url = f"https://admin.shoplineapp.com/admin/carbs/orders/{order_id}"
        self.open_url(url)

    def edit_delivery_info_scripts(self):
        postal_code = self.fetch_info("postal_code")
        address = self.fetch_info("address")
        delivery_date_time = self.fetch_delivery_date_time()
        city = self.mapping_city(postal_code)
        self.click(self.edit_delivery_detail_button)
        self.click(self.delivery_method_dropdown)
        self.click(self.custom_delivery_method_option)
        self.wait_for_element(self.modal_content)
        self.select_city(city)
        self.select_region(postal_code)
        self.input(loc=self.input_recipient_address, value=address)
        if delivery_date_time:
            self.select_delivery_time(delivery_date_time)
        self.save_delivery_info()
        self.wait_for_element(loc=self.update_success_notify, wait_type="visibility")

    def run(self):
        # orders = self.get_pending_orders()
        orders = [{"id": "68281a7883f5d800116176fc"}]
        for order in orders:
            order_id = order["id"]
            self.open_order_detail_view(order_id)
            self.edit_delivery_info_scripts()
            self.shop.update_delivery_status(order_id=order_id, status="collected")
            self.shop.update_order_status(order_id=order_id, status="completed")


if __name__ == "__main__":
    # open_debug_chrome()
    scripts = ShopLineScripts()
    scripts.run()
