import logging
from typing import Dict, Optional, List
from src.repositories.supabase_repository import InventoryRepository
from loguru import logger

class ProductConfigService:
    """
    Service for managing product configuration (Codes & Aliases).
    Replaces the legacy json-based ProductConfig.
    """
    
    def __init__(self, repository: InventoryRepository = None):
        self.repo = repository or InventoryRepository()
        self._product_codes: Dict[str, Dict] = {}
        self._product_aliases: Dict[str, str] = {}
        self._loaded = False

    def load_config(self, force_refresh: bool = False):
        """Load configuration from Supabase."""
        if self._loaded and not force_refresh:
            return

        logger.info("Loading product config from Supabase...")
        self._product_codes = self.repo.get_product_codes_map()
        self._product_aliases = self.repo.get_product_alias_map()
        self._loaded = True
        logger.info(f"Loaded {len(self._product_codes)} product codes and {len(self._product_aliases)} aliases.")

    def search_product_code(self, search_string: str) -> Optional[str]:
        """
        Search for a product code by alias/name.
        Returns product code or None.
        """
        if not self._loaded:
            self.load_config()

        if not search_string:
            return None

        # 1. Direct match in aliases
        if search_string in self._product_aliases:
            return self._product_aliases[search_string]

        # 2. Check if the string itself is a valid code
        if search_string in self._product_codes:
            return search_string

        return None

    def get_product_info(self, product_code: str) -> Optional[Dict]:
        """Get product info (qty, etc) by code."""
        if not self._loaded:
            self.load_config()
            
        return self._product_codes.get(product_code)

    def get_product_qty(self, product_code: str) -> int:
        """Get product quantity (items per pack) for box calculation."""
        info = self.get_product_info(product_code)
        if info:
            return info.get("qty", 1)
        return 0 # Return 0 if not found to indicate invalid product

    def get_all_products(self) -> List[Dict]:
        """Get all products with detailed info (aliases included)."""
        return self.repo.get_all_products_detailed()

    def create_product(self, code: str, name: str, qty: int) -> Dict:
        result = self.repo.create_product(code, name, qty)
        if result:
            self.load_config(force_refresh=True)
        return result

    def update_product_qty(self, code: str, qty: int) -> Dict:
        result = self.repo.update_product_qty(code, qty)
        if result:
            self.load_config(force_refresh=True)
        return result

    def delete_product(self, code: str) -> bool:
        success = self.repo.delete_product(code)
        if success:
            self.load_config(force_refresh=True)
        return success

    def add_alias(self, product_code: str, alias: str) -> Dict:
        result = self.repo.add_product_alias(product_code, alias)
        if result:
            self.load_config(force_refresh=True)
        return result

    def delete_alias(self, alias_id: int) -> bool:
        success = self.repo.delete_product_alias(alias_id)
        if success:
            self.load_config(force_refresh=True)
        return success
