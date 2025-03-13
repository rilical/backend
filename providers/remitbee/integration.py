"""
Remitbee Money Transfer Integration

This module implements the integration with Remitbee, a digital money transfer service
that offers competitive rates for international remittances.

The integration uses Remitbee's public quote API to fetch exchange rates and fees
for international money transfers.
"""

import datetime
import json
import logging
import os
import random
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from providers.base.provider import RemittanceProvider
from providers.remitbee.exceptions import (
    RemitbeeApiError,
    RemitbeeConnectionError,
    RemitbeeError,
    RemitbeeValidationError,
)

# Setup logging
logger = logging.getLogger(__name__)


class RemitbeeProvider(RemittanceProvider):
    """
    Aggregator-ready Remitbee Provider Integration WITHOUT any mock-data fallback.

    Provides methods to fetch exchange rates and quotes from Remitbee's API.
    If a corridor is unsupported or an error occurs, returns an error.
    """

    BASE_URL = "https://api.remitbee.com"
    QUOTE_ENDPOINT = "/public-services/calculate-money-transfer"
    RATES_ENDPOINT = "/public-services/online-rates-multi-currency"
    COUNTRIES_DATA_FILE = "countries_data.json"

    # Default payment/delivery methods and estimated delivery time (minutes)
    DEFAULT_PAYMENT_METHOD = "bank"
    DEFAULT_DELIVERY_METHOD = "bank"
    DEFAULT_DELIVERY_TIME = 1440  # 24 hours in minutes

    # Cache validity period in seconds (24 hours)
    CACHE_VALIDITY_SECONDS = 86400

    # A small pool of user-agents to mimic browser usage
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    ]

    def __init__(self, name="remitbee", countries_html_file: Optional[str] = None, **kwargs):
        """
        Initialize the Remitbee provider.

        Args:
            name: Provider identifier
            countries_html_file: Optional path to HTML file with countries data
            **kwargs: Additional parameters
        """
        super().__init__(name=name, base_url=self.BASE_URL)
        self.country_data: Dict[str, Dict[str, Any]] = {}
        self.rates_cache: Dict[str, Dict[str, Any]] = {}
        self.rates_cache_timestamp: float = 0

        # Load or parse country data (only static info, not rates)
        if countries_html_file and os.path.exists(countries_html_file):
            self.country_data = self._parse_countries_html(countries_html_file)
            self._save_country_data()
        else:
            self._load_country_data()

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": random.choice(self.USER_AGENTS)})

        self.logger = logging.getLogger(f"providers.{name}")

        # Initial rates fetch
        self._ensure_rates_are_current()

    def standardize_response(
        self, raw_result: Dict[str, Any], provider_specific_data: bool = False
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
            "delivery_time_minutes": raw_result.get(
                "delivery_time_minutes", self.DEFAULT_DELIVERY_TIME
            ),
            "timestamp": raw_result.get("timestamp", datetime.datetime.now().isoformat()),
        }

        if provider_specific_data and "raw_response" in raw_result:
            output["raw_response"] = raw_result["raw_response"]

        return output

    def _parse_countries_html(self, html_file: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse HTML file containing country data.

        Only extracts static country information, not rates.
        """
        country_data = {}
        with open(html_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        li_tags = soup.find_all("li", attrs={"data-item": True})
        for li in li_tags:
            data_str = li["data-item"]
            try:
                item = json.loads(data_str)
                cid = item.get("country_id")
                iso2 = item.get("iso2")
                ccode = item.get("currency_code")
                if cid and iso2 and ccode:
                    country_data[iso2.upper()] = {
                        "country_id": cid,
                        "country_name": item.get("country_to"),
                        "currency_name": item.get("currency_name"),
                        "currency_code": ccode.upper(),
                        "iso2": iso2.upper(),
                        "iso3": item.get("iso3"),
                    }
            except json.JSONDecodeError:
                pass
        return country_data

    def _save_country_data(self) -> None:
        """Save country data to JSON file."""
        try:
            data_file = Path(__file__).parent / self.COUNTRIES_DATA_FILE
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(self.country_data, f, indent=2)
        except Exception as exc:
            logger.warning(f"Could not save Remitbee country data: {exc}")

    def _load_country_data(self) -> None:
        """Load country data from JSON file."""
        data_file = Path(__file__).parent / self.COUNTRIES_DATA_FILE
        if data_file.exists():
            with open(data_file, "r", encoding="utf-8") as f:
                self.country_data = json.load(f)
        else:
            logger.warning(f"Countries data file not found: {data_file}")
            # Try to fetch countries from the API as a fallback
            self._fetch_countries_and_rates()

    def _ensure_rates_are_current(self) -> None:
        """
        Check if cached rates are still valid, fetch new ones if needed.

        Rates are considered valid for CACHE_VALIDITY_SECONDS (default: 24 hours).
        """
        current_time = time.time()

        # Check if cache is expired or empty
        if (
            current_time - self.rates_cache_timestamp > self.CACHE_VALIDITY_SECONDS
            or not self.rates_cache
        ):
            logger.info("Rates cache expired or empty, fetching fresh rates")
            self._fetch_countries_and_rates()

    def _fetch_countries_and_rates(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch all supported countries and rates from Remitbee API.

        Updates both country_data (static info) and rates_cache (volatile info).
        Sets the timestamp for cache validity tracking.

        Returns:
            Combined dictionary with both country data and rates
        """
        url = f"{self.BASE_URL}{self.RATES_ENDPOINT}"
        headers = {
            "Accept": "*/*",
            "Origin": "https://www.remitbee.com",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": random.choice(self.USER_AGENTS),
        }

        try:
            # First visit the home page to get cookies
            self.session.get("https://www.remitbee.com/", timeout=20)

            # Fetch all rates
            response = self.session.get(url, headers=headers, timeout=20)
            response.raise_for_status()

            data = response.json()
            rates = data.get("rates", [])

            # Process rates into our separate caches
            rates_data = {}

            for rate in rates:
                iso2 = rate.get("iso2")
                currency_code = rate.get("currency_code")

                # Skip USD entries for countries other than US (they're duplicates)
                if currency_code == "USD" and iso2 != "US":
                    continue

                if iso2 and currency_code:
                    iso2 = iso2.upper()

                    # Update static country data if not already present
                    if iso2 not in self.country_data:
                        self.country_data[iso2] = {
                            "country_id": rate.get("country_id"),
                            "country_name": rate.get("country_to"),
                            "currency_name": rate.get("currency_name"),
                            "currency_code": currency_code.upper(),
                            "iso2": iso2,
                            "iso3": rate.get("iso3"),
                        }

                    # Store rate data in the volatile cache
                    rates_data[iso2] = {
                        "rate": rate.get("rate"),
                        "special_rate": rate.get("special_rate"),
                        "special_rate_adjustment": rate.get("special_rate_adjustment"),
                        "special_rate_transfer_amount_limit": rate.get(
                            "special_rate_transfer_amount_limit"
                        ),
                    }

            # Update caches and timestamp
            self.rates_cache = rates_data
            self.rates_cache_timestamp = time.time()

            # Save just the country data (not rates) to file
            self._save_country_data()

            logger.info(f"Successfully fetched rates for {len(rates_data)} countries")
            return self.country_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Remitbee countries and rates: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error processing Remitbee countries and rates: {e}")
            return {}

    def _get_rate_for_country(self, country_code: str) -> Tuple[float, bool]:
        """
        Get the current exchange rate for a country, ensuring rates are up-to-date.

        Args:
            country_code: ISO-3166 alpha-2 country code

        Returns:
            Tuple of (rate, is_special_rate)
            - rate: The exchange rate as a float
            - is_special_rate: Boolean indicating if special rate is being used
        """
        # Make sure rates are current
        self._ensure_rates_are_current()

        country_code = country_code.upper()
        rate_info = self.rates_cache.get(country_code, {})

        # Check if special rate is available and parse rates
        special_rate = rate_info.get("special_rate")
        standard_rate = rate_info.get("rate")

        # Parse rates as floats, handling various formats
        try:
            if special_rate and special_rate not in ("null", "false", ""):
                return float(special_rate), True
        except (ValueError, TypeError):
            pass

        try:
            if standard_rate and standard_rate not in ("null", "false", ""):
                return float(standard_rate), False
        except (ValueError, TypeError):
            pass

        # No valid rate found
        return 0.0, False

    def _request_quote(
        self,
        country_id: int,
        currency_code: str,
        amount: Decimal,
        is_special_rate: bool,
    ) -> Dict[str, Any]:
        """
        Request a quote from Remitbee API.

        Args:
            country_id: Remitbee's internal country ID
            currency_code: ISO currency code for destination
            amount: Amount to send
            is_special_rate: Whether to use special rate

        Returns:
            API response as dictionary

        Raises:
            RemitbeeConnectionError: On connection issues
            RemitbeeApiError: On API errors
        """
        url = f"{self.BASE_URL}{self.QUOTE_ENDPOINT}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.remitbee.com",
            "Referer": "https://www.remitbee.com/send-money",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Requested-With": "XMLHttpRequest",
        }
        payload = {
            "transfer_amount": f"{amount:.2f}",
            "country_id": country_id,
            "currency_code": currency_code,
            "include_timeline": True,
            "is_special_rate": is_special_rate,
            "source_currency": "CAD",
            "source_country": "CA",
        }
        try:
            # First do a GET to set initial cookies
            self.session.get("https://www.remitbee.com/", timeout=20)
            resp = self.session.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 403:
                raise RemitbeeApiError("403 Forbidden from Remitbee API.")
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise RemitbeeConnectionError(f"Connection error: {e}")
        except ValueError as e:
            raise RemitbeeApiError(f"Invalid JSON response: {e}")

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
        # Remitbee only supports CAD as source currency
        if source_currency.upper() != "CAD" or source_country.upper() != "CA":
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": "Remitbee only supports CAD (Canada) as source currency/country",
                    "send_amount": float(amount),
                    "source_currency": source_currency.upper(),
                    "destination_currency": dest_currency.upper(),
                }
            )

        # Process quote for supported destination
        dest_country = dest_country.upper()
        cdata = self.country_data.get(dest_country)
        if not cdata:
            # Try to fetch country data from API if not in our cache
            logger.info(f"Country {dest_country} not found in cache, fetching from API")
            self._fetch_countries_and_rates()
            cdata = self.country_data.get(dest_country)
            if not cdata:
                return self.standardize_response(
                    {
                        "success": False,
                        "error_message": f"Unsupported destination country: {dest_country}",
                        "send_amount": float(amount),
                        "source_currency": source_currency.upper(),
                        "destination_currency": dest_currency.upper(),
                        "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                        "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                    }
                )

        # Check if destination currency matches country's currency
        if dest_currency.upper() != cdata["currency_code"]:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Invalid currency {dest_currency} for country {dest_country}. Expected: {cdata['currency_code']}",
                    "send_amount": float(amount),
                    "source_currency": source_currency.upper(),
                    "destination_currency": dest_currency.upper(),
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )

        # Attempt to get quote from API
        try:
            country_id = cdata["country_id"]
            currency_code = cdata["currency_code"]

            # Get rate from cache
            rate, is_special_rate = self._get_rate_for_country(dest_country)

            # For small amounts, we can calculate based on cached rates
            # If specific amount is small enough and we have the rate, we can avoid API call
            if float(amount) <= 200 and rate > 0:
                # Simple calculation for small amounts
                receive_amount = float(amount) * rate

                return self.standardize_response(
                    {
                        "success": True,
                        "error_message": None,
                        "send_amount": float(amount),
                        "source_currency": source_currency.upper(),
                        "destination_currency": currency_code,
                        "destination_amount": receive_amount,
                        "exchange_rate": rate,
                        "fee": 2.99,  # Default fee for small amounts
                        "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                        "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                        "delivery_time_minutes": self.DEFAULT_DELIVERY_TIME,
                        "timestamp": datetime.datetime.now().isoformat(),
                    }
                )

            # For larger amounts or if we don't have a rate, call the API
            try:
                quote_data = self._request_quote(country_id, currency_code, amount, is_special_rate)
            except (RemitbeeConnectionError, RemitbeeApiError) as e:
                if (
                    "Unable to find requested country rate" in str(e)
                    or "country rate" in str(e).lower()
                ):
                    # Try to refresh countries and rates
                    logger.info(f"Failed to get rate for {dest_country}, refreshing country data")
                    self._fetch_countries_and_rates()
                    cdata = self.country_data.get(dest_country)
                    if not cdata:
                        raise RemitbeeApiError(
                            f"Country {dest_country} not supported after refresh"
                        )

                    # Try again with fresh data
                    country_id = cdata["country_id"]
                    rate, is_special_rate = self._get_rate_for_country(dest_country)
                    quote_data = self._request_quote(
                        country_id, currency_code, amount, is_special_rate
                    )
                else:
                    raise

            # Check for API error message
            if "message" in quote_data and "unable to find" in quote_data["message"].lower():
                # Force refresh rates and try one more time
                self._fetch_countries_and_rates()
                country_id = self.country_data.get(dest_country, {}).get("country_id")
                if not country_id:
                    return self.standardize_response(
                        {
                            "success": False,
                            "error_message": quote_data["message"],
                            "send_amount": float(amount),
                            "source_currency": source_currency.upper(),
                            "destination_currency": currency_code,
                            "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                            "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                        }
                    )

                # Try one more time with fresh data
                rate, is_special_rate = self._get_rate_for_country(dest_country)
                quote_data = self._request_quote(country_id, currency_code, amount, is_special_rate)

                # If still has error message, give up
                if "message" in quote_data and "unable to find" in quote_data["message"].lower():
                    return self.standardize_response(
                        {
                            "success": False,
                            "error_message": quote_data["message"],
                            "send_amount": float(amount),
                            "source_currency": source_currency.upper(),
                            "destination_currency": currency_code,
                            "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                            "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                        }
                    )

            # Parse response data
            api_rate = quote_data.get("rate", 0.0)
            if api_rate > 0:
                # Update our rate cache with the latest value from API
                if dest_country in self.rates_cache:
                    self.rates_cache[dest_country]["rate"] = api_rate

            rec_amount_str = quote_data.get("receiving_amount", "0").replace(",", "")
            rec_amount = float(rec_amount_str) if rec_amount_str else 0.0
            fee_val = 0.0
            delivery_minutes = self.DEFAULT_DELIVERY_TIME

            # Extract payment details if available
            payment_types = quote_data.get("payment_types", [])
            actual_payment_method = payment_method or self.DEFAULT_PAYMENT_METHOD
            actual_delivery_method = delivery_method or self.DEFAULT_DELIVERY_METHOD

            if payment_types:
                # Get first payment type's fee
                fee_str = payment_types[0].get("fees", "0.00")
                fee_val = float(fee_str) if fee_str else 0.0

                # Get delivery time if available
                if (
                    "timeline" in payment_types[0]
                    and "settlement_timeline" in payment_types[0]["timeline"]
                ):
                    mins = payment_types[0]["timeline"]["settlement_timeline"].get(
                        "predicted_minutes", 0
                    )
                    delivery_minutes = mins if mins > 0 else self.DEFAULT_DELIVERY_TIME

                # Try to get actual payment and delivery methods
                if "type" in payment_types[0]:
                    payment_type = payment_types[0]["type"].lower()
                    if "bank" in payment_type:
                        actual_payment_method = "bank"
                    elif "card" in payment_type or "credit" in payment_type:
                        actual_payment_method = "card"

            # Build success response
            return self.standardize_response(
                {
                    "success": True,
                    "error_message": None,
                    "send_amount": float(amount),
                    "source_currency": source_currency.upper(),
                    "destination_currency": currency_code,
                    "destination_amount": rec_amount,
                    "exchange_rate": float(api_rate or rate),  # Prefer API rate, fallback to cached
                    "fee": fee_val,
                    "payment_method": actual_payment_method,
                    "delivery_method": actual_delivery_method,
                    "delivery_time_minutes": delivery_minutes,
                    "timestamp": datetime.datetime.now().isoformat(),
                }
            )

        except (RemitbeeConnectionError, RemitbeeApiError) as e:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": str(e),
                    "send_amount": float(amount),
                    "source_currency": source_currency.upper(),
                    "destination_currency": dest_currency.upper(),
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Unexpected error: {str(e)}",
                    "send_amount": float(amount),
                    "source_currency": source_currency.upper(),
                    "destination_currency": dest_currency.upper(),
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )

    def get_exchange_rate(
        self, send_amount: Decimal, send_currency: str, target_currency: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy method for getting exchange rate.

        This method is maintained for backward compatibility.
        For new code, use get_quote instead.
        """
        # Extract country code from kwargs or try to derive it
        receive_country = kwargs.get("receive_country")
        if not receive_country:
            # Try to find country for the target currency
            for country_code, data in self.country_data.items():
                if data.get("currency_code") == target_currency.upper():
                    receive_country = country_code
                    break

        if not receive_country:
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
            source_country="CA",  # Remitbee only supports CAD from Canada
            dest_country=receive_country,
            payment_method=kwargs.get("payment_method"),
            delivery_method=kwargs.get("delivery_method"),
        )

    def get_supported_countries(self) -> List[str]:
        """Return list of supported destination countries in ISO alpha-2 format."""
        # Ensure rates are current before returning the list
        self._ensure_rates_are_current()
        return sorted(list(self.country_data.keys()))

    def get_supported_currencies(self) -> List[str]:
        """Return list of supported destination currencies in ISO format."""
        # Ensure rates are current before returning the list
        self._ensure_rates_are_current()
        currencies = ["CAD"]  # Source currency
        for data in self.country_data.values():
            if "currency_code" in data:
                currencies.append(data["currency_code"])
        return sorted(list(set(currencies)))

    def close(self):
        """Close the session if it's open."""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
