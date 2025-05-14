import json
import os

class ConfigManager:

    def __init__(self):
        # Get the directory where config.py is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load field config
        field_config_path = os.path.join(current_dir, "field_config.json")
        with open(field_config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
            
        # Initialize configuration fields
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
        self.flowtide_sender_email = self.config["flowtide"]["sender_email"]
        self.flowtide_sheet_name_format = self.config["flowtide"]["sheet_name_format"]

class SettingsManager:

    def __init__(self):
        # Get the directory where config.py is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load main config
        config_path = os.path.join(current_dir, "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            self.settings = json.load(f)
            
        # Initialize settings fields
        self.line_access_token = self.settings["line_access_token"]
        self.group_id = self.settings["group_id"]
        self.bot_gmail = self.settings["GmailAddress"]
        self.bot_app_password = self.settings["APPPassword"]
        
        # Service account file path
        self.service_account_file = os.path.join(current_dir, "mybagel-458109-30f35338f350.json")

