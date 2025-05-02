import pandas as pd
import datetime
import json
from gmail_fetch import GmailConnect
from excel_hadle import ExcelReader
from google_drive import C2CGoogleSheet
from tcat_scraping import Tcat

config = json.load(open("config/field_config.json", "r", encoding="utf-8"))

# today = datetime.datetime.now().strftime("%d-%b-%Y")
# script = GmailConnect(email="bagelshop2025@gmail.com", password="ciyc avqe zlsu bfcg")
# messages = script.search_emails(today)
# for message in messages:
#     data = script.parse_email(message)
#     if data:
#         print(data)


def delivery_excel_handle():
    order = ExcelReader("order_excel/A442出貨單資料20250502_250501200022.xls")
    data_frame = order.get_data()
    processed = []
    order_status = {}
    for index, row in data_frame.iterrows():
        tcat_number = row[config["flowtide"]["tcat_number"]]
        order_number = row[config["flowtide"]["customer_order_number"]]
        if not pd.isna(tcat_number):
            tcat_number = str(int(tcat_number))
            if tcat_number not in processed:
                processed.append(tcat_number)
                status = Tcat.order_status(tcat_number)
                order_status[order_number] = {"status": status, "tcat_number": tcat_number}
    return order_status


def google_sheet_handle(update_orders):
    drive = C2CGoogleSheet()
    sheets = drive.get_all_sheets()
    drive.open_sheet(list(sheets.keys())[0])
    worksheet = drive.get_worksheet(0)
    all_values = drive.get_worksheet_all_values(worksheet)

    df = pd.DataFrame(all_values[1:], columns=all_values[0])
    update_count = 0
    try:
        for index, row in df.iterrows():
            customer_order_number = row[config["c2c"]["customer_order_number"]]
            print(customer_order_number)
            if not pd.isna(row[config["c2c"]["customer_order_number"]]) and row[config["c2c"]["customer_order_number"]].strip():
                tcat_number = row[config["c2c"]["delivery_number"]] if not pd.isna(row[config["c2c"]["delivery_number"]]) else None
                if not tcat_number and row[config["c2c"]["current_status"]] == config["c2c"]["status_name"]["success"]:
                    continue
                elif tcat_number and row[config["c2c"]["current_status"]] != config["c2c"]["status_name"]["success"]:
                    print(f"只更新該單號的狀態 {row[config['c2c']['customer_order_number']]}")
                    update_status = Tcat.order_status(tcat_number)
                    df.loc[index, config["c2c"]["current_status"]] = update_status
                    update_count += 1
                elif not tcat_number:
                    if row[config["c2c"]["customer_order_number"]] in update_orders:
                        print(f"更新單號及狀態 {row[config['c2c']['customer_order_number']]}")
                        df.loc[index, config["c2c"]["delivery_number"]] = update_orders[row[config["c2c"]["customer_order_number"]]]["tcat_number"]
                        status = update_orders[row[config["c2c"]["customer_order_number"]]]["status"]
                        df.loc[index, config["c2c"]["current_status"]] = status if status else config["c2c"]["status_name"]["no_data"]
                        update_count += 1
                    else:
                        # print(f"逢泰excel中未更新此單號 : {row[config['c2c']['customer_order_number']]}")
                        pass
            else:
                break
    except Exception as e:
        print(f"在Google Sheet處理 {customer_order_number} 訂單時發生錯誤: {e}")
        raise

    print(f"總共更新了 {update_count} 筆資料")
    if update_count > 0:
        print("正在更新 Google Sheet...")
        drive.update_worksheet(worksheet, df)
    else:
        print("沒有需要更新的資料")


