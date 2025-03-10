"""
RemitScout Aggregator Configurator.

This module provides utilities to customize the behavior of the RemitScout
aggregator, including enabling/disabling providers and setting configuration options.
"""

import os
import json
import logging
from typing import List, Dict, Any, Set, Optional
from apps.aggregator.aggregator import Aggregator

logger = logging.getLogger(__name__)

# Default configuration file path
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "config",
    "aggregator_config.json"
)

# Make sure the config directory exists
os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)

class AggregatorConfig:
    """
    Utility class to manage aggregator configuration.
    
    This class allows you to enable/disable providers, set default
    sorting options, and configure other aspects of the aggregator.
    """
    
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        """
        Initialize the configurator.
        
        Args:
            config_path: Path to the configuration file.
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize with defaults if needed
        if not self.config:
            self._initialize_default_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Dictionary with configuration values.
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {}
            
    def _save_config(self) -> bool:
        """
        Save configuration to file.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
            return False
            
    def _initialize_default_config(self) -> None:
        """Initialize config with default values."""
        all_providers = self.get_all_available_providers()
        
        self.config = {
            "enabled_providers": list(all_providers),
            "default_sort": "best_rate",
            "default_max_workers": 10,
            "default_timeout": 30,
            "enable_caching": True,
            "cache_ttl_seconds": 600  # 10 minutes
        }
        
        self._save_config()
    
    def get_all_available_providers(self) -> Set[str]:
        """
        Get all available provider class names.
        
        Returns:
            Set of provider class names.
        """
        return {p.__class__.__name__ for p in Aggregator.PROVIDERS}
    
    def get_enabled_providers(self) -> List[str]:
        """
        Get enabled provider class names.
        
        Returns:
            List of enabled provider class names.
        """
        return self.config.get("enabled_providers", [])
    
    def enable_provider(self, provider_name: str) -> bool:
        """
        Enable a provider.
        
        Args:
            provider_name: Provider class name to enable.
            
        Returns:
            True if the provider was enabled, False otherwise.
        """
        all_providers = self.get_all_available_providers()
        if provider_name not in all_providers:
            logger.warning(f"Provider {provider_name} is not available")
            return False
        
        enabled_providers = set(self.get_enabled_providers())
        if provider_name in enabled_providers:
            logger.info(f"Provider {provider_name} is already enabled")
            return True
        
        enabled_providers.add(provider_name)
        self.config["enabled_providers"] = list(enabled_providers)
        return self._save_config()
    
    def disable_provider(self, provider_name: str) -> bool:
        """
        Disable a provider.
        
        Args:
            provider_name: Provider class name to disable.
            
        Returns:
            True if the provider was disabled, False otherwise.
        """
        enabled_providers = set(self.get_enabled_providers())
        if provider_name not in enabled_providers:
            logger.info(f"Provider {provider_name} is already disabled")
            return True
        
        enabled_providers.remove(provider_name)
        self.config["enabled_providers"] = list(enabled_providers)
        return self._save_config()
    
    def set_default_sort(self, sort_by: str) -> bool:
        """
        Set the default sort method.
        
        Args:
            sort_by: Sorting method ("best_rate", "lowest_fee", "fastest_time", or "best_value").
            
        Returns:
            True if successful, False otherwise.
        """
        valid_sorts = ["best_rate", "lowest_fee", "fastest_time", "best_value"]
        if sort_by not in valid_sorts:
            logger.error(f"Invalid sort method: {sort_by}. Must be one of {', '.join(valid_sorts)}")
            return False
        
        self.config["default_sort"] = sort_by
        return self._save_config()
    
    def set_default_max_workers(self, max_workers: int) -> bool:
        """
        Set the default maximum number of concurrent workers.
        
        Args:
            max_workers: Maximum number of workers.
            
        Returns:
            True if successful, False otherwise.
        """
        if max_workers < 1:
            logger.error(f"Invalid max_workers: {max_workers}. Must be at least 1")
            return False
        
        self.config["default_max_workers"] = max_workers
        return self._save_config()
    
    def set_default_timeout(self, timeout: int) -> bool:
        """
        Set the default timeout for provider requests in seconds.
        
        Args:
            timeout: Timeout in seconds.
            
        Returns:
            True if successful, False otherwise.
        """
        if timeout < 1:
            logger.error(f"Invalid timeout: {timeout}. Must be at least 1")
            return False
        
        self.config["default_timeout"] = timeout
        return self._save_config()
    
    def enable_caching(self, enabled: bool = True) -> bool:
        """
        Enable or disable result caching.
        
        Args:
            enabled: Whether caching should be enabled.
            
        Returns:
            True if successful, False otherwise.
        """
        self.config["enable_caching"] = enabled
        return self._save_config()
    
    def set_cache_ttl(self, ttl_seconds: int) -> bool:
        """
        Set the cache time-to-live in seconds.
        
        Args:
            ttl_seconds: TTL in seconds.
            
        Returns:
            True if successful, False otherwise.
        """
        if ttl_seconds < 1:
            logger.error(f"Invalid TTL: {ttl_seconds}. Must be at least 1")
            return False
        
        self.config["cache_ttl_seconds"] = ttl_seconds
        return self._save_config()
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Dictionary with configuration values.
        """
        return self.config
    
    def reset_to_defaults(self) -> bool:
        """
        Reset configuration to default values.
        
        Returns:
            True if successful, False otherwise.
        """
        self._initialize_default_config()
        return True
    
    def get_excluded_providers(self) -> List[str]:
        """
        Get list of provider class names to exclude from the aggregator.
        
        Returns:
            List of provider class names to exclude.
        """
        all_providers = self.get_all_available_providers()
        enabled_providers = set(self.get_enabled_providers())
        return list(all_providers - enabled_providers)
    
    def apply_config_to_aggregator(self) -> None:
        """Apply the current configuration to the Aggregator class."""
        # This doesn't modify the class directly but returns values needed
        # for configuring aggregator calls
        pass
    
    def get_aggregator_params(self) -> Dict[str, Any]:
        """
        Get parameters to use when calling Aggregator.get_all_quotes().
        
        Returns:
            Dictionary with parameters for the aggregator.
        """
        return {
            "exclude_providers": self.get_excluded_providers(),
            "sort_by": self.config.get("default_sort", "best_rate"),
            "max_workers": self.config.get("default_max_workers", 10)
        }
    
    def print_status(self) -> None:
        """Print status of enabled and disabled providers."""
        all_providers = sorted(list(self.get_all_available_providers()))
        enabled_providers = set(self.get_enabled_providers())
        
        print("\nRemitScout Aggregator Configuration")
        print("===================================")
        print(f"Total providers: {len(all_providers)}")
        print(f"Enabled providers: {len(enabled_providers)}")
        print(f"Disabled providers: {len(all_providers) - len(enabled_providers)}")
        print(f"Default sort: {self.config.get('default_sort', 'best_rate')}")
        print(f"Default max workers: {self.config.get('default_max_workers', 10)}")
        print(f"Default timeout: {self.config.get('default_timeout', 30)} seconds")
        print(f"Caching enabled: {self.config.get('enable_caching', True)}")
        print(f"Cache TTL: {self.config.get('cache_ttl_seconds', 600)} seconds")
        
        print("\nProvider Status:")
        print("----------------")
        for provider in all_providers:
            status = "✅ Enabled" if provider in enabled_providers else "❌ Disabled"
            print(f"{provider}: {status}")
        
        print("\nConfiguration file: {self.config_path}")


def get_configured_aggregator_params(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Utility function to get configured parameters for the aggregator.
    
    Args:
        config_path: Optional path to the configuration file.
        
    Returns:
        Dictionary with parameters for the aggregator.
    """
    config = AggregatorConfig(config_path or DEFAULT_CONFIG_PATH)
    return config.get_aggregator_params()


# Example Usage
if __name__ == "__main__":
    # Usage of the configurator
    config = AggregatorConfig()
    
    # Print current status
    config.print_status()
    
    # Simple demo of enabling/disabling providers
    # config.disable_provider("XoomProvider")
    # config.enable_provider("XoomProvider") 