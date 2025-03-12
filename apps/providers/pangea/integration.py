"""
Pangea Money Transfer Integration

This module implements an aggregator-ready integration with Pangea Money Transfer API.
Pangea offers money transfer services to various countries with competitive
rates and multiple delivery methods.

The primary API endpoint used is the FeesAndFX endpoint which provides:
- Exchange rates
- Fee information
- Delivery method options
- Estimated delivery times

The API format for the exchange parameter is:
{sourceCurrency}-{targetCurrency}|{sourceCountry}-{targetCountry}
For example: USD-MXN|US-MX for US Dollar to Mexican Peso from US to Mexico
"""

import json
import logging
import os
import pprint
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider

from .exceptions import (
    PangeaAuthenticationError,
    PangeaConnectionError,
    PangeaError,
    PangeaRateLimitError,
    PangeaValidationError,
)

logger = logging.getLogger(__name__)


def log_request_details(
    logger, method: str, url: str, headers: Dict, params: Dict = None, data: Dict = None
):
    """Log details of outgoing API requests."""
    logger.debug("\n" + "=" * 80 + f"\nOUTGOING REQUEST DETAILS:\n{'='*80}")
    logger.debug(f"Method: {method}")
    logger.debug(f"URL: {url}")

    masked_headers = headers.copy()
    for key in ("Authorization", "Cookie"):
        if key in masked_headers:
            masked_headers[key] = "***MASKED***"

    logger.debug("\nHeaders:")
    logger.debug(pprint.pformat(masked_headers))

    if params:
        logger.debug("\nQuery Params:")
        logger.debug(pprint.pformat(params))
    if data:
        logger.debug("\nRequest Body:")
        logger.debug(pprint.pformat(data))


def log_response_details(logger, response):
    """Log details of API responses."""
    logger.debug("\n" + "=" * 80 + f"\nRESPONSE DETAILS:\n{'='*80}")
    logger.debug(f"Status Code: {response.status_code}")
    logger.debug(f"Reason: {response.reason}")
    logger.debug("\nResponse Headers:")
    logger.debug(pprint.pformat(dict(response.headers)))

    try:
        body = response.json()
        logger.debug("\nJSON Response Body:")
        logger.debug(pprint.pformat(body))
    except ValueError:
        body = response.text
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type:
            logger.debug("\nHTML Response (truncated):")
            logger.debug(body[:500] + "..." if len(body) > 500 else body)
        else:
            logger.debug("\nPlain Text Response:")
            logger.debug(body[:1000] + "..." if len(body) > 1000 else body)

    logger.debug("=" * 80)


