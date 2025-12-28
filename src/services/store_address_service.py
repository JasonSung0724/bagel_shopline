import requests
import xml.etree.ElementTree as ET
import json
from loguru import logger
from typing import Dict, List, Optional

class StoreAddressService:
    """
    Service to fetch store addresses for 7-11 and FamilyMart.
    """
    
    def __init__(self):
        self.session = requests.Session()

    def fetch_store_addresses(self, seven_stores: List[str], family_stores: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Fetch addresses for provided store names.
        Returns: {
            "SEVEN": {"store_name": "address", ...},
            "FAMILY": {"store_name": "address", ...}
        }
        """
        result = {
            "SEVEN": {},
            "FAMILY": {}
        }
        
        # 7-11
        for store in seven_stores:
             try:
                 address = self._fetch_seven_location(store)
                 if address:
                     result["SEVEN"][store] = address
                 else:
                     result["SEVEN"][store] = f"ERROR : 無法確認{store}正確地址"
             except Exception as e:
                 logger.error(f"Error fetching 7-11 store {store}: {e}")
                 result["SEVEN"][store] = "ERROR : 查詢失敗"

        # Family
        for store in family_stores:
            try:
                address = self._fetch_family_location(store)
                if address:
                    result["FAMILY"][store] = address
                else:
                    result["FAMILY"][store] = f"ERROR : 無法確認{store}正確地址"
            except Exception as e:
                logger.error(f"Error fetching Family store {store}: {e}")
                result["FAMILY"][store] = "ERROR : 查詢失敗"
                
        return result

    def _fetch_seven_location(self, store_name: str) -> Optional[str]:
        input_name = store_name if "門市" not in store_name else store_name.split("門市")[0]
        url = "https://emap.pcsc.com.tw/EMapSDK.aspx"
        data = {
            "commandid": "SearchStore",
            "city": "",
            "town": "",
            "roadname": "",
            "ID": "",
            "StoreName": input_name,
            "SpecialStore_Kind": "",
            "leftMenuChecked": "",
            "address": "",
        }
        response = self.session.post(url, data=data, timeout=10)
        xml_data = response.text
        root = ET.fromstring(xml_data)
        
        # Note: XML structure <GeoPosition><Address>...</Address><POIName>...</POIName></GeoPosition>
        for geo_position in root.findall("GeoPosition"):
            name = geo_position.find("POIName").text
            address = geo_position.find("Address").text
            # Strict match to avoid partial matches returning wrong store? 
            # Original code did: if name == input_name. 
            # Sometimes API returns multiple.
            if name == input_name:
                return address
        
        return None

    def _fetch_family_location(self, store_name: str) -> Optional[str]:
        url = "https://api.map.com.tw/net/familyShop.aspx"
        params = {
            "searchType": "ShopName", 
            "type": "", 
            "kw": store_name, 
            "fun": "getByName", 
            "key": "6F30E8BF706D653965BDE302661D1241F8BE9EBC"
        }
        headers = {
            "Referer": "https://www.family.com.tw/",
        }
        response = self.session.get(url, params=params, headers=headers, timeout=10)
        
        # Response is JSONP-ish: [json]
        try:
            start_index = response.text.find("[")
            end_index = response.text.rfind("]") + 1
            if start_index == -1 or end_index == 0:
                return None
                
            json_text = response.text[start_index:end_index]
            data = json.loads(json_text)
            
            for store_info in data:
                if store_name == store_info.get("NAME"):
                    return store_info.get("addr")
        except:
            return None
            
        return None
