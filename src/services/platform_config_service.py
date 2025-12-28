import logging
from typing import Dict, Optional, List
from src.repositories.supabase_repository import InventoryRepository
from loguru import logger

class PlatformConfigService:
    """
    Service for managing platform column mappings (Shopline, Mixx, etc).
    Handles loading, caching, and auto-detection scoring.
    """
    
    def __init__(self, repository: InventoryRepository = None):
        self.repo = repository or InventoryRepository()
        self._configs: Dict[str, Dict] = {}
        self._loaded = False

    def load_config(self, force_refresh: bool = False):
        """Load platform configs from Supabase."""
        if self._loaded and not force_refresh:
            return

        logger.info("Loading platform configs from Supabase...")
        self._configs = self.repo.get_all_platform_configs()
        self._loaded = True
        logger.info(f"Loaded configs for platforms: {list(self._configs.keys())}")

    def get_mapping(self, platform: str) -> Dict[str, List[str]]:
        """Get column mapping for a specific platform."""
        if not self._loaded:
            self.load_config()
        return self._configs.get(platform.lower(), {})

    def get_all_mappings(self) -> Dict[str, Dict]:
        """Get all mappings."""
        if not self._loaded:
            self.load_config()
        return self._configs

    def update_mapping(self, platform: str, mapping: Dict) -> bool:
        """Update mapping for a platform and refresh cache."""
        success = self.repo.update_platform_config(platform.lower(), mapping)
        if success:
            self.load_config(force_refresh=True)
        return success
    
    def auto_detect_platform(self, df_columns: List[str]) -> str:
        """
        Auto-detect platform by comparing DataFrame columns with config mappings.
        Returns the platform name with the highest match score.
        """
        if not self._loaded:
            self.load_config()
            
        best_platform = None
        max_score = 0
        
        # Normalize df columns for comparison (strip whitespace)
        df_cols_set = set(str(c).strip() for c in df_columns)
        
        for platform, mapping in self._configs.items():
            score = 0
            required_count = 0
            
            # Simple scoring: +1 for every matched field (if any of its aliases exist)
            for field, aliases in mapping.items():
                # Check if ANY alias for this field exists in df
                matched = False
                for alias in aliases:
                    if alias in df_cols_set:
                        matched = True
                        break
                
                if matched:
                    score += 1
                
                # We could implement "weighting" here if needed (e.g. order_id is crucial)
            
            # Normalize score? Or just raw count. Use simple count for now.
            logger.debug(f"Platform {platform} score: {score}")
            
            if score > max_score:
                max_score = score
                best_platform = platform
                
        # threshold? At least 2 matches?
        if max_score >= 2:
            return best_platform
        return None
