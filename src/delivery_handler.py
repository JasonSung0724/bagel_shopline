from typing import Dict

class DeliveryHandler:
    def __init__(self):
        self.delivery_provider = {
            "delivery_provider_name": {
                "id": "T-CAT",
                "name": "黑貓宅急便",
                "code": "T-CAT"
            }
        }

    def get_provider_name(self) -> str:
        """
        獲取物流提供者名稱
        :return: 物流提供者名稱
        """
        return self.delivery_provider["delivery_provider_name"]["name"]

    def to_api_format(self) -> Dict:
        """
        轉換為 API 所需的格式 (Ruby Hash 格式)
        :return: API 格式的物流提供者資訊
        """
        return {
            "delivery_provider_name": self.delivery_provider["delivery_provider_name"]
        }

    def to_full_format(self) -> Dict:
        """
        轉換為完整格式（包含多語言資訊）
        :return: 完整的物流提供者資訊
        """
        return self.delivery_provider


# 使用範例
if __name__ == "__main__":
    handler = DeliveryHandler()
    
    # 獲取名稱
    name = handler.get_provider_name()  # 返回 "黑貓宅急便"
    
    # 獲取 API 格式
    api_data = handler.to_api_format()
    # 返回: 
    # {
    #     "delivery_provider_name": {
    #         "id": "T-CAT",
    #         "name": "黑貓宅急便",
    #         "code": "T-CAT"
    #     }
    # }
    
    # 獲取完整格式（包含多語言）
    full_data = handler.to_full_format()
    # 返回完整的配置資訊 