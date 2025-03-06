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

# Import the base provider class
from apps.providers.base.provider import RemittanceProvider
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
    Aggregator-ready Mukuru integration. 
    Fetches exchange rates, fees, and supported corridors from Mukuru endpoints,
    returning standardized aggregator responses.
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
        ('ZA', 'ZW'),  # South Africa -> Zimbabwe
        ('ZA', 'GH'),  # South Africa -> Ghana
        ('ZA', 'NG'),  # South Africa -> Nigeria
        ('ZA', 'MZ'),  # South Africa -> Mozambique
        ('ZA', 'MW'),  # South Africa -> Malawi
    ]
    
    # Example: currency ID mapping for specific corridors (if used internally)
    CURRENCY_ID_MAPPING = {
        ('ZA', 'ZW'): 18,  # For ZAR -> USD (Zimbabwe)
        ('ZA', 'GH'): 20,  # Example ID for Ghana
        ('ZA', 'NG'): 21,  # Example ID for Nigeria
        # ...
    }

    def __init__(self, name="mukuru", **kwargs):
        """Initialize the Mukuru provider in aggregator-friendly mode."""
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

        # Cache for supported countries
        self._supported_countries = None

    # ------------------------------------------------------------------------
    # Aggregator-specific helper: standardize the response
    # ------------------------------------------------------------------------
    def standardize_response(self, local_data: Dict[str, Any], provider_specific_data: bool = False) -> Dict[str, Any]:
        """
        Convert local fields into aggregator-friendly keys:
          - 'provider_id', 'success', 'error_message'
          - 'send_amount', 'source_currency'
          - 'destination_amount', 'destination_currency'
          - 'exchange_rate', 'fee'
          - 'delivery_time_minutes', 'timestamp'
        
        Also includes aggregator keys 'rate' (mirroring exchange_rate) 
        and 'target_currency' (mirroring destination_currency).
        """
        # aggregator might want "rate" specifically
        final_exchange_rate = local_data.get("exchange_rate")
        final_rate = local_data.get("rate")
        if final_rate is None:
            final_rate = final_exchange_rate
        
        # aggregator might want "target_currency" specifically
        final_target_currency = local_data.get("target_currency") or local_data.get("receive_currency", "")

        # Build aggregator output
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
            
            # aggregator might ask for "delivery_time_minutes" if known
            "delivery_time_minutes": local_data.get("delivery_time_minutes"),
            
            # aggregator might want a "timestamp" for the quote
            "timestamp": local_data.get("timestamp"),
            
            # aggregator might specifically look for "rate" (mirroring exchange_rate)
            "rate": final_rate,
            
            # aggregator might specifically want "target_currency"
            "target_currency": final_target_currency.upper(),
        }

        # optionally attach raw response
        if provider_specific_data and "raw_response" in local_data:
            response["raw_response"] = local_data["raw_response"]

        return response

    # ------------------------------------------------------------------------
    # Public aggregator-like methods
    # ------------------------------------------------------------------------
    def get_supported_countries(self) -> Dict[str, str]:
        """
        Retrieve recipient countries from Mukuru's endpoint.
        
        Returns:
            A dict mapping country codes to currency codes.
        """
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
            
            result = {}
            for ccode, info in data.get("data", {}).items():
                currency_iso = info.get("currency_market_iso")
                result[ccode] = currency_iso
            
            self._supported_countries = result
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error fetching Mukuru countries: {str(e)}")
            raise MukuruConnectionError(f"Failed to connect to Mukuru API: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            raise MukuruResponseError(f"Failed to parse JSON response: {str(e)}")

    def get_currency_id(self, from_country: str, to_country: str) -> int:
        """
        Optional: Get a corridor-specific currency ID for internal usage.
        Fallback to a default if not found.
        """
        corridor_id = self.CURRENCY_ID_MAPPING.get((from_country, to_country))
        if corridor_id is None:
            logger.warning(f"No currency ID for {from_country}->{to_country}, fallback 18")
            corridor_id = 18  # e.g., default to ZW corridor
        return corridor_id

    def _get_exchange_rate_data(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        from_country_code: str = "ZA",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Internal method that calls Mukuru's /pricechecker/calculate
        and returns local dictionary of aggregator-like keys (not yet fully standardized).
        """
        # create a minimal local result
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

        # get corridor currency ID if needed
        corridor_id = self.get_currency_id(from_country_code, receive_country)
        
        url = self.BASE_URL + self.PRICECHECKER_CALCULATE_PATH
        params = {
            "from_currency_iso": send_currency,   # e.g. 'ZAR'
            "payin_amount": str(send_amount),     # e.g. '900'
            "from_country": from_country_code,    # e.g. 'ZA'
            "to_currency_iso": "",
            "payout_amount": "",
            "to_country": receive_country,        # e.g. 'ZW'
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

            # Parse data
            quote_data = data.get("data", {})
            breakdown = quote_data.get("breakdown", {})

            rate_str = breakdown.get("Rate", "")  # e.g. "$1:R18.7248"
            exchange_rate = None
            # parse e.g. "R18.7248"
            r_match = re.search(r"R(\d+(\.\d+)?)", rate_str)
            if r_match:
                zar_per_unit = float(r_match.group(1))  # e.g. 18.7248
                if zar_per_unit != 0:
                    # if corridor is ZAR->USD, we interpret "R18.72 = $1" => exchange_rate=1/18.72=0.053
                    exchange_rate = 1.0 / zar_per_unit

            # parse fee
            payin_info = breakdown.get("payin", {})
            fee_str = payin_info.get("Charge", "")  # e.g. "ZAR94.00"
            fee_val = 0.0
            f_match = re.search(r"(\d+(\.\d+)?)", fee_str)
            if f_match:
                fee_val = float(f_match.group(1))

            # parse receive amount from "They receive"
            payout_info = breakdown.get("payout", {})
            receive_str = payout_info.get("They receive", "")  # e.g. "USD50.00"
            rx_match = re.search(r"(\d+(\.\d+)?)", receive_str)
            rx_val = 0.0
            if rx_match:
                rx_val = float(rx_match.group(1))

            # parse currency code from "They receive"
            currency_match = re.search(r"([A-Z]{3})", receive_str)
            rcur = None
            if currency_match:
                rcur = currency_match.group(1)

            # update local result
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
        Aggregator: get a quote for sending `amount` in `source_currency` 
        to `target_country` via Mukuru. Returns aggregator-standard keys.
        """
        # Attempt to deduce from_country_code from source_currency if not in kwargs
        from_country_code = kwargs.get("from_country_code")
        if not from_country_code:
            # try matching country in COUNTRY_TO_CURRENCY
            for cc, cur in self.COUNTRY_TO_CURRENCY.items():
                if cur.upper() == source_currency.upper():
                    from_country_code = cc
                    break
            if not from_country_code:
                from_country_code = "ZA"  # fallback to South Africa

        # call internal method
        local_result = self._get_exchange_rate_data(
            send_amount=amount,
            send_currency=source_currency,
            receive_country=target_country,
            from_country_code=from_country_code,
            **kwargs
        )

        # optionally store raw response
        if kwargs.get("include_raw", False):
            local_result["raw_response"] = dict(local_result)  # shallow copy or store something else

        return self.standardize_response(local_result, provider_specific_data=kwargs.get("include_raw", False))

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Aggregator: get exchange rate for a corridor (similar to get_quote).
        Some aggregator tests specifically look for "rate" instead of "exchange_rate".
        """
        local_result = self._get_exchange_rate_data(
            send_amount=send_amount,
            send_currency=send_currency,
            receive_country=receive_country,
            **kwargs
        )
        # aggregator might not need fee or amounts for a pure "exchange rate" call,
        # but we'll keep them
        # store raw if needed
        if kwargs.get("include_raw", False):
            local_result["raw_response"] = dict(local_result)

        # aggregator might specifically want "rate" in the result
        # we can either rename exchange_rate => rate or just rely on standardize_response
        return self.standardize_response(local_result, provider_specific_data=kwargs.get("include_raw", False)) 