if __name__ == "__main__":
    # order_status = delivery_excel_handle()
    order_status = {
        17458128477408261: {"status": "順利送達", "tcat_number": "907093166271"},
        17458128865011867: {"status": "已出貨", "tcat_number": "907093166282"},
        17458129414972212: {"status": "", "tcat_number": "907093166293"},
        17458130809473590: {"status": None, "tcat_number": "907093166302"},
        17458130853263010: {"status": None, "tcat_number": "907093166313"},
        17458130869473185: {"status": None, "tcat_number": "907093166324"},
        17458131664959678: {"status": None, "tcat_number": "907093166335"},
        17458132238311947: {"status": None, "tcat_number": "907093166346"},
        17458134924894470: {"status": None, "tcat_number": "907093166350"},
        17458135914453552: {"status": None, "tcat_number": "907093166361"},
        17458136859897431: {"status": None, "tcat_number": "907093166372"},
        17458139419513588: {"status": None, "tcat_number": "907093166383"},
        17458140113673063: {"status": None, "tcat_number": "907093166394"},
        17458141361741040: {"status": None, "tcat_number": "907093166403"},
        17458141507168899: {"status": None, "tcat_number": "907093166414"},
        17458143480801725: {"status": None, "tcat_number": "907093166425"},
        17458145743816282: {"status": None, "tcat_number": "907093166436"},
        17458146027988995: {"status": None, "tcat_number": "907093166440"},
        17458147028739775: {"status": None, "tcat_number": "907093166451"},
        17458147803625059: {"status": None, "tcat_number": "907093166462"},
        17458149215806447: {"status": None, "tcat_number": "907093166473"},
        17458149672733769: {"status": None, "tcat_number": "907093166484"},
        17458152049286318: {"status": None, "tcat_number": "907093166495"},
        17458152432946706: {"status": None, "tcat_number": "907110309002"},
        17458157566701551: {"status": None, "tcat_number": "907110309013"},
        17458158295255636: {"status": None, "tcat_number": "907110309024"},
        17458160475024575: {"status": None, "tcat_number": "907110309035"},
        17458169127654938: {"status": None, "tcat_number": "907110309046"},
        17458169907306531: {"status": None, "tcat_number": "907110309050"},
        17458170855119698: {"status": None, "tcat_number": "907110309061"},
        17458172187219390: {"status": None, "tcat_number": "907110309072"},
        17458176722179083: {"status": None, "tcat_number": "907110309083"},
        17458183449343854: {"status": None, "tcat_number": "907110309094"},
        17458192003396671: {"status": None, "tcat_number": "907110309103"},
        17458195223002527: {"status": None, "tcat_number": "907110309114"},
        17458197964665640: {"status": None, "tcat_number": "907110309125"},
        17458205453497269: {"status": None, "tcat_number": "907110309136"},
        17458208786805971: {"status": None, "tcat_number": "907110309140"},
        17458210535188556: {"status": None, "tcat_number": "907110309151"},
        17458211717389795: {"status": None, "tcat_number": "907110309162"},
        17458216031932102: {"status": None, "tcat_number": "907110309173"},
        17458218595296111: {"status": None, "tcat_number": "907110309184"},
        17458220782926514: {"status": None, "tcat_number": "907110309195"},
        17458220889534947: {"status": None, "tcat_number": "907110309204"},
        17458224605795445: {"status": None, "tcat_number": "907110309215"},
        17458225800527607: {"status": None, "tcat_number": "907110309226"},
        17458226550184880: {"status": None, "tcat_number": "907110309230"},
        17458229256281367: {"status": None, "tcat_number": "907110309241"},
        17458229692097232: {"status": None, "tcat_number": "907110309252"},
        17458231004364829: {"status": None, "tcat_number": "907110309263"},
        17458232846163174: {"status": None, "tcat_number": "907110309274"},
        17458232888218100: {"status": None, "tcat_number": "907110309285"},
        17458233647683871: {"status": None, "tcat_number": "907110309296"},
        17458233784942570: {"status": None, "tcat_number": "907110309305"},
        17458233925387824: {"status": None, "tcat_number": "907110309316"},
        17458248515987633: {"status": None, "tcat_number": "907110309320"},
        17458251436731820: {"status": None, "tcat_number": "907110309331"},
        17458268907627059: {"status": None, "tcat_number": "907110309342"},
        17458270857495587: {"status": None, "tcat_number": "907110309353"},
        17458273894898085: {"status": None, "tcat_number": "907110309364"},
        17458287292221895: {"status": None, "tcat_number": "907110309375"},
        17458287533419244: {"status": None, "tcat_number": "907110309386"},
        17458287602665784: {"status": None, "tcat_number": "907110309390"},
        17458293907044024: {"status": None, "tcat_number": "907110309406"},
        17458299479778978: {"status": None, "tcat_number": "907110309410"},
        17458303667025195: {"status": None, "tcat_number": "907110309421"},
        17458311435288258: {"status": None, "tcat_number": "907110309432"},
        17458314740808461: {"status": None, "tcat_number": "907110309443"},
        17458316247796589: {"status": None, "tcat_number": "907110309454"},
        17458324730145087: {"status": None, "tcat_number": "907110309465"},
        17458328207158835: {"status": None, "tcat_number": "907110309476"},
        17458332709376577: {"status": None, "tcat_number": "907110309480"},
        17458333043252787: {"status": None, "tcat_number": "907110309491"},
        17458353747214397: {"status": None, "tcat_number": "907110309500"},
        17458388768345384: {"status": None, "tcat_number": "907110309511"},
        202504250001: {"status": None, "tcat_number": "907110309522"},
    }
    google_sheet_handle(order_status)
