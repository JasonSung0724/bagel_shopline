from c2c_main import fetch_email_by_date, delivery_excel_handle, GoogleSheetHandle, ShopLineOrderScripts, MessageSender, ConfigManager
import datetime

if __name__ == "__main__":
    CONFIG = ConfigManager()
    msg = MessageSender()
    date = datetime.datetime.now() - datetime.timedelta(days=1)
    result = fetch_email_by_date(msg, CONFIG.flowtide_sender_email, date)
    c2c_order_status = delivery_excel_handle(result, msg, platform="c2c")
    sheet_handel = GoogleSheetHandle(c2c_order_status)
    sheet_handel.process_data_scripts(msg)

    shopline_order_scripts = ShopLineOrderScripts(mail_result=result, msg_instance=msg)
    shopline_order_scripts.run_scripts()

    msg.line_push_message()
