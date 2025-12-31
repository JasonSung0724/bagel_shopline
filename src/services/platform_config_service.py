import logging
from typing import Dict, Optional, List
from src.repositories.supabase_repository import InventoryRepository
from loguru import logger


class ColumnMappingService:
    """
    Service for managing unified column mappings.
    All platforms share the same mapping - aliases are combined.
    """

    def __init__(self, repository: InventoryRepository = None):
        self.repo = repository or InventoryRepository()
        self._mapping: Dict[str, List[str]] = {}
        self._loaded = False

    def load_config(self, force_refresh: bool = False):
        """Load column mappings from Supabase."""
        if self._loaded and not force_refresh:
            return

        logger.info("Loading unified column mappings from Supabase...")
        self._mapping = self.repo.get_column_mappings()
        self._loaded = True
        logger.info(f"Loaded mappings for fields: {list(self._mapping.keys())}")

    def get_mapping(self) -> Dict[str, List[str]]:
        """Get the unified column mapping."""
        if not self._loaded:
            self.load_config()
        return self._mapping

    def get_aliases(self, field_name: str) -> List[str]:
        """Get aliases for a specific field."""
        if not self._loaded:
            self.load_config()
        return self._mapping.get(field_name, [])

    def update_mapping(self, mapping: Dict[str, List[str]]) -> bool:
        """Update all mappings and refresh cache."""
        success = self.repo.update_column_mappings(mapping)
        if success:
            self.load_config(force_refresh=True)
        return success

    def update_field(self, field_name: str, aliases: List[str]) -> bool:
        """Update aliases for a single field."""
        success = self.repo.update_field_aliases(field_name, aliases)
        if success:
            self.load_config(force_refresh=True)
        return success

    def validate_columns(self, df_columns: List[str]) -> Dict[str, bool]:
        """
        Validate which fields can be found in the given columns.
        Returns: { 'order_id': True, 'receiver_name': False, ... }
        """
        if not self._loaded:
            self.load_config()

        df_cols_set = set(str(c).strip() for c in df_columns)
        result = {}

        for field, aliases in self._mapping.items():
            found = any(alias in df_cols_set for alias in aliases)
            result[field] = found

        return result


# Backward compatibility alias
PlatformConfigService = ColumnMappingService
