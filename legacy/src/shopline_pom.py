from .selenium_base.base import BaseHandler, Component
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import json
from selenium.webdriver.common.keys import Keys
from loguru import logger

class ShopLinePOM(BaseHandler):

    detail_field_value = Component(locator=(By.XPATH, "//span[@class='ng-binding']"))
    delivery_info = Component(locator=(By.XPATH, "//div[@addr='displayOrder.delivery_address']"))
    edit_delivery_detail_button = Component(locator=(By.XPATH, "//*[@data-e2e-id='order-detail-delivery-edit_button']"))
    delivery_method_dropdown = Component(locator=(By.XPATH, "//*[@data-e2e-id='order-detail-delivery-delivery_dropdown']"))
    custom_delivery_method_option = Component(locator=(By.XPATH, "//*[@label='低溫宅配（台灣本島）（下單後 2~5 個工作天內出貨）']"))
    modal_content = Component(locator=(By.XPATH, "//*[@class='modal-content']"))
    input_recipient_name = Component(locator=(By.XPATH, "//input[@name='deliveryChange.recipient_name']"))
    input_recipient_phone = Component(locator=(By.XPATH, "//input[@name='deliveryChange.recipient_phone']"))
    selector_recipient_city = Component(locator=(By.XPATH, "//*[@name='select_delivery_address.delivery_address.city']"))
    selector_recipient_region = Component(locator=(By.XPATH, "//select[@name='hidden_delivery_address.delivery_address.tw_address_2']"))
    input_recipient_address = Component(locator=(By.XPATH, "//input[@name='delivery_address.delivery_address.address_1']"))
    selector_delivery_time = Component(locator=(By.XPATH, "//select[@name='delivery_time']"))
    save_delivery_info_button = Component(locator=(By.XPATH, "//*[@ladda='orderDeliveryFormSubmitting' and @ng-click='save()']"))
    check_box_agree = Component(locator=(By.XPATH, "//*[@name='deliveryAgreeChange']"))
    delivery_date_time = Component(locator=(By.XPATH, "//div[@ng-show='order.delivery_data.time_slot_key']"))
    delivery_info_form = Component(locator=(By.XPATH, "//form[@id='orderDeliveryForm']"))
    update_success_notify = Component(locator=(By.XPATH, "//*[@class='ui-pnotify-title' and text()='訂單已更新']"))
    phone_code_dropdown = Component(locator=(By.XPATH, "(//*[@class='country-code'])[2]"))
    open_phone_code_dropdown = Component(locator=(By.XPATH, "(//*[@class='iti__arrow'])[2]"))
    tw_phone_code = Component(locator=(By.XPATH, "((//*[@aria-label='List of countries'])[2]//*[@data-country-code='tw'])[1]"))

    def fetch_delivery_info(self):
        return self.wait_for_element(self.delivery_info, wait_type="visibility").text

    def fetch_info(self, field, retry=3):
        delivery_info = self.fetch_delivery_info()
        if not delivery_info and retry > 0:
            self.time_sleep(0.5)
            return self.fetch_info(field, retry - 1)
        info_list = delivery_info.split("\n")
        if field == "postal_code":
            return info_list[1]
        elif field == "city":
            return info_list[2].split(" ")[0]
        elif field == "region":
            return info_list[2].split(" ")[1]
        elif field == "address":
            return info_list[3]

    def fetch_delivery_date_time(self):
        return self.find_elements(self.delivery_date_time, wait=False)[0].text

    def mapping_city(self, postal_code):
        with open("src/config/postal_code.json", "r", encoding="utf-8") as f:
            postal_code_dict = json.load(f)
        for city, region in postal_code_dict.items():
            for region, code in region.items():
                if code == postal_code:
                    return city
        return None

    def select_city(self, city):
        select_element = self.find_element(self.selector_recipient_city)
        select = Select(select_element)
        select.select_by_visible_text(city)
        self.wait_for_attribute_to_be_removed(self.selector_recipient_region, "disabled")
        self.time_sleep(0.5)

    def select_phone_code(self):
        phone_code_dropdown = self.find_elements(self.phone_code_dropdown, wait=False)
        if not phone_code_dropdown:
            self.click(self.open_phone_code_dropdown)
            self.click(self.wait_for_element(loc=self.tw_phone_code, wait_type="visibility"))
            return
        phone_code = phone_code_dropdown[0].text
        logger.info(f"Phone code: {phone_code}")

    def select_region(self, postal_code=None, region=None):
        select_element = self.find_element(self.selector_recipient_region)
        select = Select(select_element)
        for option in select.options:
            if region in option.text:
                select.select_by_visible_text(option.text)
                logger.info(f"Select region by region: {option.text}")
                return
        for option in select.options:
            if option.text.startswith(postal_code):
                select.select_by_visible_text(option.text)
                logger.info(f"Select region by postal_code: {option.text}")
                return

    def select_delivery_time(self, delivery_date_time):
        select_element = self.find_element(self.selector_delivery_time)
        select = Select(select_element)
        if " - " in delivery_date_time:
            delivery_date_time = delivery_date_time.replace(" - ", "~")
        if not delivery_date_time:
            delivery_date_time = "任何時段"
        select.select_by_visible_text(delivery_date_time)

    def save_delivery_info(self):
        self.click(self.check_box_agree)
        form = self.find_element(self.delivery_info_form)
        save = self.find_child_element(loc=form, child_loc=self.save_delivery_info_button)
        self.click(save)
