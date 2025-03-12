"""
Sendwave (Wave) Integration

This module integrates with Sendwave's public endpoint to retrieve
pricing and quote information for remittances.
"""

import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

# Import base provider
from apps.providers.base.provider import RemittanceProvider

# Import Sendwave (Wave) custom exceptions
from apps.providers.sendwave.exceptions import (
    SendwaveApiError,
    SendwaveConnectionError,
    SendwaveCorridorUnsupportedError,
    SendwaveError,
    SendwaveResponseError,
    SendwaveValidationError,
)

# Import Sendwave-specific mappings
from apps.providers.sendwave.sendwave_mappings import (
    API_CONFIG,
    COUNTRY_DELIVERY_METHODS,
    DEFAULT_VALUES,
    SUPPORTED_CORRIDORS,
    get_delivery_methods_for_country,
    get_segment_name_for_delivery_method,
    get_send_country_for_currency,
)
from apps.providers.sendwave.sendwave_mappings import (
    is_corridor_supported as is_sendwave_corridor_supported,
)

# Import utility functions for standardized country and currency mappings
from apps.providers.utils.country_currency_standards import (
    get_default_currency_for_country,
    normalize_country_code,
)

logger = logging.getLogger(__name__)


class SendwaveProvider(RemittanceProvider):
    """
    Aggregator-ready Sendwave provider integration.

    - No fallback/mock data: if the API call fails or corridor is unsupported,
      returns success=False plus an error_message.
    - On success, returns aggregator-standard quote fields:
      provider_id, success, error_message,
      send_amount, source_currency,
      destination_amount, destination_currency,
      exchange_rate, fee,
      payment_method, delivery_method,
      delivery_time_minutes, timestamp, etc.

    Usage:
        wave = SendwaveProvider()
        quote = wave.get_quote(
            amount=Decimal("500"),
            source_currency="USD",
            dest_country="PH",   # e.g. Philippines
            source_country="US", # if needed
        )
    """

    # Base URL for Sendwave's public pricing
    BASE_URL = API_CONFIG["base_url"]
    PRICING_ENDPOINT = API_CONFIG["pricing_endpoint"]

    # If aggregator uses corridor checks:
    SUPPORTED_CORRIDORS = SUPPORTED_CORRIDORS

    # Mapping of country codes to available delivery methods
    # These are Sendwave-specific and not part of standard mappings
    COUNTRY_DELIVERY_METHODS = COUNTRY_DELIVERY_METHODS

    DEFAULT_USER_AGENT = API_CONFIG["default_user_agent"]

    # Default aggregator fields for payment/delivery if not specified
    DEFAULT_PAYMENT_METHOD = DEFAULT_VALUES["payment_method"]
    DEFAULT_DELIVERY_METHOD = DEFAULT_VALUES["delivery_method"]
    DEFAULT_DELIVERY_TIME = DEFAULT_VALUES["delivery_time_minutes"]

    def __init__(self, name="sendwave", base_url: Optional[str] = None):
        """
        Initialize Sendwave provider for the aggregator.

        Args:
            name: Provider identifier
            base_url: Optional URL override
        """
        super().__init__(name=name, base_url=base_url or self.BASE_URL)
        self.session = requests.Session()
        # Basic headers for a browser-like request
        self.session.headers.update(
            {
                "User-Agent": self.DEFAULT_USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Origin": API_CONFIG["origin"],
                "Referer": API_CONFIG["referer"],
            }
        )
        self.logger = logging.getLogger(f"providers.{name}")

    def standardize_response(
        self, raw_result: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Convert local result dictionary into aggregator's standard shape.

        Args:
            raw_result: Provider-specific response
            provider_specific_data: Whether to include raw provider data

        Returns:
            Standardized response dictionary
        """
        now_ts = datetime.utcnow().isoformat()
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
            "delivery_time_minutes": raw_result.get(
                "delivery_time_minutes", self.DEFAULT_DELIVERY_TIME
            ),
            "timestamp": raw_result.get("timestamp", now_ts),
        }

        # Ensure delivery methods are preserved if present
        if "available_delivery_methods" in raw_result:
            self.logger.debug(
                f"Preserving {len(raw_result['available_delivery_methods'])} delivery methods in standardized response"
            )
            output["available_delivery_methods"] = raw_result["available_delivery_methods"]

        # Preserve promotions if present
        if "promotions" in raw_result and raw_result["promotions"]:
            output["promotions"] = raw_result["promotions"]

        # Optionally include raw response or other details
        if provider_specific_data and "raw_data" in raw_result:
            output["raw_response"] = raw_result["raw_data"]

        return output

    def is_corridor_supported(self, send_currency: str, receive_country: str) -> bool:
        """
        Check if a corridor is in our SUPPORTED_CORRIDORS list.

        Args:
            send_currency: Source currency code (e.g., "USD")
            receive_country: Destination country code (e.g., "PH")

        Returns:
            True if the corridor is supported
        """
        # Normalize the country code first
        receive_country = normalize_country_code(receive_country)
        return is_sendwave_corridor_supported(send_currency, receive_country)

    def get_supported_countries(self, base_currency: str = None) -> List[str]:
        """
        Return a list of receiving countries we know are supported,
        optionally filtered by base_currency.

        Args:
            base_currency: Optional currency filter (e.g., "USD")

        Returns:
            List of supported country codes
        """
        if base_currency is None:
            # Return all
            return sorted(set(c for (cur, c) in self.SUPPORTED_CORRIDORS))
        else:
            return sorted(
                c for (cur, c) in self.SUPPORTED_CORRIDORS if cur == base_currency.upper()
            )

    def get_supported_currencies(self) -> List[str]:
        """
        Return list of supported source currencies.

        Returns:
            List of currency codes
        """
        return sorted(set(cur for (cur, c) in self.SUPPORTED_CORRIDORS))

    def _get_receive_currency(self, country_code: str) -> str:
        """
        Return the currency for a given receive country code using standard mappings.

        Args:
            country_code: Two-letter country code (e.g., "PH")

        Returns:
            Currency code (e.g., "PHP")
        """
        # Use the standardized function for country to currency mapping
        normalized_country = normalize_country_code(country_code)
        currency = get_default_currency_for_country(normalized_country)

        # If no mapping found, log a warning but don't fail - try to proceed with API call
        if not currency:
            self.logger.warning(f"No standard currency mapping found for country {country_code}")
            # If API requires this, we can make an educated guess for common countries
            if normalized_country == "PH":
                return "PHP"
            elif normalized_country == "KE":
                return "KES"
            elif normalized_country == "UG":
                return "UGX"
            elif normalized_country == "GH":
                return "GHS"

        return currency or "USD"  # Default to USD if nothing else found

    def _get_delivery_methods_for_country(self, country_code: str) -> List[Dict[str, Any]]:
        """
        Get available delivery methods for a specific country.

        Args:
            country_code: Two-letter country code (e.g., "PH")

        Returns:
            List of delivery method dictionaries
        """
        normalized_country = normalize_country_code(country_code)
        return get_delivery_methods_for_country(normalized_country)

    def _get_send_country_iso2(self, source_currency: str, source_country: str = None) -> str:
        """
        Get the appropriate sender country ISO code based on source currency.

        Args:
            source_currency: Source currency code (e.g., "USD", "EUR")
            source_country: Optional source country code to override defaults

        Returns:
            Lower case ISO2 country code
        """
        if source_country:
            return normalize_country_code(source_country).lower()

        return get_send_country_for_currency(source_currency, None)

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        dest_country: str,
        source_country: str = None,
        payment_method: str = None,
        delivery_method: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Aggregator-standard method returning a quote dictionary.
        No fallback data: if the request fails or corridor is unsupported,
        returns success=False plus error_message.

        Args:
            amount: Decimal amount to send
            source_currency: Source currency code (e.g., "USD")
            dest_country: Destination country code (e.g., "PH")
            source_country: Source country code (e.g., "US")
            payment_method: Payment method (e.g., "debitCard")
            delivery_method: Delivery method (e.g., "mobileWallet")
            **kwargs: Additional parameters

        Returns:
            Standardized quote dictionary
        """
        # Use defaults if not provided
        if payment_method is None:
            payment_method = self.DEFAULT_PAYMENT_METHOD
        if delivery_method is None:
            delivery_method = self.DEFAULT_DELIVERY_METHOD

        # Normalize country codes
        normalized_dest_country = normalize_country_code(dest_country)

        # Start with a base result template
        base_result = {
            "success": False,
            "error_message": None,
            "send_amount": float(amount),
            "source_currency": source_currency.upper(),
            "destination_currency": "",  # We'll fill after we determine it
            "payment_method": payment_method,
            "delivery_method": delivery_method,
            "delivery_time_minutes": self.DEFAULT_DELIVERY_TIME,
        }

        # Corridor check
        if not self.is_corridor_supported(source_currency.upper(), normalized_dest_country):
            msg = f"Corridor not supported: {source_currency}->{normalized_dest_country}"
            self.logger.warning(msg)
            base_result["error_message"] = msg
            return self.standardize_response(base_result)

        # Derive the receiving currency from the country code
        receive_currency = self._get_receive_currency(normalized_dest_country)
        base_result["destination_currency"] = receive_currency

        # Get available delivery methods for this country
        available_delivery_methods = self._get_delivery_methods_for_country(normalized_dest_country)
        if available_delivery_methods:
            base_result["available_delivery_methods"] = available_delivery_methods

            # Try to find the appropriate segment name for the API call
            segment_name = kwargs.get(
                "segment_name",
                get_segment_name_for_delivery_method(normalized_dest_country, delivery_method),
            )
        else:
            # Build a default segment name if needed
            segment_name = kwargs.get("segment_name", "")
            if not segment_name and normalized_dest_country.upper() == "PH":
                segment_name = "ph_gcash"
            elif not segment_name and normalized_dest_country.upper() == "KE":
                segment_name = "ke_mpesa"

        # Build the request to Sendwave's public endpoint
        endpoint_url = f"{self.base_url}{self.PRICING_ENDPOINT}"

        # Attempt to guess sendCountryIso2 from the source currency
        # If aggregator didn't pass one, default to appropriate country based on currency
        send_country_iso2 = kwargs.get(
            "send_country_iso2",
            self._get_send_country_iso2(source_currency, source_country),
        )

        # Build the query parameters
        params = {
            "amountType": "SEND",
            "receiveCurrency": receive_currency,
            "segmentName": segment_name,
            "amount": str(float(amount)),
            "sendCurrency": source_currency.upper(),
            "sendCountryIso2": send_country_iso2.lower(),
            "receiveCountryIso2": normalized_dest_country.lower(),
        }

        # Make the API call
        try:
            self.logger.debug(f"Sending request to {endpoint_url} with params: {params}")
            resp = self.session.get(endpoint_url, params=params, timeout=API_CONFIG["timeout"])
            resp.raise_for_status()
        except requests.HTTPError as exc:
            msg = f"HTTP error from Sendwave: {exc}"
            self.logger.error(msg, exc_info=True)
            base_result["error_message"] = msg
            return self.standardize_response(base_result)
        except requests.ConnectionError as exc:
            msg = f"Connection error to Sendwave: {exc}"
            self.logger.error(msg, exc_info=True)
            base_result["error_message"] = msg
            return self.standardize_response(base_result)
        except Exception as e:
            msg = f"Unexpected error calling Sendwave: {e}"
            self.logger.error(msg, exc_info=True)
            base_result["error_message"] = msg
            return self.standardize_response(base_result)

        # Parse response JSON
        try:
            data = resp.json()
            self.logger.debug(f"Received response: {data}")
        except ValueError as ve:
            msg = f"Invalid JSON from Sendwave: {ve}"
            self.logger.error(msg, exc_info=True)
            base_result["error_message"] = msg
            return self.standardize_response(base_result)

        # Check mandatory fields
        if "effectiveExchangeRate" not in data or "effectiveSendAmount" not in data:
            msg = "Missing required fields in Sendwave response (effectiveExchangeRate / effectiveSendAmount)"
            self.logger.error(msg)
            base_result["error_message"] = msg
            return self.standardize_response(base_result)

        # Extract relevant info
        try:
            exchange_rate = float(data["effectiveExchangeRate"])
            fee = float(data.get("effectiveFeeAmount", 0.0))
            send_amount_float = float(data["effectiveSendAmount"])
            receive_amount = send_amount_float * exchange_rate
        except (TypeError, ValueError) as parse_err:
            msg = f"Error parsing numeric fields from Sendwave response: {parse_err}"
            self.logger.error(msg)
            base_result["error_message"] = msg
            return self.standardize_response(base_result)

        # Extract any promotions
        promotions = []
        if "campaignsApplied" in data and data["campaignsApplied"]:
            for campaign in data["campaignsApplied"]:
                promotions.append(
                    {
                        "code": campaign.get("code", ""),
                        "description": campaign.get("description", ""),
                        "value": campaign.get("sendCurrencyValue", "0"),
                    }
                )
            self.logger.debug(f"Extracted {len(promotions)} promotions from Sendwave response")

        # Mark success and finalize result
        base_result.update(
            {
                "success": True,
                "exchange_rate": exchange_rate,
                "fee": fee,
                "destination_amount": receive_amount,
                "promotions": promotions,
                "raw_data": data,
            }
        )

        self.logger.info(
            f"Sendwave quote success: {amount} {source_currency} → {receive_amount} {receive_currency} "
            f"(rate={exchange_rate}, fee={fee})"
        )

        return self.standardize_response(base_result, provider_specific_data=True)

    def get_exchange_rate(
        self, send_amount: Decimal, send_currency: str, receive_country: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy aggregator method. For consistency, just call get_quote
        with matching parameters.

        Args:
            send_amount: Amount to send
            send_currency: Source currency code
            receive_country: Destination country code
            **kwargs: Additional parameters

        Returns:
            Standardized quote dictionary
        """
        return self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            dest_country=receive_country,
            **kwargs,
        )

    def close(self):
        """Close the session when done."""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Legacy class name for backward compatibility
class WaveProvider(SendwaveProvider):
    """Legacy class name for backward compatibility."""

    pass
