import json

class ConfigManager:

    def __init__(self):
        self.config = json.load(open("config/field_config.json", "r", encoding="utf-8"))
        self.flowdite_backup_sheet = self.config["flowtide"]["backup_sheet_name_format"]
        self.flowtide_mark_field = self.config["flowtide"]["mark_field"]
        self.flowtide_c2c_mark = self.config["flowtide"]["c2c_mark"]
        self.flowtide_tcat_number = self.config["flowtide"]["tcat_number"]
        self.flowtide_order_number = self.config["flowtide"]["customer_order_number"]
        self.c2c_shipping_date = self.config["c2c"]["shipping_date"]
        self.c2c_current_status = self.config["c2c"]["current_status"]
        self.c2c_order_number = self.config["c2c"]["customer_order_number"]
        self.c2c_delivery_number = self.config["c2c"]["delivery_number"]
        self.c2c_status_success = self.config["c2c"]["status_name"]["success"]
        self.c2c_status_no_data = self.config["c2c"]["status_name"]["no_data"]
        self.c2c_status_collected = self.config["c2c"]["status_name"]["collected"]
