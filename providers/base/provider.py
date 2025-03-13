"""
Base provider class for remittance providers.
"""
import abc
import datetime
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union


class RemittanceProvider(abc.ABC):
    """
    Abstract base class for all remittance providers.
    
    This class defines the interface that all provider implementations must follow,
    and provides default implementations that can be overridden by subclasses.
    """
    
    @classmethod
    def get_provider_id(cls) -> str:
        """
        Get the unique identifier for this provider.
        
        Returns:
            String identifier for the provider.
        """
        # Default implementation: Extract from class name
        # e.g., WiseProvider -> "WISE"
        class_name = cls.__name__
        if class_name.endswith("Provider"):
            return class_name[:-8].upper()
        return class_name.upper()
    
    @classmethod
    def get_display_name(cls) -> str:
        """
        Get the human-readable name for this provider.
        
        Returns:
            Display name for the provider.
        """
        # Default implementation: Create from provider_id
        # e.g., "WISE" -> "Wise"
        provider_id = cls.get_provider_id()
        return provider_id.replace('_', ' ').title()

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url

    @abc.abstractmethod
    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        dest_currency: str,
        source_country: str,
        dest_country: str,
        payment_method: Optional[str] = None,
        delivery_method: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Get standardized quote for money transfer between currencies."""
        raise NotImplementedError

    def standardize_response(
        self, raw_result: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Standardize the response shape for aggregator consumption.
        raw_result must contain keys like:
            "success", "error_message", "send_amount", "send_currency",
            "receive_amount", "receive_currency", "exchange_rate", "fee",
            "payment_method", "delivery_method", "delivery_time_minutes",
            ... plus any others your provider added
        """
        # Normalize timestamp
        timestamp = raw_result.get("timestamp")
        if timestamp is None:
            timestamp = datetime.datetime.now().isoformat()
        elif isinstance(timestamp, (int, float)):
            # Convert unix timestamp to ISO format
            timestamp = datetime.datetime.fromtimestamp(timestamp).isoformat()
        
        # Normalize numeric values
        send_amount = self._normalize_numeric(raw_result.get("send_amount", 0.0))
        destination_amount = self._normalize_numeric(raw_result.get("receive_amount", 0.0))
        exchange_rate = self._normalize_numeric(raw_result.get("exchange_rate"))
        fee = self._normalize_numeric(raw_result.get("fee", 0.0))
        
        # Handle multiple delivery methods
        delivery_methods = raw_result.get("delivery_methods", [])
        if not delivery_methods and raw_result.get("delivery_method"):
            delivery_methods = [{"method": raw_result.get("delivery_method"), 
                                "time_minutes": raw_result.get("delivery_time_minutes")}]
        
        # Ensure required keys exist
        output = {
            "provider_id": self.name,
            "provider_name": self.get_display_name(),
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),
            "send_amount": send_amount,
            "source_currency": str(raw_result.get("send_currency", "")).upper(),
            "destination_amount": destination_amount,
            "destination_currency": str(raw_result.get("receive_currency", "")).upper(),
            "exchange_rate": exchange_rate,
            "fee": fee,
            "payment_method": raw_result.get("payment_method"),
            "delivery_method": raw_result.get("delivery_method"),
            "delivery_time_minutes": raw_result.get("delivery_time_minutes"),
            "delivery_methods": delivery_methods,
            "timestamp": timestamp,
        }

        if provider_specific_data:
            output["raw_response"] = raw_result.get("raw_response")

        return output
    
    def _normalize_numeric(self, value: Any) -> Union[float, None]:
        """
        Normalize numeric values to float type or None.
        """
        if value is None:
            return None
            
        try:
            if isinstance(value, str):
                return float(value.replace(',', ''))
            return float(value)
        except (ValueError, TypeError):
            return None
