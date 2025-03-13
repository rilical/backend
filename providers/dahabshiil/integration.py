"""
Dahabshiil provider integration module.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

from providers.base.provider import RemittanceProvider

from .exceptions import DahabshiilApiError

logger = logging.getLogger(__name__)


class DahabshiilProvider(RemittanceProvider):
    """
    Provider implementation for Dahabshiil, an international remittance service.
    """

    BASE_URL = "https://apigw-us.dahabshiil.com/remit/transaction"
    GET_CHARGES_ENDPOINT = "/get-charges-anonymous"
    # Default delivery time in minutes (24 hours)
    DEFAULT_DELIVERY_TIME = 1440

    def __init__(self, name="dahabshiil"):
        """Initialize the Dahabshiil provider."""
        super().__init__(name=name, base_url=self.BASE_URL)
        self.session = requests.Session()

        # Update headers based on actual request headers
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/18.3 Safari/605.1.15"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Origin": "https://www.dahabshiil.com",
                "Priority": "u=3, i",
            }
        )

        self.logger = logging.getLogger(f"providers.{name}")

    def get_delivery_methods(
        self,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str,
    ) -> List[Dict[str, Any]]:
        """
        Return the list of delivery methods (bank deposit, mobile wallet, etc.).
        """
        return [
            {
                "id": "Mobile Transfer",
                "name": "Mobile Transfer",
                "description": "Send to mobile wallet",
                "fee": 0.0,
                "delivery_time_minutes": self.DEFAULT_DELIVERY_TIME,
            },
            {
                "id": "Cash Pickup",
                "name": "Cash Pickup",
                "description": "Recipient picks up cash at agent location",
                "fee": 0.0,
                "delivery_time_minutes": self.DEFAULT_DELIVERY_TIME,
            },
        ]

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        dest_currency: str,
        source_country: str,
        dest_country: str,
        delivery_method: Optional[str] = None,
        payment_method: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get a quote for a money transfer from Dahabshiil.

        Args:
            amount: Amount to send (Decimal)
            source_currency: Source currency code (e.g., "USD")
            dest_currency: Destination currency code (e.g., "KES")
            source_country: Source country code (e.g., "US")
            dest_country: Destination country code (e.g., "KE")
            delivery_method: Method of delivery (default: Mobile Transfer)
            payment_method: Method of payment
            **kwargs: Additional parameters (e.g. include_raw=True)

        Returns:
            Dictionary containing aggregator-standard quote information.
        """
        # Default values
        if not delivery_method:
            delivery_method = "Mobile Transfer"

        # Default payment method
        if not payment_method:
            payment_method = "bank"

        # Local dictionary for initial result
        quote_result = {
            "success": False,
            "send_amount": float(amount),
            "source_currency": source_currency.upper(),
            "destination_currency": dest_currency.upper(),
            "exchange_rate": 0.0,
            "fee": 0.0,
            "destination_amount": 0.0,
            "delivery_method": delivery_method,
            "payment_method": payment_method,
            "delivery_time_minutes": self.DEFAULT_DELIVERY_TIME,
            "error_message": None,
        }

        try:
            # Build query params based on the successful curl request
            params = {
                "source_country_code": source_country.upper(),
                "destination_country_iso2": dest_country.upper(),
                "amount_type": "SOURCE",
                "amount": f"{amount:.2f}",
                "destination_currency": dest_currency.upper(),
                "type": delivery_method,
            }

            self.logger.info(f"Dahabshiil request: {params}")

            # Perform the GET request
            response = self.session.get(
                f"{self.BASE_URL}{self.GET_CHARGES_ENDPOINT}", params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.logger.debug(f"Dahabshiil response: {data}")

            # Check for success based on the provided sample response
            if (
                data.get("status") == "Success"
                and data.get("code") == 200
                and "data" in data
                and "charges" in data["data"]
            ):
                charges = data["data"]["charges"]

                send_amount = Decimal(str(charges.get("source_amount", amount)))
                exchange_rate = Decimal(str(charges.get("rate", 0)))
                fee = Decimal(str(charges.get("commission", 0)))
                receive_amount = Decimal(str(charges.get("destination_amount", 0)))

                # Update quote result with successful response data
                quote_result.update(
                    {
                        "success": True,
                        "send_amount": float(send_amount),
                        "exchange_rate": float(exchange_rate),
                        "fee": float(fee),
                        "destination_amount": float(receive_amount),
                    }
                )

                # If aggregator wants raw response for debugging
                if kwargs.get("include_raw", False):
                    quote_result["raw_response"] = data
            else:
                # Fallback error if not success or missing data
                error_msg = data.get("message", "Unknown error from Dahabshiil")
                quote_result["error_message"] = error_msg

        except requests.exceptions.RequestException as exc:
            error_msg = f"Network/Request error: {exc}"
            self.logger.error(error_msg)
            quote_result["error_message"] = error_msg

        except (ValueError, KeyError, TypeError) as exc:
            error_msg = f"Response parsing error: {exc}"
            self.logger.error(error_msg)
            quote_result["error_message"] = error_msg

        except Exception as exc:
            error_msg = f"Unexpected error: {exc}"
            self.logger.error(error_msg)
            quote_result["error_message"] = error_msg

        # Return standardized response for the aggregator
        return self.standardize_response(
            raw_result=quote_result,
            provider_specific_data=kwargs.get("include_raw", False),
        )

    def get_exchange_rate(
        self, send_amount: Decimal, send_currency: str, target_currency: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Get current exchange rate for a currency pair using `get_quote`.

        Implementation adheres to the aggregator's expected method signature.
        """
        try:
            # Extract source and target countries from kwargs if provided, otherwise use defaults
            source_country = kwargs.get("source_country", "US")
            target_country = kwargs.get(
                "target_country",
                self._get_default_country_for_currency(target_currency),
            )

            # Call get_quote to obtain exchange rate information
            quote = self.get_quote(
                amount=send_amount,
                source_currency=send_currency,
                dest_currency=target_currency,
                source_country=source_country,
                dest_country=target_country,
            )

            # Return the standardized response as-is (it already contains all necessary fields)
            return quote

        except Exception as exc:
            logger.error(f"Failed to get exchange rate: {exc}", exc_info=True)
            # Return standardized error response
            error_result = {
                "provider_id": self.name,
                "success": False,
                "error_message": str(exc),
                "source_currency": send_currency,
                "destination_currency": target_currency,
                "exchange_rate": 0.0,
                "fee": 0.0,
                "send_amount": float(send_amount),
                "destination_amount": 0.0,
                "timestamp": datetime.now().isoformat(),
            }
            return error_result

    def _get_default_country_for_currency(self, currency_code: str) -> str:
        """Return a default country code for a given currency code."""
        currency_to_country = {
            "KES": "KE",  # Kenya
            "USD": "US",  # United States
            "GBP": "GB",  # United Kingdom
            "EUR": "DE",  # Germany/Eurozone
            "CAD": "CA",  # Canada
            "AUD": "AU",  # Australia
            "INR": "IN",  # India
            "NGN": "NG",  # Nigeria
            "UGX": "UG",  # Uganda
            "TZS": "TZ",  # Tanzania
            "ETB": "ET",  # Ethiopia
            "SOS": "SO",  # Somalia
            "DJF": "DJ",  # Djibouti
        }
        return currency_to_country.get(currency_code.upper(), "US")  # Default to US if not found

    def standardize_response(self, raw_result=None, provider_specific_data=False) -> Dict[str, Any]:
        """
        Standardize the response shape for aggregator usage.

        The standardized format matches the aggregator's expected schema.
        """
        if raw_result is None:
            raw_result = {}

        # Build the aggregator-standard dictionary
        standardized = {
            "provider_id": self.name,
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),
            "send_amount": raw_result.get("send_amount", 0.0),
            "source_currency": raw_result.get("source_currency", ""),
            "destination_amount": raw_result.get("destination_amount", 0.0),
            "destination_currency": raw_result.get("destination_currency", ""),
            "exchange_rate": raw_result.get("exchange_rate", 0.0),
            "fee": raw_result.get("fee", 0.0),
            "payment_method": raw_result.get("payment_method", "bank"),
            "delivery_method": raw_result.get("delivery_method", "Mobile Transfer"),
            "delivery_time_minutes": raw_result.get(
                "delivery_time_minutes", self.DEFAULT_DELIVERY_TIME
            ),
            "timestamp": raw_result.get("timestamp", datetime.now().isoformat()),
        }

        # Include raw response if requested
        if provider_specific_data and "raw_response" in raw_result:
            standardized["raw_response"] = raw_result["raw_response"]

        return standardized

    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
