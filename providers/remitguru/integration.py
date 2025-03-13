"""
RemitGuru Money Transfer Integration

This module implements the integration with RemitGuru, a digital money transfer service
that offers competitive rates for international remittances.

The integration uses RemitGuru's public API to fetch exchange rates and fees
for international money transfers.
"""

import datetime
import json
import logging
import time
from decimal import Decimal
from decimal import InvalidOperation as DecimalException
from typing import Any, Dict, List, Optional, Tuple

import requests

from providers.base.provider import RemittanceProvider
from providers.utils.country_currency_standards import (
    normalize_country_code,
    validate_corridor,
)
from providers.utils.currency_mapping import get_country_currencies

# Setup logging
logger = logging.getLogger(__name__)


class RemitGuruProvider(RemittanceProvider):
    """
    Aggregator-ready RemitGuru integration without mock data.

    This provider fetches quotes (exchange rates, fees) from RemitGuru's
    public API for specific corridors. If an error or unsupported corridor
    is encountered, it returns an error response instead of fallback data.

    NOTE: RemitGuru currently only supports money transfers from UK (GBP) to India (IN).
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
    CURRENCY_MAPPING = {
        "GB": "GBP",  # United Kingdom - British Pound
        "UK": "GBP",  # Alternative code for United Kingdom
        "IN": "INR",  # India - Indian Rupee
    }

    # IMPORTANT: RemitGuru only supports these corridors
    SUPPORTED_CORRIDORS = [
        ("GB", "IN"),  # UK to India
        ("UK", "IN"),  # UK to India (alternate country code)
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
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
                ),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*",
                "Origin": self.BASE_URL,
                "Referer": f"{self.BASE_URL}/send-money-UK-to-India",
                "Connection": "keep-alive",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )
        self.logger = logging.getLogger(f"providers.{name}")
        self._visit_homepage()

    def standardize_response(
        self, raw_result: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Standardize the response shape for aggregator consumption.

        Args:
            raw_result: Raw provider response
            provider_specific_data: Whether to include provider-specific data

        Returns:
            Standardized response dictionary
        """
        logger.debug(f"RemitGuru standardize_response input: {raw_result}")

        # Initialize standard response structure
        response = {
            "provider_id": "remitguru",
            "provider_name": "RemitGuru",
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),
            "source_country": raw_result.get("source_country", "GB"),  # Default to GB
            "destination_country": raw_result.get("destination_country", "IN"),  # Default to IN
            "source_currency": raw_result.get("source_currency", "GBP"),
            "destination_currency": raw_result.get("destination_currency", "INR"),
            "source_amount": raw_result.get("send_amount", 0.0),
            "destination_amount": raw_result.get("destination_amount", 0.0),
            "exchange_rate": raw_result.get("exchange_rate", 0.0),
            "fee": raw_result.get("fee", 0.0),
            "payment_method": raw_result.get("payment_method", self.DEFAULT_PAYMENT_METHOD),
            "delivery_method": raw_result.get("delivery_method", self.DEFAULT_DELIVERY_METHOD),
            "delivery_time_minutes": raw_result.get(
                "delivery_time_minutes", self.DEFAULT_DELIVERY_TIME
            ),
            "timestamp": raw_result.get("timestamp", datetime.datetime.now().isoformat()),
        }

        # Include raw response if requested
        if provider_specific_data and "raw_response" in raw_result:
            response["raw_response"] = raw_result["raw_response"]

        logger.debug(f"RemitGuru standardize_response output: {response}")
        return response

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
        self,
        send_country: str,
        send_currency: str,
        recv_country: str,
        recv_currency: str,
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
        self, send_amount: Decimal, send_country_code: str, recv_country_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Request a quote from RemitGuru for a given corridor and amount.

        Args:
            send_amount: Decimal, amount to send
            send_country_code: Source country code (e.g., "GB" or "UK")
            recv_country_code: Destination country code (e.g., "IN")

        Returns:
            Parsed response dict or None if an error occurs
        """
        # Only GB/UK to IN is supported
        if send_country_code not in ["GB", "UK"] or recv_country_code != "IN":
            logger.error(
                f"RemitGuru only supports GB/UK to IN corridor, got: {send_country_code} -> {recv_country_code}"
            )
            return None

        # Hardcode the corridor for UK/GB to India which is the only supported one
        corridor_str = "GB~GBP~IN~INR"

        # Format the amount as a whole number as required by the API
        amount_int = int(send_amount)

        payload = {
            "amountTransfer": str(amount_int),
            "corridor": corridor_str,
            "sendMode": "CIP-FER",
        }

        url = f"{self.BASE_URL}{self.QUOTE_ENDPOINT}"
        try:
            logger.debug(f"Requesting RemitGuru quote with payload: {payload}")
            resp = self.session.post(url, data=payload, timeout=30)

            content = resp.text.strip()
            logger.debug(f"RemitGuru raw response: {content}")

            # Check if the response is empty
            if not content:
                logger.error("Empty response from RemitGuru")
                return None

            # Example successful response: "128115.68|103.99|0.00|1232.00||true|GBP|"
            # Format: receive_amount|exchange_rate|fee|send_amount|error_msg|valid_flag|send_currency|[error_code]
            parts = content.split("|")

            # Log the parsed parts for debugging
            logger.debug(f"RemitGuru response parsed into {len(parts)} parts: {parts}")

            if len(parts) < 6:
                logger.error(f"Invalid RemitGuru response format: {content}")
                return None

            # Parse response parts
            receive_amount_str = parts[0].strip() if parts[0].strip() else None
            rate_str = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            fee_str = parts[2].strip() if len(parts) > 2 and parts[2].strip() else "0.00"
            send_amt_str = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
            error_msg = parts[4].strip() if len(parts) > 4 and parts[4].strip() else ""
            valid_flag = (
                parts[5].strip().lower() if len(parts) > 5 and parts[5].strip() else "false"
            )
            send_cur = parts[6].strip() if len(parts) > 6 and parts[6].strip() else "GBP"

            # Debug logging
            logger.debug(
                f"RemitGuru parsed values: receive={receive_amount_str}, rate={rate_str}, fee={fee_str}, "
                f"send={send_amt_str}, error={error_msg}, valid={valid_flag}, currency={send_cur}"
            )

            # Check if the quote is valid
            is_valid = valid_flag == "true"

            # If not valid, return error info
            if not is_valid:
                error_text = error_msg or "Invalid quote"
                logger.error(f"RemitGuru invalid quote: {error_text}")
                return {"is_valid": False, "error": error_text, "raw_response": content}

            # If valid but required values are missing, treat as an error
            if is_valid and (not receive_amount_str or not rate_str):
                logger.error("RemitGuru fee not defined or missing required values")
                return {
                    "is_valid": False,
                    "error": "Fee Not Define.",
                    "raw_response": content,
                }

            # Parse numeric values, handling empty strings
            try:
                receive_amount = Decimal(receive_amount_str) if receive_amount_str else None
                exchange_rate = Decimal(rate_str) if rate_str else None
                fee = Decimal(fee_str) if fee_str else Decimal("0")
                send_amount_confirmed = Decimal(send_amt_str) if send_amt_str else send_amount

                # Success case
                return {
                    "receive_amount": receive_amount,
                    "exchange_rate": exchange_rate,
                    "fee": fee,
                    "send_amount": send_amount_confirmed,
                    "is_valid": True,
                    "send_currency": send_cur,
                    "receive_currency": "INR",
                    "raw_response": content,
                }
            except (ValueError, DecimalException) as e:
                logger.error(f"Error parsing numeric values in RemitGuru response: {e}")
                return {
                    "is_valid": False,
                    "error": f"Failed to parse response values: {e}",
                    "raw_response": content,
                }

        except requests.RequestException as exc:
            logger.error(f"RemitGuru API request failed: {exc}")
            return None
        except Exception as exc:
            logger.error(f"Unexpected error processing RemitGuru quote: {exc}")
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
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get a standardized quote for money transfer between currencies.

        This implements the abstract method from RemittanceProvider.
        """
        # Log the input parameters for debugging
        logger.debug(
            f"RemitGuru get_quote called with: amount={amount}, source_country={source_country}, "
            f"source_currency={source_currency}, dest_country={dest_country}, "
            f"dest_currency={dest_currency}"
        )

        # Normalize country codes
        source_country_original = source_country
        dest_country_original = dest_country
        source_country = normalize_country_code(source_country)
        dest_country = normalize_country_code(dest_country)

        # Special case for RemitGuru: UK is valid and maps to GB
        is_uk_to_india = (source_country == "UK" or source_country == "GB") and dest_country == "IN"

        # Skip validation for the special UK to India case
        if not is_uk_to_india:
            # Validate corridor
            is_valid, error_message = validate_corridor(
                source_country=source_country,
                source_currency=source_currency,
                dest_country=dest_country,
                dest_currency=dest_currency,
            )

            if not is_valid:
                logger.warning(f"RemitGuru corridor validation failed: {error_message}")
                return self.standardize_response(
                    {
                        "success": False,
                        "error_message": error_message,
                        "send_amount": float(amount),
                        "source_currency": source_currency.upper(),
                        "destination_currency": dest_currency.upper(),
                        "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                        "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                    }
                )
        else:
            logger.debug("RemitGuru: Special case UK/GB to India (IN) - bypassing validation")

        # Special handling for UK/GB - ensure UK is mapped to GB for internal processing
        if source_country == "UK":
            source_country = "GB"

        # Get the internal quote
        quote = self._internal_get_quote(amount, source_country, dest_country)

        if not quote:
            error_msg = "RemitGuru quote request failed or invalid response"
            logger.error(error_msg)
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": error_msg,
                    "send_amount": float(amount),
                    "source_currency": source_currency.upper(),
                    "destination_currency": dest_currency.upper(),
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )

        if not quote.get("is_valid", False):
            error_msg = quote.get("error", "Invalid corridor or unknown error")
            raw_response = quote.get("raw_response", "No raw response")
            logger.error(f"RemitGuru invalid quote: {error_msg}, raw response: {raw_response}")
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": error_msg,
                    "send_amount": float(amount),
                    "source_currency": source_currency.upper(),
                    "destination_currency": dest_currency.upper(),
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                    "raw_response": raw_response if kwargs.get("include_raw", False) else None,
                }
            )

        # Build success response
        response_data = {
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
            "timestamp": datetime.datetime.now().isoformat(),
            "raw_response": quote.get("raw_response") if kwargs.get("include_raw", False) else None,
        }

        logger.debug(f"RemitGuru quote success: {response_data}")
        response = self.standardize_response(response_data)
        logger.debug(f"RemitGuru standardized response: {response}")
        return response

    def get_exchange_rate(
        self, send_amount: Decimal, send_currency: str, target_currency: str, **kwargs
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
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Unsupported sending currency: {send_currency}",
                    "send_amount": float(send_amount),
                    "source_currency": send_currency.upper(),
                    "destination_currency": target_currency.upper(),
                }
            )

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
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Cannot determine country for currency: {target_currency}",
                    "send_amount": float(send_amount),
                    "source_currency": send_currency.upper(),
                    "destination_currency": target_currency.upper(),
                }
            )

        # Call standardized get_quote method
        return self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            dest_currency=target_currency,
            source_country=send_country_code,
            dest_country=recv_country_code,
            payment_method=kwargs.get("payment_method"),
            delivery_method=kwargs.get("delivery_method"),
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
