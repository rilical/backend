"""
Base class for remittance providers.
"""
import abc
import uuid
import time
import datetime
from decimal import Decimal
from typing import Dict, Any, Optional


class RemittanceProvider(abc.ABC):
    """
    Abstract base class for standardized remittance provider interface.
    """

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
        **kwargs
    ) -> Dict[str, Any]:
        """Get standardized quote for money transfer between currencies."""
        raise NotImplementedError

    def standardize_response(
        self,
        raw_result: Dict[str, Any],
        provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Standardize the response shape for aggregator consumption.
        raw_result must contain keys like:
            "success", "error_message", "send_amount", "send_currency",
            "receive_amount", "receive_currency", "exchange_rate", "fee",
            "payment_method", "delivery_method", "delivery_time_minutes",
            ... plus any others your provider added
        """
        # Ensure required keys exist
        output = {
            "provider_id": self.name,
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),
            "send_amount": raw_result.get("send_amount", 0.0),
            "source_currency": raw_result.get("send_currency", "").upper(),
            "destination_amount": raw_result.get("receive_amount", 0.0),
            "destination_currency": raw_result.get("receive_currency", "").upper(),
            "exchange_rate": raw_result.get("exchange_rate"),
            "fee": raw_result.get("fee", 0.0),
            "payment_method": raw_result.get("payment_method"),
            "delivery_method": raw_result.get("delivery_method"),
            "delivery_time_minutes": raw_result.get("delivery_time_minutes"),
            "timestamp": datetime.datetime.now().isoformat(),
        }

        if provider_specific_data:
            output["raw_response"] = raw_result.get("raw_response")

        return output