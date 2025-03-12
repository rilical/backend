import json
import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

from apps.providers.base.provider import RemittanceProvider
from apps.providers.rewire.exceptions import (
    RewireApiError,
    RewireConnectionError,
    RewireCorridorUnsupportedError,
    RewireError,
    RewireRateLimitError,
    RewireResponseError,
)

logger = logging.getLogger(__name__)


class RewireProvider(RemittanceProvider):
    RATES_URL = "https://api.rewire.to/services/rates/v3/jsonp"
    PRICING_URL = "https://lights.rewire.to/public/public-pricing"

    DEFAULT_PAYMENT_METHOD = "bank"
    DEFAULT_DELIVERY_METHOD = "bank"
    DEFAULT_DELIVERY_TIME = 1440

    COUNTRY_TO_CURRENCY = {
        "IL": "ILS",
        "GB": "GBP",
        "DE": "EUR",
        "FR": "EUR",
        "IT": "EUR",
        "ES": "EUR",
        "US": "USD",
        "IN": "INR",
        "PH": "PHP",
        "CN": "CNY",
        "JP": "JPY",
        "CA": "CAD",
        "AU": "AUD",
    }

    SUPPORTED_CORRIDORS = [
        ("IL", "PHP"),
        ("IL", "INR"),
        ("IL", "CNY"),
        ("GB", "PHP"),
        ("GB", "INR"),
        ("DE", "PHP"),
        ("DE", "INR"),
    ]

    def __init__(self, name="rewire", **kwargs):
        super().__init__(name=name, base_url=None, **kwargs)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
                ),
                "Accept": "*/*",
                "Origin": "https://www.rewire.com",
                "Referer": "https://www.rewire.com/",
            }
        )

        self.cached_rates: Dict[str, Dict[str, Dict[str, float]]] = {}
        self.cached_fees: Dict[str, Any] = {}
        self.last_fetch_timestamp: int = 0
        self.logger = logging.getLogger(f"providers.{name}")

    def standardize_response(
        self, raw_result: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        output = {
            "provider_id": self.name,
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),
            "send_amount": raw_result.get("send_amount", 0.0),
            "source_currency": raw_result.get("send_currency", "").upper(),
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

        if provider_specific_data and "details" in raw_result:
            output["details"] = raw_result["details"]

        return output

    def fetch_rates(self) -> Dict[str, Any]:
        logger.info("Fetching Rewire rates from %s", self.RATES_URL)
        try:
            resp = self.session.get(self.RATES_URL, timeout=15)
            resp.raise_for_status()

            try:
                data = resp.json()
                if "rates" not in data:
                    raise RewireResponseError("Missing 'rates' field in Rewire response")

                self.cached_rates = data["rates"]
                self.last_fetch_timestamp = data.get("timestamp", 0)
                logger.debug("Cached rates for %d sending countries", len(self.cached_rates))
                return data

            except json.JSONDecodeError as e:
                raise RewireResponseError(f"Failed to parse JSON: {str(e)}")

        except requests.RequestException as e:
            logger.error("Connection error fetching Rewire rates: %s", str(e))
            raise RewireConnectionError(f"Failed to connect to Rewire API: {str(e)}")

    def fetch_pricing(self) -> Dict[str, Any]:
        logger.info("Fetching Rewire public pricing from %s", self.PRICING_URL)
        try:
            resp = self.session.get(self.PRICING_URL, timeout=15)
            resp.raise_for_status()

            try:
                data = resp.json()
                logger.debug("Got pricing data with %d top-level keys", len(data))
                self.cached_fees = data
                return data

            except json.JSONDecodeError as e:
                raise RewireResponseError(f"Failed to parse JSON pricing data: {str(e)}")

        except requests.RequestException as e:
            logger.error("Connection error fetching Rewire pricing: %s", str(e))
            raise RewireConnectionError(f"Failed to connect to Rewire pricing API: {str(e)}")

    def _ensure_rates_loaded(self):
        if not self.cached_rates:
            self.fetch_rates()

    def _get_receive_currency(self, receive_country: str) -> str:
        return self.COUNTRY_TO_CURRENCY.get(receive_country, "USD")

    def _get_fee_for_corridor(
        self, send_currency: str, receive_currency: str, send_amount: float
    ) -> float:
        if not self.cached_fees:
            self.fetch_pricing()

        if send_currency not in self.cached_fees:
            raise RewireResponseError(f"No pricing info for send currency '{send_currency}'")

        corridor_info = self.cached_fees[send_currency].get(receive_currency)
        if not corridor_info:
            raise RewireResponseError(
                f"No pricing info for corridor {send_currency}->{receive_currency}"
            )

        for tier in corridor_info:
            tier_from = tier.get("from", 0)
            tier_to = tier.get("to", float("inf"))
            if tier_from <= send_amount <= tier_to:
                return float(tier.get("fee", 0.0))

        raise RewireResponseError(
            f"No matching fee tier found for corridor {send_currency}->{receive_currency}"
        )

    def is_corridor_supported(self, send_country: str, receive_country: str) -> bool:
        if (send_country, receive_country) in self.SUPPORTED_CORRIDORS:
            return True

        self._ensure_rates_loaded()
        if send_country not in self.cached_rates:
            return False

        rcurr = self._get_receive_currency(receive_country)
        if rcurr in self.cached_rates[send_country]:
            self.SUPPORTED_CORRIDORS.append((send_country, receive_country))
            return True

        return False

    def get_supported_countries(self) -> List[str]:
        self._ensure_rates_loaded()
        countries = list(self.cached_rates.keys())
        countries.sort()
        return countries

    def get_supported_currencies(self) -> List[str]:
        return sorted(list(set(self.COUNTRY_TO_CURRENCY.values())))

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
        try:
            self._ensure_rates_loaded()
        except (RewireConnectionError, RewireResponseError) as e:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Failed to fetch rates: {str(e)}",
                    "send_amount": float(amount),
                    "send_currency": source_currency,
                    "destination_currency": dest_currency,
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )

        if source_country not in self.cached_rates:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Unsupported source country: {source_country}",
                    "send_amount": float(amount),
                    "send_currency": source_currency,
                    "destination_currency": dest_currency,
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )

        country_rates = self.cached_rates[source_country]
        if dest_currency not in country_rates:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Unsupported corridor: {source_country} to {dest_currency}",
                    "send_amount": float(amount),
                    "send_currency": source_currency,
                    "destination_currency": dest_currency,
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )

        rate_info = country_rates[dest_currency]
        buy_rate = rate_info.get("buy", 0.0)

        source_rate_info = self.cached_rates[source_country][source_currency]
        sell_rate = source_rate_info.get("sell", 0.0)

        if sell_rate == 0 or buy_rate == 0:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Invalid exchange rate (zero) for {source_country} to {dest_currency}",
                    "send_amount": float(amount),
                    "send_currency": source_currency,
                    "destination_currency": dest_currency,
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )

        common_currency_amount = float(amount) / sell_rate
        destination_amount = common_currency_amount / buy_rate
        exchange_rate = destination_amount / float(amount)

        try:
            fee = self._get_fee_for_corridor(source_currency, dest_currency, float(amount))
        except (RewireConnectionError, RewireResponseError) as e:
            logger.warning(f"Could not fetch fee information: {str(e)}. Setting fee to None.")
            fee = None

            return self.standardize_response(
                {
                    "success": True,
                    "error_message": f"Fee information not available: {str(e)}",
                    "send_amount": float(amount),
                    "send_currency": source_currency,
                    "destination_currency": dest_currency,
                    "destination_amount": destination_amount,
                    "exchange_rate": exchange_rate,
                    "fee": 0.0,
                    "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                    "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
                }
            )

        return self.standardize_response(
            {
                "success": True,
                "error_message": None,
                "send_amount": float(amount),
                "send_currency": source_currency,
                "destination_currency": dest_currency,
                "destination_amount": destination_amount,
                "exchange_rate": exchange_rate,
                "fee": fee,
                "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
                "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
            }
        )

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_country: str,
        send_currency: str,
        receive_currency: str,
        **kwargs,
    ) -> Dict[str, Any]:
        return self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            dest_currency=receive_currency,
            source_country=send_country,
            dest_country=kwargs.get("receive_country", ""),
            payment_method=kwargs.get("payment_method"),
            delivery_method=kwargs.get("delivery_method"),
        )

    def close(self):
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
