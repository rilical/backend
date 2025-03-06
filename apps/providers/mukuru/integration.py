"""
Mukuru Integration

This module implements the integration with Mukuru's public endpoints
to fetch exchange rates, fees, and supported corridors.
"""

import logging
import json
import re
import requests
from decimal import Decimal
from typing import Dict, Any, List, Optional

# Import the base provider class
from apps.providers.base import RemittanceProvider
from apps.providers.mukuru.exceptions import (
    MukuruError,
    MukuruConnectionError,
    MukuruApiError,
    MukuruResponseError,
    MukuruCorridorUnsupportedError,
    MukuruRateLimitError,
)

logger = logging.getLogger(__name__)


class MukuruProvider(RemittanceProvider):
    """
    Provider implementation for Mukuru, which offers cross-border
    money transfer services primarily from South Africa to various
    African countries and beyond.

    Example usage:
        mukuru = MukuruProvider()
        quote = mukuru.get_exchange_rate(
            send_amount=Decimal("900"),
            send_currency="ZAR",
            receive_country="ZW"
        )
    """

    # Public Mukuru endpoints
    BASE_URL = "https://mobile.mukuru.com"
    PRICECHECKER_CALCULATE_PATH = "/pricechecker/calculate"
    PRICECHECKER_COUNTRIES_PATH = "/pricechecker/get_recipient_countries"
    
    # Mapping of ISO country codes to currencies
    COUNTRY_TO_CURRENCY = {
        'ZA': 'ZAR',  # South Africa - South African Rand
        'ZW': 'USD',  # Zimbabwe - US Dollar
        'GH': 'GHS',  # Ghana - Ghana Cedi
        'NG': 'NGN',  # Nigeria - Nigerian Naira
        'ML': 'XOF',  # Mali - West African CFA franc
        'MZ': 'MZN',  # Mozambique - Mozambican Metical
        'KE': 'KES',  # Kenya - Kenyan Shilling
        'MW': 'MWK',  # Malawi - Malawian Kwacha
    }
    
    # Default corridors based on Mukuru's typical operations
    SUPPORTED_CORRIDORS = [
        # From -> To
        ('ZA', 'ZW'),  # South Africa to Zimbabwe
        ('ZA', 'GH'),  # South Africa to Ghana
        ('ZA', 'NG'),  # South Africa to Nigeria
        ('ZA', 'MZ'),  # South Africa to Mozambique
        ('ZA', 'MW'),  # South Africa to Malawi
    ]
    
    # Currency ID mapping (based on Mukuru's internal IDs)
    CURRENCY_ID_MAPPING = {
        ('ZA', 'ZW'): 18,  # For ZAR to USD (Zimbabwe)
        ('ZA', 'GH'): 20,  # Example ID for Ghana (placeholder)
        ('ZA', 'NG'): 21,  # Example ID for Nigeria (placeholder)
        # Add more as discovered
    }

    def __init__(self, name="mukuru", **kwargs):
        """
        Initialize the Mukuru provider.
        :param name: internal provider name
        :param kwargs: additional config
        """
        super().__init__(name=name, base_url=self.BASE_URL, **kwargs)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.3 Safari/605.1.15"
            ),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        })

        # Cache for supported countries and currencies
        self._supported_countries = None

    def get_supported_countries(self) -> Dict[str, str]:
        """
        Retrieve the list of recipient countries from the Mukuru API.
        
        Returns:
            A dictionary mapping country codes to currency codes 
            (e.g., {'ZW': 'USD', 'GH': 'GHS'})
        """
        # Return cached results if available
        if self._supported_countries is not None:
            return self._supported_countries
        
        url = self.BASE_URL + self.PRICECHECKER_COUNTRIES_PATH
        logger.info(f"Fetching Mukuru recipient countries from {url}")
        
        try:
            resp = self.session.get(url, params={
                "brand_id": 1,
                "sales_channel": "mobi",
            }, timeout=15)
            resp.raise_for_status()
            
            try:
                data = resp.json()
                
                if data.get("status") != "success":
                    logger.error("Mukuru get_recipient_countries returned non-success status")
                    return {}
                
                result = {}
                for country_code, info in data.get("data", {}).items():
                    currency_iso = info.get("currency_market_iso")
                    result[country_code] = currency_iso
                
                # Cache the results
                self._supported_countries = result
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                raise MukuruResponseError(f"Failed to parse JSON response: {str(e)}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error fetching Mukuru countries: {str(e)}")
            raise MukuruConnectionError(f"Failed to connect to Mukuru API: {str(e)}")

    def get_currency_id(self, from_country: str, to_country: str) -> int:
        """
        Get the currency ID for a specific corridor.
        
        Args:
            from_country: ISO country code of sending country (e.g., 'ZA')
            to_country: ISO country code of receiving country (e.g., 'ZW')
            
        Returns:
            The currency ID for the corridor, or a default value if not found
        """
        # Try to get the currency ID from the mapping
        currency_id = self.CURRENCY_ID_MAPPING.get((from_country, to_country))
        
        # If not found, use default ID for Zimbabwe as fallback
        if currency_id is None:
            logger.warning(f"No currency ID found for {from_country} to {to_country}, using default")
            currency_id = 18  # Default to ZW (Zimbabwe) corridor
        
        return currency_id

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retrieve a quote from Mukuru's pricechecker/calculate endpoint.
        
        Args:
            send_amount: Amount to send in the source currency
            send_currency: The currency code of the sending country (e.g., 'ZAR')
            receive_country: ISO country code of receiving country (e.g., 'ZW')
            **kwargs: Additional parameters including from_country_code
            
        Returns:
            Dictionary with exchange rate information
        """
        # Get the from_country_code from kwargs or default to 'ZA' (South Africa)
        from_country_code = kwargs.get("from_country_code", "ZA")
        
        # Get the currency ID for this corridor
        currency_id = self.get_currency_id(from_country_code, receive_country)
        
        # Create result dictionary
        result = {
            "provider": self.name,
            "success": False,
            "send_amount": float(send_amount),
            "send_currency": send_currency,
            "receive_country": receive_country,
            "error_message": None
        }
        
        # Build the API request
        url = self.BASE_URL + self.PRICECHECKER_CALCULATE_PATH
        params = {
            "from_currency_iso": send_currency,   # e.g. 'ZAR'
            "payin_amount": str(send_amount),     # e.g. '900'
            "from_country": from_country_code,    # e.g. 'ZA'
            "to_currency_iso": "",                # often empty if we rely on currency_id
            "payout_amount": "",
            "to_country": receive_country,        # e.g. 'ZW'
            "currency_id": currency_id,
            "active_input": "payin_amount",
            "brand_id": 1,
            "sales_channel": "mobi",
        }
        
        logger.info(f"Requesting Mukuru quote for {send_currency} {send_amount} to {receive_country}")
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            
            try:
                data = resp.json()
                
                if data.get("status") != "success":
                    error_msg = f"Non-success status from Mukuru: {data}"
                    logger.error(error_msg)
                    result["error_message"] = error_msg
                    return result
                
                # Extract data from the response
                quote_data = data.get("data", {})
                breakdown = quote_data.get("breakdown", {})
                
                # Extract exchange rate from the Rate field (e.g., "$1:R18.7248")
                rate_str = breakdown.get("Rate", "")
                exchange_rate = None
                
                # Parse the rate string to extract the exchange rate
                rate_match = re.search(r"R(\d+(\.\d+)?)", rate_str)
                if rate_match:
                    zar_per_unit = float(rate_match.group(1))  # e.g., 18.7248
                    if zar_per_unit:
                        exchange_rate = 1.0 / zar_per_unit  # Convert to USD per ZAR
                else:
                    logger.warning(f"Could not parse exchange rate from: {rate_str}")
                
                # Extract fee from the Charge field (e.g., "ZAR94.00")
                payin_info = breakdown.get("payin", {})
                fee_str = payin_info.get("Charge", "")  # e.g., "ZAR94.00"
                fee_value = 0.0
                
                fee_match = re.search(r"(\d+(\.\d+)?)", fee_str)
                if fee_match:
                    fee_value = float(fee_match.group(1))
                
                # Extract receive amount from They receive field (e.g., "USD50.00")
                payout_info = breakdown.get("payout", {})
                receive_str = payout_info.get("They receive", "")  # e.g., "USD50.00"
                receive_amount = 0.0
                
                receive_match = re.search(r"(\d+(\.\d+)?)", receive_str)
                if receive_match:
                    receive_amount = float(receive_match.group(1))
                
                # Set receive_currency based on the They receive field
                receive_currency_match = re.search(r"([A-Z]{3})", receive_str)
                receive_currency = None
                if receive_currency_match:
                    receive_currency = receive_currency_match.group(1)
                
                # Update result with the extracted information
                result.update({
                    "success": True,
                    "exchange_rate": exchange_rate,
                    "receive_amount": receive_amount,
                    "fee": fee_value,
                    "receive_currency": receive_currency,
                })
                
                return result
                
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON response: {str(e)}"
                logger.error(error_msg)
                result["error_message"] = error_msg
                return result
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection error fetching Mukuru quote: {str(e)}"
            logger.error(error_msg)
            result["error_message"] = error_msg
            return result

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        target_country: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for a money transfer.
        
        Args:
            amount: Amount to send
            source_currency: Currency code of the sending amount (e.g., 'ZAR')
            target_country: ISO country code of the receiving country (e.g., 'ZW')
            **kwargs: Additional parameters including from_country_code
            
        Returns:
            Dictionary with quote information
        """
        # Extract from_country_code from kwargs or infer it from source_currency
        from_country_code = kwargs.get("from_country_code")
        
        if not from_country_code:
            # Try to find a country that uses this currency as default
            for country, currency in self.COUNTRY_TO_CURRENCY.items():
                if currency == source_currency:
                    from_country_code = country
                    break
            
            # If still not found, default to ZA (South Africa)
            if not from_country_code:
                from_country_code = "ZA"
        
        # Call get_exchange_rate with the determined parameters
        return self.get_exchange_rate(
            send_amount=amount,
            send_currency=source_currency,
            receive_country=target_country,
            from_country_code=from_country_code,
            **kwargs
        ) 