"""
RemitGuru Money Transfer Integration

This module implements the integration with RemitGuru, a digital money transfer service
that offers competitive rates for international remittances.

The integration uses RemitGuru's public API to fetch exchange rates and fees
for international money transfers.
"""

import json
import logging
import time
import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
import requests

from apps.providers.base.provider import RemittanceProvider
from apps.providers.utils.country_currency_standards import normalize_country_code, validate_corridor
from apps.providers.utils.currency_mapping import get_country_currencies

# Setup logging
logger = logging.getLogger(__name__)


class RemitGuruProvider(RemittanceProvider):
    """
    Aggregator-ready RemitGuru integration without mock data.
    
    This provider fetches quotes (exchange rates, fees) from RemitGuru's
    public API for specific corridors. If an error or unsupported corridor
    is encountered, it returns an error response instead of fallback data.
    
    NOTE: RemitGuru currently only supports money transfers from UK (GBP) to India (INR).
    All other corridors will return appropriate error responses.
    """
    
    BASE_URL = "https://www.remitguru.com"
    QUOTE_ENDPOINT = "/transfer/jsp/getQTStatistics.jsp"
    
    # Default payment/delivery methods and estimated delivery time (minutes)
    DEFAULT_PAYMENT_METHOD = "bank"
    DEFAULT_DELIVERY_METHOD = "bank"
    DEFAULT_DELIVERY_TIME = 1440  # 24 hours in minutes
    
    # Maps 2-letter country codes to RemitGuru country codes (e.g. "GB" -> "GB", "IN" -> "IN")
    # Keep only non-standard mappings
    CORRIDOR_MAPPING = {
        "UK": "GB",  # UK is non-standard, maps to GB (ISO standard)
    }
    
    # Maps RemitGuru country codes to default currency codes
    # Only GB->IN is supported, so we only need these currencies
    CURRENCY_MAPPING = {
        "GB": "GBP",  # United Kingdom - British Pound
        "IN": "INR",  # India - Indian Rupee
    }
    
    # IMPORTANT: RemitGuru only supports this one corridor
    SUPPORTED_CORRIDORS = [
        ("GB", "IN"),  # UK to India - ONLY SUPPORTED CORRIDOR
    ]
    
    def __init__(self, name="remitguru", **kwargs):
        """
        Initialize the RemitGuru provider.
        
        Args:
            name: Provider identifier
            **kwargs: Additional parameters
        """
        super().__init__(name=name, base_url=self.BASE_URL)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
                "Safari/537.36"
            ),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "*/*",
            "Origin": self.BASE_URL,
            "Referer": f"{self.BASE_URL}/",
            "Connection": "keep-alive",
            "Accept-Language": "en-US,en;q=0.9"
        })
        self.logger = logging.getLogger(f"providers.{name}")
        self._visit_homepage()
    
    def standardize_response(
        self,
        raw_result: Dict[str, Any],
        provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Standardize the response shape for aggregator consumption.
        
        Follows the structure defined in RemittanceProvider base class
        to ensure consistent response format across all providers.
        """
        # Ensure required keys exist with proper formatting
        output = {
            "provider_id": self.name,
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),
            "send_amount": raw_result.get("send_amount", 0.0),
            "source_currency": raw_result.get("source_currency", "").upper(),
            "destination_amount": raw_result.get("destination_amount", 0.0),
            "destination_currency": raw_result.get("destination_currency", "").upper(),
            "exchange_rate": raw_result.get("exchange_rate"),
            "fee": raw_result.get("fee", 0.0),
            "payment_method": raw_result.get("payment_method", self.DEFAULT_PAYMENT_METHOD),
            "delivery_method": raw_result.get("delivery_method", self.DEFAULT_DELIVERY_METHOD),
            "delivery_time_minutes": raw_result.get("delivery_time_minutes", self.DEFAULT_DELIVERY_TIME),
            "timestamp": raw_result.get("timestamp", datetime.datetime.now().isoformat()),
        }

        if provider_specific_data and "raw_response" in raw_result:
            output["raw_response"] = raw_result["raw_response"]

        return output
    
    def _visit_homepage(self):
        """Obtain initial cookies by visiting RemitGuru's homepage."""
        try:
            logger.debug("Requesting RemitGuru homepage for session cookies")
            resp = self.session.get(self.BASE_URL, timeout=30)
            resp.raise_for_status()
            time.sleep(1)
        except Exception as exc:
            logger.error(f"Could not visit RemitGuru homepage: {exc}")
    
    def _build_corridor_str(
        self, send_country: str, send_currency: str, 
        recv_country: str, recv_currency: str
    ) -> str:
        """Build the corridor string in RemitGuru's expected format."""
        return f"{send_country}~{send_currency}~{recv_country}~{recv_currency}"
    
    def _is_corridor_supported(self, send_country: str, recv_country: str) -> bool:
        """Check if a corridor is in the list of supported corridors."""
        return (send_country, recv_country) in self.SUPPORTED_CORRIDORS
    
    def _get_country_currency(self, country_code: str) -> Optional[str]:
        """
        Map country code to RemitGuru's expected currency.
        First tries RemitGuru's own mapping, then falls back to standard mapping.
        """
        # Normalize and map country code
        country_code = normalize_country_code(country_code)
        mapped_code = self.CORRIDOR_MAPPING.get(country_code, country_code)
        
        # Try RemitGuru's specific mapping
        currency = self.CURRENCY_MAPPING.get(mapped_code)
        if currency:
            return currency
            
        # Fall back to standard mapping
        currencies = get_country_currencies(country_code)
        if currencies:
            return currencies[0]
            
        return None
    
    def _internal_get_quote(
        self, 
        send_amount: Decimal, 
        send_country_code: str, 
        recv_country_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Request a quote from RemitGuru for a given corridor and amount.
        
        Args:
            send_amount: Decimal, amount to send
            send_country_code: Source country code (e.g., "GB")
            recv_country_code: Destination country code (e.g., "IN")
        
        Returns:
            Parsed response dict or None if an error occurs
        """
        send_country_mapped = self.CORRIDOR_MAPPING.get(send_country_code, send_country_code)
        recv_country_mapped = self.CORRIDOR_MAPPING.get(recv_country_code, recv_country_code)
        send_currency = self._get_country_currency(send_country_code)
        recv_currency = self._get_country_currency(recv_country_code)
        
        if not send_currency or not recv_currency:
            logger.error(f"No currency mapping for corridor {send_country_code} -> {recv_country_code}")
            return None
        
        if not self._is_corridor_supported(send_country_mapped, recv_country_mapped):
            logger.warning(f"Corridor {send_country_mapped} -> {recv_country_mapped} not in known corridors")
        
        corridor_str = self._build_corridor_str(
            send_country_mapped, send_currency,
            recv_country_mapped, recv_currency
        )
        
        payload = {
            "amountTransfer": str(int(send_amount)),
            "corridor": corridor_str,
            "sendMode": "CIP-FER"
        }
        
        url = f"{self.BASE_URL}{self.QUOTE_ENDPOINT}"
        try:
            resp = self.session.post(url, data=payload, timeout=30)
            resp.raise_for_status()
            content = resp.text.strip()
            if not content or '|' not in content:
                logger.error(f"Invalid RemitGuru response: {content}")
                return None
            
            parts = content.split('|')
            if len(parts) < 7:
                logger.error(f"Not enough data in RemitGuru response: {content}")
                return None
            
            receive_amount_str, rate_str, fee_str, send_amt_str, error_msg, valid_flag, send_cur = parts[:7]
            error_code = parts[7] if len(parts) > 7 else None
            
            if valid_flag.lower() != "true":
                return {
                    "is_valid": False,
                    "error": error_msg or "Invalid quote",
                    "error_code": error_code,
                    "raw_response": content
                }
            
            receive_amount = Decimal(receive_amount_str) if receive_amount_str else None
            exchange_rate = Decimal(rate_str) if rate_str else None
            fee = Decimal(fee_str) if fee_str else Decimal('0')
            send_amount_confirmed = Decimal(send_amt_str) if send_amt_str else send_amount
            return {
                "receive_amount": receive_amount,
                "exchange_rate": exchange_rate,
                "fee": fee,
                "send_amount": send_amount_confirmed,
                "is_valid": True,
                "send_currency": send_cur if send_cur else send_currency,
                "receive_currency": recv_currency,
                "raw_response": content
            }
        except requests.RequestException as exc:
            logger.error(f"RemitGuru API request failed: {exc}")
            return None
        except Exception as exc:
            logger.error(f"Unexpected error parsing RemitGuru quote: {exc}")
            return None
    
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
        """
        Get a standardized quote for money transfer between currencies.
        
        This implements the abstract method from RemittanceProvider.
        """
        # Normalize country codes
        source_country = normalize_country_code(source_country)
        dest_country = normalize_country_code(dest_country)
        
        # Validate corridor
        is_valid, error_message = validate_corridor(
            source_country=source_country,
            source_currency=source_currency,
            dest_country=dest_country,
            dest_currency=dest_currency
        )
        
        if not is_valid:
            return self.standardize_response({
                "success": False,
                "error_message": error_message,
                "send_amount": float(amount),
                "source_currency": source_currency.upper(),
                "destination_currency": dest_currency.upper(),
                "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD
            })
        
        # Get the internal quote
        quote = self._internal_get_quote(amount, source_country, dest_country)
        
        if not quote:
            return self.standardize_response({
                "success": False,
                "error_message": "RemitGuru quote request failed or invalid response",
                "send_amount": float(amount),
                "source_currency": source_currency.upper(),
                "destination_currency": dest_currency.upper(),
                "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD
            })
        
        if not quote.get("is_valid", False):
            return self.standardize_response({
                "success": False,
                "error_message": quote.get("error", "Invalid corridor or unknown error"),
                "send_amount": float(amount),
                "source_currency": source_currency.upper(),
                "destination_currency": dest_currency.upper(),
                "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD
            })
        
        # Build success response
        return self.standardize_response({
            "success": True,
            "error_message": None,
            "send_amount": float(quote.get("send_amount", amount)),
            "source_currency": quote.get("send_currency", source_currency.upper()),
            "destination_currency": quote.get("receive_currency", dest_currency.upper()),
            "destination_amount": float(quote.get("receive_amount", 0.0)),
            "exchange_rate": float(quote.get("exchange_rate", 0.0)),
            "fee": float(quote.get("fee", 0.0)),
            "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
            "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
            "delivery_time_minutes": self.DEFAULT_DELIVERY_TIME,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        target_currency: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy method for getting exchange rate.
        
        This method is maintained for backward compatibility.
        For new code, use get_quote instead.
        """
        # Determine sending country from the currency
        send_country_code = None
        for cty, cur in self.CURRENCY_MAPPING.items():
            if cur == send_currency.upper():
                send_country_code = cty
                break
        
        if not send_country_code:
            return self.standardize_response({
                "success": False,
                "error_message": f"Unsupported sending currency: {send_currency}",
                "send_amount": float(send_amount),
                "source_currency": send_currency.upper(),
                "destination_currency": target_currency.upper()
            })
        
        # Determine receiving country from the currency
        recv_country_code = None
        for cty, cur in self.CURRENCY_MAPPING.items():
            if cur == target_currency.upper():
                recv_country_code = cty
                break
                
        # If no country code found, use kwargs or default to None
        if not recv_country_code:
            recv_country_code = kwargs.get("receive_country")
            
        if not recv_country_code:
            return self.standardize_response({
                "success": False,
                "error_message": f"Cannot determine country for currency: {target_currency}",
                "send_amount": float(send_amount),
                "source_currency": send_currency.upper(),
                "destination_currency": target_currency.upper()
            })
        
        # Call standardized get_quote method
        return self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            dest_currency=target_currency,
            source_country=send_country_code,
            dest_country=recv_country_code,
            payment_method=kwargs.get("payment_method"),
            delivery_method=kwargs.get("delivery_method")
        )
    
    def get_supported_countries(self) -> List[str]:
        """Return list of supported countries in ISO alpha-2 format."""
        # Include both source and destination countries
        source_countries = set(country for country, _ in self.SUPPORTED_CORRIDORS)
        dest_countries = set(country for _, country in self.SUPPORTED_CORRIDORS)
        return sorted(list(source_countries.union(dest_countries)))
    
    def get_supported_currencies(self) -> List[str]:
        """Return list of supported currencies in ISO format."""
        return sorted(list(set(self.CURRENCY_MAPPING.values())))
    
    def close(self):
        """Close the session if it's open."""
        if self.session:
            self.session.close()
            self.session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 