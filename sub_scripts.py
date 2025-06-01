from c2c_main import ShopLineOrderScripts, MessageSender

if __name__ == "__main__":
    msg = MessageSender()
    shopline_order_scripts = ShopLineOrderScripts(msg_instance=msg)
    shopline_order_scripts.run_update_outstanding_shopline_order()