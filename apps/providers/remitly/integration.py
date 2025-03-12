"""
Remitly Money Transfer Integration

This module implements the integration with Remitly, a service for international
money transfers. Remitly supports various payment and delivery methods.

PAYMENT METHODS:
---------------------------------
- BANK_ACCOUNT: Bank account transfer
- DEBIT_CARD: Debit card payment
- CREDIT_CARD: Credit card payment

DELIVERY METHODS:
---------------------------------
- BANK_DEPOSIT: Bank deposit
- CASH_PICKUP: Cash pickup at agent locations
- HOME_DELIVERY: Cash delivered to recipient's home
- MOBILE_WALLET: Mobile wallet transfer

Important API notes:
1. Remitly's API requires specific headers including Remitly-DeviceEnvironmentID
2. Each corridor has different combinations of payment and delivery methods
3. Fees vary significantly based on payment method, delivery method, and amount
4. Exchange rates can vary by corridor and amount
"""

import json
import logging
import re
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from apps.providers.remitly.exceptions import (
    RemitlyAuthenticationError,
    RemitlyConnectionError,
    RemitlyError,
    RemitlyRateLimitError,
    RemitlyValidationError,
)

# Setup logging
logger = logging.getLogger(__name__)


class ExchangeRateResult:
    """Class to store exchange rate information in a standardized format."""

    def __init__(
        self,
        provider_id: str,
        source_currency: str,
        source_amount: float,
        destination_currency: str,
        destination_amount: float,
        exchange_rate: float,
        fee: float,
        delivery_method: str,
        delivery_time_minutes: Optional[int] = None,
        corridor: Optional[str] = None,
        payment_method: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        self.provider_id = provider_id
        self.source_currency = source_currency
        self.source_amount = source_amount
        self.destination_currency = destination_currency
        self.destination_amount = destination_amount
        self.exchange_rate = exchange_rate
        self.fee = fee
        self.delivery_method = delivery_method
        self.delivery_time_minutes = delivery_time_minutes
        self.corridor = corridor
        self.payment_method = payment_method
        self.details = details or {}

    def to_dict(self) -> Dict:
        """Convert the result to a dictionary."""
        return {
            "provider_id": self.provider_id,
            "source_currency": self.source_currency,
            "source_amount": self.source_amount,
            "destination_currency": self.destination_currency,
            "destination_amount": self.destination_amount,
            "exchange_rate": self.exchange_rate,
            "fee": self.fee,
            "delivery_method": self.delivery_method,
            "delivery_time_minutes": self.delivery_time_minutes,
            "corridor": self.corridor,
            "payment_method": self.payment_method,
            "details": self.details,
        }


class RemitlyProvider(RemittanceProvider):
    """
    Aggregator-ready integration with Remitly money transfer service.
    Produces standardized dictionary responses, with no fallback data.

    If an API call fails, it returns a standardized response with success=False
    and an appropriate error message rather than using mock data.

    Example usage:
        provider = RemitlyProvider()
        result = provider.get_quote(
            amount=Decimal("1000.00"),
            source_currency="USD",
            dest_currency="PHP",
            source_country="US",
            dest_country="PH"
        )
    """

    BASE_URL = "https://api.remitly.io"
    CALCULATOR_ENDPOINT = "/v3/calculator/estimate"

    # Default payment/delivery methods and estimated delivery time (minutes)
    DEFAULT_PAYMENT_METHOD = "bank"
    DEFAULT_DELIVERY_METHOD = "bank"
    DEFAULT_DELIVERY_TIME = 1440  # 24 hours in minutes

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.3 Safari/605.1.15"
    )

    DEFAULT_DEVICE_ENV_ID = (
        "3RoCMEE0ZDG79rpNP7sK7MoEVrYFpVS4TgavrNTpz405kCFlIwl0s49e1xh4okoKhH2bA"
        "HxYPg0GZINPtd1BG4xDZGA0b0wOoffs2ZSr9Lm1"
    )

    DEFAULT_BROWSER_FINGERPRINT = {
        "browser_fingerprint_id": "1424498403190294011",
        "session_id": "1424498403198931748",
        "identity_id": "1424498403198837863",
        "link": "https://link.remitly.com/a/key_live_fedYw0b1AK8QmSuljIyvAmdbrAbwqqAc"
        "?%24identity_id=1424498403198837863",
        "data": '{"+clicked_branch_link":false,"+is_first_session":true}',
        "has_app": False,
    }

    def __init__(
        self,
        name="remitly",
        device_env_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: int = 30,
        **kwargs,
    ):
        """
        Initialize the Remitly provider.

        Args:
            name: Provider identifier
            device_env_id: Remitly-DeviceEnvironmentID header
            user_agent: Custom user agent string
            timeout: Request timeout in seconds
            **kwargs: Additional parameters
        """
        super().__init__(name=name, base_url=self.BASE_URL)
        self.timeout = timeout
        self.device_env_id = device_env_id or self.DEFAULT_DEVICE_ENV_ID
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT

        self.session = requests.Session()
        self._setup_session()
        self.logger = logging.getLogger(f"providers.{name}")

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
            "timestamp": raw_result.get("timestamp", time.time()),
        }

        # Include raw API response if requested and available
        if (
            provider_specific_data
            and "details" in raw_result
            and "raw_response" in raw_result["details"]
        ):
            output["raw_response"] = raw_result["details"]["raw_response"]

        return output

    def _setup_session(self) -> None:
        """Set up the HTTP session with appropriate headers and retry strategy."""
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://www.remitly.com",
                "Referer": "https://www.remitly.com/",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )
        fingerprint_json = json.dumps(self.DEFAULT_BROWSER_FINGERPRINT)
        self.session.headers["X-Remitly-Browser-Fingerprint"] = fingerprint_json
        self.session.headers["Remitly-DeviceEnvironmentID"] = self.device_env_id

        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _make_api_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        retry_auth: bool = True,
        max_retries: int = 2,
    ) -> Dict:
        """
        Make a request to the Remitly API with retry logic.

        Args:
            method: HTTP method (GET, POST)
            url: API endpoint URL
            params: Query parameters
            data: Request body for POST requests
            retry_auth: Whether to retry on authentication failures
            max_retries: Maximum number of retries

        Returns:
            API response as dictionary

        Raises:
            RemitlyError: General API errors
            RemitlyAuthenticationError: Authentication failures
            RemitlyConnectionError: Network issues
            RemitlyRateLimitError: Rate limiting
        """
        retry_count = 0

        while retry_count <= max_retries:
            try:
                if method.upper() == "GET":
                    response = self.session.get(
                        url, params=params, timeout=self.timeout, allow_redirects=False
                    )
                else:
                    response = self.session.post(
                        url,
                        json=data,
                        params=params,
                        timeout=self.timeout,
                        allow_redirects=False,
                    )

                logger.debug(f"Remitly API response status: {response.status_code}")

                # Handle 3xx redirects if they point to sign-in pages
                if response.status_code in (301, 302, 303, 307, 308):
                    redirect_url = response.headers.get("Location")
                    logger.debug(f"Redirected to: {redirect_url}")
                    if redirect_url and "/sign-in" in redirect_url:
                        if retry_auth and retry_count < max_retries:
                            logger.warning(
                                f"Redirected to sign-in, refreshing session (attempt {retry_count + 1})"
                            )
                            self._setup_session()
                            time.sleep(1)
                            retry_count += 1
                            continue
                        else:
                            raise RemitlyAuthenticationError("Redirected to sign-in page")

                if response.status_code in (401, 403):
                    if retry_auth and retry_count < max_retries:
                        logger.warning(
                            f"Authentication failed, refreshing session (attempt {retry_count + 1})"
                        )
                        self._setup_session()
                        time.sleep(1)
                        retry_count += 1
                        continue
                    raise RemitlyAuthenticationError("Authentication failed")

                if response.status_code == 429:
                    if retry_count < max_retries:
                        wait_time = 5 * (retry_count + 1)
                        logger.warning(
                            f"Rate limit exceeded, waiting {wait_time}s (attempt {retry_count + 1})"
                        )
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    raise RemitlyRateLimitError("Rate limit exceeded")

                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", "Unknown API error")
                        raise RemitlyError(f"API error: {error_msg}")
                    except (ValueError, KeyError):
                        raise RemitlyError(f"API error: {response.status_code}")

                try:
                    return response.json()
                except ValueError:
                    if response.status_code == 200 and not response.text.strip():
                        return {}
                    raise RemitlyError("Invalid JSON response from API")

            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")
                if retry_count < max_retries:
                    logger.warning(f"Network error, retrying (attempt {retry_count + 1})")
                    time.sleep(2)
                    retry_count += 1
                    continue
                raise RemitlyConnectionError(f"Connection error: {e}")

        raise RemitlyError("Maximum retries exceeded")

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
        # Convert 2-letter country codes to 3-letter format needed by Remitly
        source_country_3 = self._convert_country_code(source_country)
        dest_country_3 = self._convert_country_code(dest_country)

        # Verify destination currency matches the country
        expected_dest_currency = dest_currency
        if not dest_currency:
            expected_dest_currency = self._get_currency_for_country(dest_country_3)

        if dest_currency and dest_currency != expected_dest_currency:
            logger.warning(
                f"Provided currency {dest_currency} may not match default currency for {dest_country_3} ({expected_dest_currency})"
            )

        send_amount_float = float(amount)

        # Build corridor string for Remitly (e.g., "USA:USD-PHL:PHP")
        conduit_str = f"{source_country_3}:{source_currency}-{dest_country_3}:{dest_currency or expected_dest_currency}"

        url = f"{self.base_url}{self.CALCULATOR_ENDPOINT}"
        params = {
            "conduit": conduit_str,
            "anchor": "SEND",
            "amount": str(send_amount_float),
            "purpose": kwargs.get("purpose", "OTHER"),
            "customer_segment": kwargs.get("customer_segment", "UNRECOGNIZED"),
            "strict_promo": str(kwargs.get("strict_promo", False)).lower(),
        }

        try:
            response_data = self._make_api_request("GET", url, params=params)
            if not response_data:
                return self.standardize_response(
                    {
                        "success": False,
                        "error_message": "Empty response from Remitly API",
                        "send_amount": send_amount_float,
                        "source_currency": source_currency,
                        "destination_currency": dest_currency or expected_dest_currency,
                        "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                        "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                    }
                )

            estimate = response_data.get("estimate")
            if not estimate:
                return self.standardize_response(
                    {
                        "success": False,
                        "error_message": "No 'estimate' data in Remitly response",
                        "send_amount": send_amount_float,
                        "source_currency": source_currency,
                        "destination_currency": dest_currency or expected_dest_currency,
                        "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                        "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                    }
                )

            # Extract exchange rate
            exchange_rate_data = estimate.get("exchange_rate", {})
            exchange_rate = float(exchange_rate_data.get("base_rate", 0.0))

            # Extract fee
            fee_data = estimate.get("fee", {})
            fee = float(fee_data.get("total_fee_amount", 0.0))

            # Extract receive amount
            receive_amount_str = estimate.get("receive_amount", "0.0")
            try:
                receive_amount = float(receive_amount_str)
            except ValueError:
                receive_amount = 0.0

            # Extract delivery time
            delivery_time_minutes = self.DEFAULT_DELIVERY_TIME
            delivery_time_text = estimate.get("delivery_speed_description", "")
            if "minutes" in delivery_time_text.lower():
                match = re.search(r"(\d+)\s*minutes", delivery_time_text.lower())
                if match:
                    delivery_time_minutes = int(match.group(1))
            elif "hours" in delivery_time_text.lower():
                match = re.search(r"(\d+)\s*hours", delivery_time_text.lower())
                if match:
                    delivery_time_minutes = int(match.group(1)) * 60

            # Extract delivery method
            normalized_delivery_method = (
                self._normalize_delivery_method(estimate.get("delivery_method", ""))
                or delivery_method
                or self.DEFAULT_DELIVERY_METHOD
            )

            # Extract payment method
            pm = estimate.get("payment_method", "") or payment_method or self.DEFAULT_PAYMENT_METHOD

            return self.standardize_response(
                {
                    "success": True,
                    "error_message": None,
                    "send_amount": send_amount_float,
                    "source_currency": source_currency,
                    "destination_currency": dest_currency or expected_dest_currency,
                    "destination_amount": receive_amount,
                    "exchange_rate": exchange_rate,
                    "fee": fee,
                    "delivery_method": normalized_delivery_method,
                    "delivery_time_minutes": delivery_time_minutes,
                    "payment_method": pm,
                    "details": {"raw_response": response_data},
                }
            )

        except (
            RemitlyError,
            RemitlyConnectionError,
            RemitlyAuthenticationError,
            RemitlyRateLimitError,
        ) as e:
            logger.error(f"Remitly API error: {e}")
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": str(e),
                    "send_amount": send_amount_float,
                    "source_currency": source_currency,
                    "destination_currency": dest_currency or expected_dest_currency,
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error from Remitly: {e}")
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Unexpected error: {str(e)}",
                    "send_amount": send_amount_float,
                    "source_currency": source_currency,
                    "destination_currency": dest_currency or expected_dest_currency,
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )

    def get_exchange_rate(
        self, send_amount: Decimal, send_currency: str, target_currency: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy method for getting exchange rates.

        This method is maintained for backward compatibility.
        For new code, use get_quote instead.
        """
        # Determine sending and receiving countries from currencies
        source_country = kwargs.get("source_country") or self._get_country_for_currency(
            send_currency
        )
        if len(source_country) == 2:
            source_country = self._convert_country_code(source_country)

        dest_country = kwargs.get("receive_country") or self._get_country_for_currency(
            target_currency
        )
        if len(dest_country) == 2:
            dest_country = self._convert_country_code(dest_country)

        # Call standardized get_quote method
        return self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            dest_currency=target_currency,
            source_country=source_country,
            dest_country=dest_country,
            payment_method=kwargs.get("payment_method"),
            delivery_method=kwargs.get("delivery_method"),
            **kwargs,
        )

    def _get_currency_for_country(self, country_code: str) -> str:
        """
        Map a country code to its default currency.

        Args:
            country_code: 3-letter country code (e.g., "USA" or "PHL")

        Returns:
            ISO currency code (e.g., "USD" or "PHP")
        """
        country_to_currency = {
            "USA": "USD",
            "US": "USD",
            "CAN": "CAD",
            "CA": "CAD",
            "MEX": "MXN",
            "MX": "MXN",
            "GTM": "GTQ",
            "SV": "USD",
            "HND": "HNL",
            "NIC": "NIO",
            "CRI": "CRC",
            "PAN": "PAB",
            "COL": "COP",
            "PER": "PEN",
            "ECU": "USD",
            "BRA": "BRL",
            "CHL": "CLP",
            "ARG": "ARS",
            "VEN": "VES",
            "PRY": "PYG",
            "URY": "UYU",
            "BOL": "BOB",
            "PHL": "PHP",
            "IND": "INR",
            "CHN": "CNY",
            "VNM": "VND",
            "THA": "THB",
            "IDN": "IDR",
            "KOR": "KRW",
            "NPL": "NPR",
            "BGD": "BDT",
            "PAK": "PKR",
            "JPN": "JPY",
            "LKA": "LKR",
            "MYS": "MYR",
            "SGP": "SGD",
            "MMR": "MMK",
            "KHM": "KHR",
            "LAO": "LAK",
            "ISR": "ILS",
            "SAU": "SAR",
            "ARE": "AED",
            "TUR": "TRY",
            "EGY": "EGP",
            "MAR": "MAD",
            "NGA": "NGN",
            "KEN": "KES",
            "GHA": "GHS",
            "ZAF": "ZAR",
            "TUN": "TND",
            "ETH": "ETB",
            "UGA": "UGX",
            "TZA": "TZS",
            "DZA": "DZD",
            "SEN": "XOF",
            "CMR": "XAF",
            "ESP": "EUR",
            "DEU": "EUR",
            "FRA": "EUR",
            "ITA": "EUR",
            "NLD": "EUR",
            "BEL": "EUR",
            "PRT": "EUR",
            "FIN": "EUR",
            "GBR": "GBP",
            "CHE": "CHF",
            "SWE": "SEK",
            "NOR": "NOK",
            "DNK": "DKK",
            "POL": "PLN",
            "ROU": "RON",
            "AUT": "EUR",
            "IRL": "EUR",
            "AUS": "AUD",
            "NZL": "NZD",
        }
        return country_to_currency.get(country_code, "USD")

    def _convert_country_code(self, cc2: str) -> str:
        """
        Convert 2-letter country code to 3-letter country code.

        Args:
            cc2: 2-letter country code (e.g., "US")

        Returns:
            3-letter country code (e.g., "USA")
        """
        cc_map = {
            "US": "USA",
            "CA": "CAN",
            "MX": "MEX",
            "GT": "GTM",
            "SV": "SLV",
            "HN": "HND",
            "NI": "NIC",
            "CR": "CRI",
            "PA": "PAN",
            "CO": "COL",
            "PE": "PER",
            "EC": "ECU",
            "BR": "BRA",
            "CL": "CHL",
            "AR": "ARG",
            "VE": "VEN",
            "PY": "PRY",
            "UY": "URY",
            "BO": "BOL",
            "PH": "PHL",
            "IN": "IND",
            "CN": "CHN",
            "VN": "VNM",
            "TH": "THA",
            "ID": "IDN",
            "KR": "KOR",
            "NP": "NPL",
            "BD": "BGD",
            "PK": "PAK",
            "JP": "JPN",
            "LK": "LKA",
            "MY": "MYS",
            "SG": "SGP",
            "MM": "MMR",
            "KH": "KHM",
            "LA": "LAO",
            "IL": "ISR",
            "SA": "SAU",
            "AE": "ARE",
            "TR": "TUR",
            "DZ": "DZA",
            "EG": "EGY",
            "MA": "MAR",
            "GH": "GHA",
            "KE": "KES",
            "NG": "NGA",
            "SN": "SEN",
            "TN": "TUN",
            "ZA": "ZAF",
            "UG": "UGA",
            "TZ": "TZA",
            "ET": "ETH",
            "ES": "ESP",
            "DE": "DEU",
            "FR": "FRA",
            "IT": "ITA",
            "PT": "PRT",
            "PL": "POL",
            "RO": "ROU",
            "NL": "NLD",
            "BE": "BEL",
            "GR": "GRC",
            "IE": "IRL",
            "UK": "GBR",
            "GB": "GBR",  # Both UK and GB map to GBR
            "AU": "AUS",
            "NZ": "NZL",
            "FI": "FIN",
            "DK": "DNK",
            "SE": "SWE",
            "NO": "NOR",
            "AT": "AUT",
        }
        return cc_map.get(cc2.upper(), cc2)

    def _get_country_for_currency(self, currency_code: str) -> str:
        """
        Map a currency code to its most common country.

        Args:
            currency_code: ISO currency code (e.g., "USD")

        Returns:
            3-letter country code (e.g., "USA")
        """
        currency_to_country = {
            "USD": "USA",
            "EUR": "ESP",
            "GBP": "GBR",
            "CAD": "CAN",
            "AUD": "AUS",
            "JPY": "JPN",
            "CHF": "CHE",
            "INR": "IND",
            "SGD": "SGP",
            "SEK": "SWE",
            "NOK": "NOR",
            "DKK": "DNK",
            "HKD": "HKG",
            "CNY": "CHN",
            "MXN": "MEX",
            "BRL": "BRA",
            "ZAR": "ZAF",
            "RUB": "RUS",
            "TRY": "TUR",
            "PLN": "POL",
            "PHP": "PHL",
            "THB": "THA",
            "MYR": "MYS",
            "IDR": "IDN",
            "NZD": "NZL",
            "PKR": "PAK",
        }
        return currency_to_country.get(currency_code, "USA")

    def _normalize_delivery_method(self, method_type: str) -> str:
        """
        Normalize delivery method strings to standardized format.

        Args:
            method_type: Raw delivery method string from API

        Returns:
            Normalized delivery method string
        """
        method_map = {
            "BANK_DEPOSIT": "bank",
            "CASH_PICKUP": "cash",
            "HOME_DELIVERY": "delivery",
            "MOBILE_WALLET": "mobile",
        }
        return method_map.get(method_type, method_type.lower())

    def get_supported_countries(self) -> List[str]:
        """Return list of supported countries in ISO alpha-2 format."""
        # These are commonly supported destination countries by Remitly
        return [
            "MX",
            "PH",
            "IN",
            "CO",
            "SV",
            "GT",
            "HN",
            "NI",
            "DO",
            "EC",
            "PE",
            "PL",
            "RO",
            "VN",
            "BD",
            "CN",
            "KR",
            "LK",
            "NP",
            "PK",
            "TH",
            "ID",
            "MY",
            "KH",
        ]

    def get_supported_currencies(self) -> List[str]:
        """Return list of supported currencies in ISO format."""
        # These are currencies Remitly commonly supports
        return [
            "USD",
            "CAD",
            "GBP",
            "EUR",
            "AUD",
            "MXN",
            "PHP",
            "INR",
            "COP",
            "PEN",
            "SVC",
            "GTQ",
            "HNL",
            "NIO",
            "DOP",
            "ECU",
            "PLN",
            "RON",
            "VND",
            "BDT",
            "CNY",
            "KRW",
            "LKR",
            "NPR",
            "PKR",
            "THB",
            "IDR",
            "MYR",
            "KHR",
        ]

    def close(self):
        """Close the session if it's open."""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
