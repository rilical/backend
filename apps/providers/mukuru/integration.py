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
from datetime import datetime

from apps.providers.base.provider import RemittanceProvider
from apps.providers.mukuru.exceptions import (
    MukuruError,
    MukuruConnectionError,
    MukuruApiError,
    MukuruResponseError,
    MukuruCorridorUnsupportedError,
    MukuruRateLimitError,
)
from apps.providers.mukuru.mapping import (
    COUNTRY_TO_CURRENCY,
    CURRENCY_ID_MAPPING,
    SUPPORTED_CORRIDORS,
    PAYMENT_METHODS,
    DELIVERY_METHODS,
    update_country_currency_mapping,
)

logger = logging.getLogger(__name__)


class MukuruProvider(RemittanceProvider):
    """
    Mukuru integration for retrieving fees, exchange rates, and quotes.
    """

    BASE_URL = "https://mobile.mukuru.com"
    PRICECHECKER_CALCULATE_PATH = "/pricechecker/calculate"
    PRICECHECKER_COUNTRIES_PATH = "/pricechecker/get_recipient_countries"
    
    # Import mappings from mapping.py
    COUNTRY_TO_CURRENCY = COUNTRY_TO_CURRENCY
    SUPPORTED_CORRIDORS = SUPPORTED_CORRIDORS
    CURRENCY_ID_MAPPING = CURRENCY_ID_MAPPING
    PAYMENT_METHODS = PAYMENT_METHODS
    DELIVERY_METHODS = DELIVERY_METHODS

    def __init__(self, name="mukuru", **kwargs):
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

        self._supported_countries = None

    def standardize_response(self, local_data: Dict[str, Any], provider_specific_data: bool = False) -> Dict[str, Any]:
        final_exchange_rate = local_data.get("exchange_rate")
        final_rate = local_data.get("rate")
        if final_rate is None:
            final_rate = final_exchange_rate
        
        final_target_currency = local_data.get("target_currency") or local_data.get("receive_currency", "")

        response = {
            "provider_id": self.name,
            "success": local_data.get("success", False),
            "error_message": local_data.get("error_message"),
            
            "send_amount": local_data.get("send_amount", 0.0),
            "source_currency": (local_data.get("send_currency") or "").upper(),
            
            "destination_amount": local_data.get("receive_amount"),
            "destination_currency": (local_data.get("receive_currency") or "").upper(),
            
            "exchange_rate": final_exchange_rate,
            "fee": local_data.get("fee", 0.0),
            "payment_method": local_data.get("payment_method"),
            "delivery_method": local_data.get("delivery_method"),
            
            "delivery_time_minutes": local_data.get("delivery_time_minutes"),
            "timestamp": local_data.get("timestamp"),
            "rate": final_rate,
            "target_currency": final_target_currency.upper(),
        }

        if provider_specific_data and "raw_response" in local_data:
            response["raw_response"] = local_data["raw_response"]

        return response

    def get_supported_countries(self) -> Dict[str, str]:
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
            
            data = resp.json()
            if data.get("status") != "success":
                logger.error("Mukuru /get_recipient_countries returned non-success")
                self._supported_countries = {}
                return {}
            
            # Extract the country data from the API response
            country_data = data.get("data", {})
            
            # Update our mapping with the latest data from the API
            self._supported_countries = update_country_currency_mapping(country_data)
            
            return self._supported_countries
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error fetching Mukuru countries: {str(e)}")
            raise MukuruConnectionError(f"Failed to connect to Mukuru API: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            raise MukuruResponseError(f"Failed to parse JSON response: {str(e)}")

    def get_currency_id(self, from_country: str, to_country: str, delivery_method: str = None) -> int:
        """
        Get the appropriate currency ID for the given corridor and delivery method.
        
        Args:
            from_country: Source country code
            to_country: Destination country code
            delivery_method: Optional delivery method (cash, wallet, bank)
            
        Returns:
            The currency ID to use in the API request
        """
        # Normalize the delivery method to lowercase if provided
        method = delivery_method.lower() if delivery_method else None
        
        # First try with the specific delivery method
        if method:
            corridor_id = self.CURRENCY_ID_MAPPING.get((from_country, to_country, method))
            if corridor_id is not None:
                return corridor_id
        
        # Then try the general corridor
        corridor_id = self.CURRENCY_ID_MAPPING.get((from_country, to_country))
        
        # If still not found, use default USD Cash for Zimbabwe (18) or default (1)
        if corridor_id is None:
            if to_country == 'ZW':
                logger.warning(f"No currency ID for {from_country}->{to_country}, using default USD Cash (18)")
                corridor_id = 18
            else:
                logger.warning(f"No currency ID for {from_country}->{to_country}, using default (1)")
                corridor_id = 1
                
        return corridor_id

    def _get_exchange_rate_data(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        from_country_code: str = "ZA",
        delivery_method: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        local_result = {
            "success": False,
            "send_amount": float(send_amount),
            "send_currency": send_currency.upper(),
            "receive_amount": None,
            "receive_currency": None,
            "exchange_rate": None,
            "fee": 0.0,
            "error_message": None,
            "timestamp": datetime.now().isoformat()
        }

        corridor_id = self.get_currency_id(from_country_code, receive_country, delivery_method)
        
        url = self.BASE_URL + self.PRICECHECKER_CALCULATE_PATH
        params = {
            "from_currency_iso": send_currency,
            "payin_amount": str(send_amount),
            "from_country": from_country_code,
            "to_currency_iso": "",
            "payout_amount": "",
            "to_country": receive_country,
            "currency_id": corridor_id,
            "active_input": "payin_amount",
            "brand_id": 1,
            "sales_channel": "mobi",
        }
        
        logger.info(f"Requesting Mukuru exchange rate with {params}")
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            if data.get("status") != "success":
                error_msg = f"Non-success from Mukuru: {data}"
                logger.error(error_msg)
                local_result["error_message"] = error_msg
                return local_result

            quote_data = data.get("data", {})
            breakdown = quote_data.get("breakdown", {})

            rate_str = breakdown.get("Rate", "")
            exchange_rate = None
            r_match = re.search(r"R(\d+(\.\d+)?)", rate_str)
            if r_match:
                zar_per_unit = float(r_match.group(1))
                if zar_per_unit != 0:
                    exchange_rate = 1.0 / zar_per_unit

            payin_info = breakdown.get("payin", {})
            fee_str = payin_info.get("Charge", "")
            fee_val = 0.0
            f_match = re.search(r"(\d+(\.\d+)?)", fee_str)
            if f_match:
                fee_val = float(f_match.group(1))

            payout_info = breakdown.get("payout", {})
            receive_str = payout_info.get("They receive", "")
            rx_match = re.search(r"(\d+(\.\d+)?)", receive_str)
            rx_val = 0.0
            if rx_match:
                rx_val = float(rx_match.group(1))

            currency_match = re.search(r"([A-Z]{3})", receive_str)
            rcur = None
            if currency_match:
                rcur = currency_match.group(1)

            local_result.update({
                "success": True,
                "exchange_rate": exchange_rate,
                "receive_amount": rx_val,
                "fee": fee_val,
                "receive_currency": rcur if rcur else None,
            })

        except requests.exceptions.RequestException as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            local_result["error_message"] = error_msg
        except json.JSONDecodeError as e:
            error_msg = f"JSON parse error: {str(e)}"
            logger.error(error_msg)
            local_result["error_message"] = error_msg

        return local_result

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        target_country: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for sending money from source_currency to target_country.
        
        Args:
            amount: The amount to send
            source_currency: The currency to send from (e.g. "USD")
            target_country: The country to send to (e.g. "KE")
            **kwargs: Additional parameters including from_country_code
            
        Returns:
            Standardized response with exchange rate, fees, and delivery options
        """
        # Ensure we have data to work with
        if not amount or not source_currency or not target_country:
            raise ValueError("Missing required parameters for Mukuru quote")
            
        # Extract from_country_code from kwargs if available
        from_country_code = kwargs.pop('from_country', None) or kwargs.pop('from_country_code', None)
        
        # If not explicitly provided, try to determine from source_currency
        if not from_country_code:
            # Try to derive country from currency
            country_mapping = self.COUNTRY_TO_CURRENCY
            
            # Look up country code based on currency
            for cc, cur in country_mapping.items():
                if cur.upper() == source_currency.upper():
                    from_country_code = cc
                    break
                    
            # Default to South Africa if no match found
            if not from_country_code:
                # Common currency mappings for major source countries
                currency_to_country = {
                    "USD": "US",
                    "GBP": "GB",
                    "EUR": "DE",  # Default to Germany for Euro
                    "ZAR": "ZA",
                    "CAD": "CA",
                    "AUD": "AU"
                }
                from_country_code = currency_to_country.get(source_currency.upper(), "ZA")

        # Call the exchange rate data method without duplicating from_country_code
        # since it's now passed as a named parameter
        local_result = self._get_exchange_rate_data(
            send_amount=amount,
            send_currency=source_currency,
            receive_country=target_country,
            from_country_code=from_country_code,
            delivery_method=kwargs.get("delivery_method")
            # Do NOT pass **kwargs here to avoid parameter duplication
        )

        if kwargs.get("include_raw", False):
            local_result["raw_response"] = dict(local_result)

        return self.standardize_response(local_result, provider_specific_data=kwargs.get("include_raw", False))

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get exchange rate from send_currency to receive_country.
        
        Args:
            send_amount: The amount to send
            send_currency: The currency to send from (e.g. "USD")
            receive_country: The country to send to (e.g. "KE")
            
        Returns:
            Response containing exchange rate data
        """
        # Extract from_country_code from kwargs to avoid duplicate parameters
        from_country_code = kwargs.pop('from_country', None) or kwargs.pop('from_country_code', None)
        
        # Similar currency-to-country mapping as in get_quote
        if not from_country_code:
            currency_to_country = {
                "USD": "US",
                "GBP": "GB",
                "EUR": "DE",
                "ZAR": "ZA",
                "CAD": "CA",
                "AUD": "AU"
            }
            from_country_code = currency_to_country.get(send_currency.upper(), "ZA")
        
        local_result = self._get_exchange_rate_data(
            send_amount=send_amount,
            send_currency=send_currency,
            receive_country=receive_country,
            from_country_code=from_country_code,
            delivery_method=kwargs.get("delivery_method")
            # Again, don't pass the full **kwargs to avoid duplication
        )

        if kwargs.get("include_raw", False):
            local_result["raw_response"] = dict(local_result)

        return self.standardize_response(local_result, provider_specific_data=kwargs.get("include_raw", False))