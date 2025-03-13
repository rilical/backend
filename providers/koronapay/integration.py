"""
KoronaPay Provider Integration

This module provides integration with the KoronaPay remittance service.
It supports sending money from Europe to various countries with multiple payment methods.
"""

import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

from providers.base.provider import RemittanceProvider

from .exceptions import (
    KoronaPayAPIError,
    KoronaPayAuthError,
    KoronaPayCorridorError,
    KoronaPayError,
    KoronaPayPaymentMethodError,
    KoronaPayValidationError,
)
from .mapping import (
    get_country_id,
    get_currency_id,
    get_payment_method,
    get_receiving_method,
    get_supported_countries,
    get_supported_currencies,
    get_supported_payment_methods,
    get_supported_receiving_methods,
)

logger = logging.getLogger(__name__)


class KoronaPayProvider(RemittanceProvider):
    """
    KoronaPay integration for retrieving fees, exchange rates, and quotes.
    """

    BASE_URL = "https://koronapay.com/api"
    API_VERSION = "v2.138"

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the KoronaPay provider."""
        super().__init__(name="koronapay", base_url=self.BASE_URL)
        self.config = config or {}
        self.session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Set up the session with required headers."""
        self.session.headers.update(
            {
                "Accept": f"application/vnd.cft-data.{self.API_VERSION}+json",
                "Accept-Language": "en",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
                ),
                "x-application": "Qpay-Web/3.0",
            }
        )

    def _get_request_headers(self) -> Dict[str, str]:
        """Get additional headers for the API request."""
        return {
            "Request-ID": str(uuid.uuid4()),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    # ------------------------------------------------------------------------
    # Aggregator-Specific Helper: Standardize Response
    # ------------------------------------------------------------------------
    def standardize_response(
        self, raw_data: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Convert internal fields into aggregator-friendly keys:
          "provider_id", "success", "error_message",
          "send_amount", "source_currency",
          "destination_amount", "destination_currency",
          "exchange_rate", "fee", "payment_method",
          "delivery_method", "delivery_time_minutes", "timestamp",
          plus aggregator special keys "rate" (mirroring exchange_rate)
          and "target_currency" (mirroring destination_currency).
        """
        # aggregator might want "rate" in some tests:
        final_exchange_rate = raw_data.get("exchange_rate")
        final_rate = raw_data.get("rate")
        if final_rate is None:
            final_rate = final_exchange_rate

        # aggregator might want "target_currency" for get_exchange_rate calls:
        final_target_currency = raw_data.get("target_currency") or raw_data.get(
            "receive_currency", ""
        )

        standardized = {
            "provider_id": self.name,
            "success": raw_data.get("success", False),
            "error_message": raw_data.get("error_message"),
            "send_amount": raw_data.get("send_amount", 0.0),
            "source_currency": (raw_data.get("send_currency") or "").upper(),
            "destination_amount": raw_data.get("receive_amount"),
            "destination_currency": (raw_data.get("receive_currency") or "").upper(),
            "exchange_rate": final_exchange_rate,
            "fee": raw_data.get("fee", 0.0),
            "payment_method": raw_data.get("payment_method"),
            "delivery_method": raw_data.get("delivery_method"),
            "delivery_time_minutes": raw_data.get("delivery_time_minutes"),
            "timestamp": raw_data.get("timestamp", datetime.now().isoformat()),
            # aggregator might specifically look for these:
            "rate": final_rate,  # mirror exchange_rate
            "target_currency": final_target_currency.upper(),
        }

        if provider_specific_data and "raw_response" in raw_data:
            standardized["raw_response"] = raw_data["raw_response"]

        return standardized

    # ------------------------------------------------------------------------
    # Validation Helpers
    # ------------------------------------------------------------------------
    def _validate_currency(self, currency: str) -> str:
        """Validate and return KoronaPay internal currency ID."""
        currency_id = get_currency_id(currency)
        if not currency_id:
            raise KoronaPayValidationError(f"Unsupported currency: {currency}")
        return currency_id

    def _validate_country(self, country: str) -> str:
        """Validate and return KoronaPay internal country ID."""
        country_id = get_country_id(country)
        if not country_id:
            raise KoronaPayValidationError(f"Unsupported country: {country}")
        return country_id

    def _validate_payment_method(self, method: str) -> str:
        """Validate and return KoronaPay internal payment method."""
        payment_method = get_payment_method(method)
        if not payment_method:
            raise KoronaPayPaymentMethodError(f"Unsupported payment method: {method}")
        return payment_method

    def _validate_receiving_method(self, method: str) -> str:
        """Validate and return KoronaPay internal receiving method."""
        receiving_method = get_receiving_method(method)
        if not receiving_method:
            raise KoronaPayPaymentMethodError(f"Unsupported receiving method: {method}")
        return receiving_method

    # ------------------------------------------------------------------------
    # Public aggregator methods
    # ------------------------------------------------------------------------
    def get_supported_countries(self) -> List[str]:
        """Get list of supported country codes."""
        return get_supported_countries()

    def get_supported_currencies(self) -> List[str]:
        """Get list of supported currency codes."""
        return get_supported_currencies()

    def get_supported_payment_methods(self) -> List[str]:
        """Get list of supported payment methods."""
        return get_supported_payment_methods()

    def get_supported_receiving_methods(self) -> List[str]:
        """Get list of supported receiving methods."""
        return get_supported_receiving_methods()

    def get_quote(
        self,
        send_amount: Optional[float] = None,
        receive_amount: Optional[float] = None,
        send_currency: str = "EUR",
        receive_currency: str = "USD",
        send_country: str = "ESP",
        receive_country: str = "TUR",
        payment_method: str = "debit_card",
        receiving_method: str = "cash",
        **kwargs,
    ) -> Dict[str, Any]:
        """Get a standardized quote for a money transfer."""
        # Must have either send_amount or receive_amount
        if send_amount is None and receive_amount is None:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": "Either send_amount or receive_amount must be provided",
                }
            )

        # Decide which amount is provided
        is_amount_receiving = send_amount is None
        raw_amount = receive_amount if is_amount_receiving else send_amount
        amount_dec = Decimal(str(raw_amount))

        try:
            # Validate the aggregator-friendly inputs
            validated_send_currency = self._validate_currency(send_currency)
            validated_receive_currency = self._validate_currency(receive_currency)
            validated_send_country = self._validate_country(send_country)
            validated_receive_country = self._validate_country(receive_country)
            validated_payment_method = self._validate_payment_method(payment_method)
            validated_receiving_method = self._validate_receiving_method(receiving_method)

            # Prepare the GET /transfers/tariffs call
            # In practice, you'd have a function, e.g. get_tariffs(...),
            # but we'll inline or call that method here for brevity
            tariff = self._get_tariff_info(
                sending_country=validated_send_country,
                receiving_country=validated_receive_country,
                sending_currency=validated_send_currency,
                receiving_currency=validated_receive_currency,
                amount=amount_dec,
                is_amount_receiving=is_amount_receiving,
                payment_method=validated_payment_method,
                receiving_method=validated_receiving_method,
            )

            # If success, build aggregator-friendly local result
            local_result = {
                "success": True,
                "send_amount": float(tariff["sending_amount"]),
                "send_currency": send_currency,  # aggregator expects ISO code
                "receive_amount": float(tariff["receiving_amount"]),
                "receive_currency": receive_currency,  # aggregator expects ISO code
                "exchange_rate": float(tariff["exchange_rate"]),
                "fee": float(tariff["fee"]),
                "total_cost": float(tariff["total_cost"]),
                "payment_method": payment_method,
                "delivery_method": receiving_method,
                "timestamp": tariff["timestamp"],
            }
            # Optionally add raw response
            if kwargs.get("include_raw", False):
                local_result["raw_response"] = tariff

            return self.standardize_response(
                local_result, provider_specific_data=kwargs.get("include_raw", False)
            )

        except KoronaPayError as e:
            logger.error(f"Failed to get quote: {e}")
            return self.standardize_response({"success": False, "error_message": str(e)})
        except Exception as e:
            logger.error(f"Unexpected error getting quote: {e}")
            return self.standardize_response(
                {"success": False, "error_message": f"Unexpected error: {str(e)}"}
            )

    def get_exchange_rate(
        self,
        send_currency: str,
        receive_currency: str,
        send_country: str = "ESP",
        receive_country: str = "TUR",
        amount: Decimal = Decimal("1000"),
    ) -> Dict[str, Any]:
        """Get exchange rate for a currency pair."""
        try:
            # Reuse the same tariff logic, assuming send_amount approach
            tariff = self._get_tariff_info(
                sending_country=self._validate_country(send_country),
                receiving_country=self._validate_country(receive_country),
                sending_currency=self._validate_currency(send_currency),
                receiving_currency=self._validate_currency(receive_currency),
                amount=amount,
                is_amount_receiving=False,
                payment_method="debitCard",  # default
                receiving_method="cash",  # default
            )

            # aggregator test might look for "rate" instead of "exchange_rate"
            rate_info = {
                "success": True,
                "error_message": None,
                "source_currency": send_currency,
                "send_currency": send_currency,  # Include both for standardization
                "target_currency": receive_currency,
                "receive_currency": receive_currency,  # Include both for standardization
                "rate": float(tariff["exchange_rate"]),
                "exchange_rate": float(tariff["exchange_rate"]),  # Include both for standardization
                "fee": float(tariff["fee"]),
                "send_amount": float(tariff["sending_amount"]),
                "receive_amount": float(tariff["receiving_amount"]),
                "timestamp": tariff["timestamp"],
            }
            return self.standardize_response(rate_info)

        except KoronaPayError as e:
            logger.error(f"Failed to get exchange rate: {e}")
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": str(e),
                    "source_currency": send_currency,
                    "target_currency": receive_currency,
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error getting exchange rate: {e}")
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Unexpected error: {str(e)}",
                    "source_currency": send_currency,
                    "target_currency": receive_currency,
                }
            )

    # ------------------------------------------------------------------------
    # Internal function to request tariff info from KoronaPay
    # ------------------------------------------------------------------------
    def _get_tariff_info(
        self,
        sending_country: str,
        receiving_country: str,
        sending_currency: str,
        receiving_currency: str,
        amount: Decimal,
        is_amount_receiving: bool,
        payment_method: str,
        receiving_method: str,
    ) -> Dict[str, Any]:
        """Get tariff information from KoronaPay API."""
        try:
            # Build query
            params = {
                "sendingCountryId": sending_country,
                "receivingCountryId": receiving_country,
                "sendingCurrencyId": sending_currency,
                "receivingCurrencyId": receiving_currency,
                "paymentMethod": payment_method,
                "receivingMethod": receiving_method,
                "paidNotificationEnabled": "false",
            }
            # handle which amount param
            amount_key = "receivingAmount" if is_amount_receiving else "sendingAmount"
            params[amount_key] = str(int(amount * 100))  # in "cents"

            response = self.session.get(
                f"{self.BASE_URL}/transfers/tariffs",
                params=params,
                headers=self._get_request_headers(),
                timeout=30,
            )
            if response.status_code != 200:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_msg)
                except:
                    pass
                raise KoronaPayAPIError(error_msg, status_code=response.status_code)

            try:
                tariffs = response.json()
            except json.JSONDecodeError as e:
                raise KoronaPayAPIError(f"Invalid JSON response: {str(e)}")

            if not tariffs:
                raise KoronaPayAPIError("No tariffs available for this corridor")

            # If we get a list, we handle the first item:
            if isinstance(tariffs, list):
                tariff_data = tariffs[0]
            elif isinstance(tariffs, dict):
                tariff_data = tariffs
            else:
                raise KoronaPayAPIError("Invalid tariff response format")

            required_fields = [
                "sendingAmount",
                "receivingAmount",
                "exchangeRate",
                "sendingCommission",
            ]
            missing = [f for f in required_fields if f not in tariff_data]
            if missing:
                raise KoronaPayAPIError(f"Missing fields in tariff: {', '.join(missing)}")

            sending_amount_int = int(tariff_data["sendingAmount"])  # in cents
            receiving_amount_int = int(tariff_data["receivingAmount"])
            commission_int = int(tariff_data["sendingCommission"])

            local_tariff = {
                "success": True,
                "sending_amount": Decimal(sending_amount_int) / 100,
                "receiving_amount": Decimal(receiving_amount_int) / 100,
                "exchange_rate": Decimal(str(tariff_data["exchangeRate"])),
                "fee": Decimal(commission_int) / 100,
                "total_cost": Decimal(sending_amount_int) / 100,  # sendingAmount includes principal
                "timestamp": datetime.now().isoformat(),
            }
            return local_tariff

        except requests.exceptions.RequestException as rexc:
            logger.error(f"KoronaPay tariff request failed: {rexc}")
            raise KoronaPayAPIError(f"Tariff request error: {str(rexc)}")
        except (ValueError, KeyError, TypeError) as exc:
            logger.error(f"Error parsing KoronaPay tariff data: {exc}")
            raise KoronaPayAPIError(f"Error parsing tariff data: {str(exc)}")

    def close(self):
        """Close the session if it exists."""
        if self.session:
            self.session.close()