class PangeaProvider(RemittanceProvider):
    """
    Aggregator-ready integration with Pangea Money Transfer service.
    Fetches exchange rates, fees, and other info from the FeesAndFX endpoint.
    """

    BASE_URL = "https://api.gopangea.com"
    FEES_AND_FX_ENDPOINT = "/api/v5/FeesAndFX"

    # Mapping of country codes -> default currency codes
    COUNTRY_TO_CURRENCY = {
        "US": "USD",  # United States
        "MX": "MXN",  # Mexico
        "CO": "COP",  # Colombia
        "GT": "GTQ",  # Guatemala
        "DO": "DOP",  # Dominican Republic
        "SV": "USD",  # El Salvador
        "PE": "PEN",  # Peru
        "EC": "USD",  # Ecuador
        "BR": "BRL",  # Brazil
        "BO": "BOB",  # Bolivia
        "PY": "PYG",  # Paraguay
        "NI": "NIO",  # Nicaragua
        "HN": "HNL",  # Honduras
        "PH": "PHP",  # Philippines
        "IN": "INR",  # India
        "VN": "VND",  # Vietnam
        "CN": "CNY",  # China
        "ID": "IDR",  # Indonesia
        "KR": "KRW",  # South Korea
        "ES": "EUR",  # Spain
        "FR": "EUR",  # France
        "DE": "EUR",  # Germany
        "IT": "EUR",  # Italy
        "GB": "GBP",  # United Kingdom
        "CA": "CAD",  # Canada
        "AU": "AUD",  # Australia
        "JP": "JPY",  # Japan
    }

    # Sample supported corridors
    SUPPORTED_CORRIDORS = [
        ("US", "MX"),
        ("US", "CO"),
        ("US", "GT"),
        ("US", "DO"),
        ("US", "SV"),
        ("US", "PE"),
        ("US", "EC"),
        ("US", "BR"),
        ("US", "BO"),
        ("US", "PY"),
        ("US", "NI"),
        ("US", "HN"),
        ("US", "PH"),
        ("US", "IN"),
        ("CA", "MX"),
        ("CA", "CO"),
        ("CA", "IN"),
        ("CA", "PH"),
    ]

    def __init__(self, timeout: int = 30, user_agent: Optional[str] = None):
        """Initialize aggregator-ready Pangea provider."""
        super().__init__(name="Pangea", base_url=self.BASE_URL)
        self.logger = logger
        self.timeout = timeout

        self.user_agent = user_agent or os.environ.get(
            "PANGEA_DEFAULT_UA",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
        )

        self._session = requests.Session()
        self._initialize_session()
        self.logger.debug(f"Initialized PangeaProvider with UA: {self.user_agent}")

    def _initialize_session(self) -> None:
        """Set up the HTTP session with default headers and retries."""
        self.logger.debug("Initializing Pangea session...")

        # Default HTTP headers
        self._session.headers.update(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": self.user_agent,
                "Origin": "https://pangeamoneytransfer.com",
                "Referer": "https://pangeamoneytransfer.com/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Connection": "keep-alive",
            }
        )

        self.logger.debug(f"Session headers: {self._session.headers}")

        # Add retry for reliability
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)

    def standardize_response(
        self, local_data: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """Convert local Pangea fields -> aggregator-friendly keys."""
        # aggregator sometimes wants "rate" in parallel to "exchange_rate"
        final_rate = local_data.get("exchange_rate")
        # aggregator also wants "target_currency" = "destination_currency"
        final_target_currency = local_data.get("destination_currency")

        # Build standardized dictionary
        standardized = {
            "provider_id": self.name,
            "success": local_data.get("success", False),
            "error_message": local_data.get("error_message"),
            "send_amount": local_data.get("send_amount"),
            "source_currency": (local_data.get("source_currency") or "").upper(),
            "destination_amount": local_data.get("destination_amount"),
            "destination_currency": (local_data.get("destination_currency") or "").upper(),
            "exchange_rate": local_data.get("exchange_rate"),
            "fee": local_data.get("fee"),
            "payment_method": local_data.get("payment_method"),
            "delivery_method": local_data.get("delivery_method"),
            "delivery_time_minutes": local_data.get("delivery_time_minutes"),
            "timestamp": local_data.get("timestamp") or datetime.now(UTC).isoformat(),
            "rate": final_rate,  # aggregator also expects "rate"
            "target_currency": (final_target_currency or "").upper(),
        }

        # If aggregator wants raw, attach it
        if provider_specific_data and "raw_response" in local_data:
            standardized["raw_response"] = local_data["raw_response"]

        return standardized

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        receive_currency: Optional[str] = None,
        send_country: str = "US",
        **kwargs,
    ) -> Dict[str, Any]:
        """Aggregator style get_exchange_rate returning standardized fields."""
        # local dict to store raw info
        local_result = {
            "success": False,
            "error_message": None,
            "send_amount": float(send_amount),
            "source_currency": send_currency,
            "destination_currency": receive_currency,
            "exchange_rate": None,
            "fee": None,
            "destination_amount": None,
            "delivery_time_minutes": None,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # If no receive_currency, derive from COUNTRY_TO_CURRENCY
        if not receive_currency:
            receive_currency = self.COUNTRY_TO_CURRENCY.get(receive_country)
            if not receive_currency:
                local_result["error_message"] = f"No default currency mapped for {receive_country}"
                return self.standardize_response(local_result)

        # Basic validation
        if send_amount <= 0:
            local_result["error_message"] = f"Invalid send_amount: {send_amount}"
            return self.standardize_response(local_result)

        try:
            # 1) call get_fees_and_fx to retrieve raw Fees & FX JSON
            fees_data = self.get_fees_and_fx(
                source_country=send_country,
                target_country=receive_country,
                source_currency=send_currency,
                target_currency=receive_currency,
            )
            if not fees_data:
                local_result["error_message"] = "Empty or invalid FeesAndFX data from Pangea"
                return self.standardize_response(local_result)

            # 2) parse exchange rates
            exchange_rates = fees_data.get("ExchangeRates", [])
            if not exchange_rates:
                local_result["error_message"] = "No ExchangeRates in Pangea response"
                return self.standardize_response(local_result)

            # find 'Regular' rate
            regular_rate = next(
                (r for r in exchange_rates if r.get("ExchangeRateType") == "Regular"),
                None,
            )
            if not regular_rate:
                local_result["error_message"] = "No 'Regular' exchange rate found"
                return self.standardize_response(local_result)

            # parse numeric exchange rate
            rate_val = float(regular_rate.get("Rate", 0))
            if rate_val <= 0:
                local_result["error_message"] = "Exchange rate is zero or negative"
                return self.standardize_response(local_result)

            # 3) parse fees
            fees_obj = fees_data.get("Fees", {})
            card_fees = fees_obj.get("Card", [])
            fee_val = float(card_fees[0].get("Fee", 0)) if card_fees else 0.0

            local_result["exchange_rate"] = rate_val
            local_result["fee"] = fee_val

            # 4) compute final destination_amount = (send_amount - fee) * rate
            adj_send_amount = float(send_amount) - fee_val
            if adj_send_amount < 0:
                adj_send_amount = 0.0
            local_result["destination_amount"] = adj_send_amount * rate_val

            local_result["success"] = True
            local_result["destination_currency"] = receive_currency  # finalize

        except (PangeaError, PangeaConnectionError, PangeaValidationError) as exc:
            self.logger.error(f"Pangea error: {exc}")
            local_result["error_message"] = str(exc)
        except Exception as exc:
            self.logger.error(f"Unexpected error in get_exchange_rate: {exc}")
            local_result["error_message"] = f"Unexpected error: {exc}"

        return self.standardize_response(
            local_result, provider_specific_data=kwargs.get("include_raw", False)
        )

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        target_currency: str,
        source_country: str = "US",
        target_country: str = "MX",
        **kwargs,
    ) -> Dict[str, Any]:
        """Aggregator style get_quote. Calls get_exchange_rate internally."""
        return self.get_exchange_rate(
            send_amount=amount,
            send_currency=source_currency,
            receive_country=target_country,
            receive_currency=target_currency,
            send_country=source_country,
            **kwargs,
        )

    def get_fees_and_fx(
        self,
        source_country: str,
        target_country: str,
        source_currency: str,
        target_currency: str,
    ) -> Dict[str, Any]:
        """Get fees and exchange rate data from Pangea's API (raw JSON)."""
        try:
            # Construct exchange param: {sourceCur}-{targetCur}|{sourceCountry}-{targetCountry}
            exchange_param = (
                f"{source_currency}-{target_currency}|{source_country}-{target_country}"
            )
            url = urljoin(self.BASE_URL, self.FEES_AND_FX_ENDPOINT)
            params = {"exchange": exchange_param, "senderId": ""}

            self.logger.info(f"Requesting Pangea Fees/FX: {url}, params={params}")
            log_request_details(self.logger, "GET", url, dict(self._session.headers), params=params)

            response = self._session.get(url, params=params, timeout=self.timeout)
            log_response_details(self.logger, response)

            if response.status_code != 200:
                try:
                    error_json = response.json()
                    self.logger.warning(
                        f"Non-200 status from Pangea: {response.status_code}, error_json={error_json}"
                    )
                except Exception:
                    pass
                response.raise_for_status()

            try:
                data = response.json()
            except ValueError as e:
                raise PangeaValidationError(
                    "Invalid JSON response from Pangea",
                    error_code="INVALID_JSON",
                    details={"raw_response_text": response.text[:500]},
                )

            if not data:
                raise PangeaValidationError(
                    "Empty JSON from Pangea", error_code="EMPTY_RESPONSE", details={}
                )
            if "ExchangeRates" not in data:
                raise PangeaValidationError(
                    "Missing ExchangeRates field in Pangea response",
                    error_code="INVALID_RESPONSE",
                    details={"partial_response": data},
                )

            return data

        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            resp_text = e.response.text if e.response else ""
            if status_code == 401:
                raise PangeaAuthenticationError(
                    "Authentication failed with Pangea API",
                    error_code="AUTH_FAILED",
                    details={"original_error": str(e), "response": resp_text},
                )
            elif status_code == 400:
                raise PangeaValidationError(
                    "Invalid request parameters to Pangea",
                    error_code="INVALID_PARAMETERS",
                    details={"original_error": str(e), "response": resp_text},
                )
            elif status_code == 429:
                raise PangeaRateLimitError(
                    "Rate limit exceeded for Pangea API",
                    error_code="RATE_LIMIT",
                    details={"original_error": str(e), "response": resp_text},
                )
            else:
                raise PangeaConnectionError(
                    f"HTTP error from Pangea: {status_code}",
                    error_code="HTTP_ERROR",
                    details={"original_error": str(e), "response": resp_text},
                )

        except requests.RequestException as e:
            raise PangeaConnectionError(
                f"Failed to connect to Pangea API: {e}",
                error_code="CONNECTION_FAILED",
                details={"original_error": str(e)},
            )
        except Exception as e:
            raise PangeaError(
                f"Unexpected error: {e}",
                error_code="UNEXPECTED_ERROR",
                details={"original_error": str(e)},
            )

    def get_supported_corridors(self) -> List[Dict]:
        """List aggregator style corridors."""
        return [
            {"source_country": src, "target_country": tgt} for src, tgt in self.SUPPORTED_CORRIDORS
        ]

    def get_payment_methods(self, source_country: str, target_country: str) -> List[str]:
        """List aggregator style payment methods."""
        return ["bank_transfer", "debit_card", "credit_card"]

    def get_delivery_methods(self, source_country: str, target_country: str) -> List[str]:
        """List aggregator style receiving methods."""
        methods = ["bank_deposit"]
        if target_country in ["MX", "CO", "GT", "DO", "PE", "EC", "BR", "PH"]:
            methods.append("cash_pickup")
        if target_country in ["PH", "IN"]:
            methods.append("mobile_money")
        return methods

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            self._session.close()
