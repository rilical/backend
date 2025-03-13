"""
Intermex Provider Integration

This module provides integration with the Intermex remittance service.
It supports sending money from the US to various countries with multiple payment methods.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

from providers.base.provider import RemittanceProvider

from .exceptions import IntermexAPIError, IntermexAuthError, IntermexError, IntermexValidationError
from .mapping import map_country_code, map_delivery_method, map_payment_method, validate_corridor

logger = logging.getLogger(__name__)


class IntermexProvider(RemittanceProvider):
    """
    Intermex integration for retrieving fees, exchange rates, and quotes.

    - Payment methods: debitCard, creditCard, bankAccount, cash, ACH, wireTransfer
    - Delivery methods: bankDeposit, cashPickup, mobileWallet, homeDelivery
    """

    BASE_URL = "https://api.imxi.com"  # Corrected endpoint for live API access
    API_VERSION = "v1"
    # Payment methods
    PAYMENT_METHODS = {
        "debitCard": "Debit Card",
        "creditCard": "Credit Card",
        "bankAccount": "Bank Account",
        "cash": "Cash",
        "ACH": "ACH Transfer",
        "wireTransfer": "Wire Transfer",
    }

    # Receiving methods
    RECEIVING_METHODS = {
        "bankDeposit": "Bank Deposit",
        "cashPickup": "Cash Pickup",
        "mobileWallet": "Mobile Wallet",
        "homeDelivery": "Home Delivery",
    }

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the Intermex provider."""
        super().__init__(name="intermex", base_url=self.BASE_URL)
        self.config = config or {}
        self.session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Set up the session with required headers."""
        self.session.headers.update(
            {
                "Pragma": "no-cache",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Origin": "https://www.intermexonline.com",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
                ),
                "Referer": "https://www.intermexonline.com/",
            }
        )

    def _get_request_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Ocp-Apim-Subscription-Key": self.config.get(
                "api_key", "2162a586e2164623a1cd9b6b2d300b4c"
            ),
            "PartnerId": "1",
            "ChannelId": "1",
            "LanguageId": "1",
            "Priority": "u=3, i",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
        }

    # -------------------------
    # Aggregator Helper Methods
    # -------------------------
    def standardize_response(
        self, raw_data: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Convert local result dict into aggregator-friendly fields:
          "provider_id", "success", "error_message",
          "send_amount", "source_currency",
          "destination_amount", "destination_currency",
          "exchange_rate", "rate", "target_currency",
          "fee", "payment_method", "delivery_method",
          "delivery_time_minutes", "timestamp", ...
        """
        # aggregator might want "rate" in some tests; we mirror "exchange_rate"
        final_exchange_rate = raw_data.get("exchange_rate")
        final_rate = raw_data.get("rate")
        if final_rate is None:
            final_rate = final_exchange_rate

        # aggregator might want "target_currency" (mirroring destination currency)
        final_target_currency = (
            raw_data.get("target_currency") or raw_data.get("receive_currency") or ""
        )

        # Make sure we have the source_currency
        final_source_currency = (
            raw_data.get("source_currency") or raw_data.get("send_currency") or ""
        )

        standardized = {
            "provider_id": self.name,
            "success": raw_data.get("success", False),
            "error_message": raw_data.get("error_message"),
            "send_amount": raw_data.get("send_amount", 0.0),
            "source_currency": final_source_currency.upper(),
            "destination_amount": raw_data.get("receive_amount"),
            "destination_currency": (raw_data.get("receive_currency") or "").upper(),
            "exchange_rate": final_exchange_rate,
            "rate": final_rate,
            "target_currency": final_target_currency.upper() if final_target_currency else "",
            "fee": raw_data.get("fee", 0.0),
            "payment_method": raw_data.get("payment_method"),
            "delivery_method": raw_data.get("delivery_method"),
            "delivery_time_minutes": raw_data.get("delivery_time_minutes"),
            "timestamp": raw_data.get("timestamp", datetime.now().isoformat()),
        }

        # Include raw response if aggregator wants it
        if provider_specific_data and "raw_response" in raw_data:
            standardized["raw_response"] = raw_data["raw_response"]

        return standardized

    # ---------------------------
    # Public Aggregator Methods
    # ---------------------------
    def get_supported_countries(self) -> List[str]:
        """Get list of supported destination countries."""
        return list(self.SUPPORTED_COUNTRIES.keys())

    def get_supported_currencies(self) -> List[str]:
        """Get list of supported currencies."""
        return list(self.SUPPORTED_CURRENCIES.keys())

    def get_supported_payment_methods(self) -> List[str]:
        """Get list of supported payment methods."""
        return list(self.PAYMENT_METHODS.keys())

    def get_supported_receiving_methods(self) -> List[str]:
        """Get list of supported receiving methods."""
        return list(self.RECEIVING_METHODS.keys())

    def get_delivery_methods(
        self,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str,
    ) -> Dict[str, Any]:
        """
        Fetch possible delivery methods for a corridor (aggregator style).
        """
        try:
            # corridor validation
            is_valid, error = validate_corridor(
                source_country, source_currency, dest_country, dest_currency
            )
            if not is_valid:
                return {"success": False, "error": error, "provider": self.name}

            mapped_source = "USA" if source_country.upper() == "US" else source_country
            mapped_dest = dest_country

            params = {
                "DestCountryAbbr": mapped_dest,
                "DestCurrency": dest_currency.upper(),
                "OriCountryAbbr": mapped_source,
                "OriStateAbbr": "NY",  # Default to New York
                "ChannelId": "1",
            }

            response = self.session.get(
                f"{self.BASE_URL}/pricing/api/deliveryandpayments",
                params=params,
                headers=self._get_request_headers(),
                timeout=30,
            )

            if response.status_code != 200:
                raise IntermexAPIError(
                    f"API request failed with status {response.status_code}",
                    status_code=response.status_code,
                    response=response.json() if response.text else None,
                )

            data = response.json()

            # Convert to aggregator-friendly structures
            delivery_methods = []
            if "deliveryMethodsList" in data:
                for method in data["deliveryMethodsList"]:
                    delivery_methods.append(
                        {
                            "id": method.get("tranTypeId"),
                            "name": method.get("tranTypeName"),
                            "type": method.get("deliveryMethod"),
                            "estimated_minutes": 60,  # Default to 60 minutes
                            "description": "",
                            "is_default": method.get("isSelected", False),
                        }
                    )

            # Extract payment methods if present
            payment_methods = []
            if "paymentMethods" in data:
                for method in data["paymentMethods"]:
                    payment_methods.append(
                        {
                            "id": method.get("senderPaymentMethodId"),
                            "name": method.get("senderPaymentMethodName"),
                            "fee": method.get("feeAmount", 0.0),
                            "is_available": method.get("isAvailable", False),
                        }
                    )

            return {
                "success": True,
                "delivery_methods": delivery_methods,
                "payment_methods": payment_methods,
                "provider": self.name,
                "timestamp": datetime.now().isoformat(),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Intermex API request failed: {e}")
            return {
                "success": False,
                "error": f"API request failed: {str(e)}",
                "provider": self.name,
            }
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing Intermex response: {e}")
            return {
                "success": False,
                "error": f"Error parsing response: {str(e)}",
                "provider": self.name,
            }

    def get_quote(
        self,
        send_amount: Optional[float] = None,
        receive_amount: Optional[float] = None,
        send_currency: str = "USD",
        receive_currency: str = "MXN",
        send_country: str = "US",
        receive_country: str = "MX",
        payment_method: str = "debitCard",
        delivery_method: str = "bankDeposit",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get a quote for a money transfer from Intermex in aggregator-ready format.
        """
        # Validate that at least one of send_amount or receive_amount is provided
        if send_amount is None and receive_amount is None:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": "Either send_amount or receive_amount must be provided",
                }
            )

        # corridor validation
        is_valid, error = validate_corridor(
            send_country, send_currency, receive_country, receive_currency
        )
        if not is_valid:
            return self.standardize_response({"success": False, "error_message": error})

        # Validate payment and receiving methods
        if payment_method not in self.PAYMENT_METHODS:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Invalid or unsupported payment method: {payment_method}",
                }
            )

        if delivery_method not in self.RECEIVING_METHODS:
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": f"Invalid or unsupported receiving method: {delivery_method}",
                }
            )

        # Decide which amount is provided
        is_amount_receiving = send_amount is None
        raw_amount = receive_amount if is_amount_receiving else send_amount
        if raw_amount is not None:
            amt_dec = Decimal(str(raw_amount))
            # Arbitrary validation: 0 < amount <= 999999.99
            if amt_dec <= 0 or amt_dec > Decimal("999999.99"):
                return self.standardize_response(
                    {
                        "success": False,
                        "error_message": f"Invalid send/receive amount: {raw_amount}",
                    }
                )

        # Map the delivery method to TranTypeId
        tran_type_id = "1"  # Default Cash Pickup
        if delivery_method == "bankDeposit":
            tran_type_id = "3"

        # Map payment method to SenderPaymentMethodId
        payment_method_id = "3"  # Default Debit Card
        if payment_method == "creditCard":
            payment_method_id = "4"

        # For API, convert country codes if needed
        mapped_send_country = "USA" if send_country.upper() == "US" else send_country

        # Build URL / parameters using the real Intermex API endpoint
        endpoint = f"{self.BASE_URL}/pricing/api/v2/feesrates"
        params = {
            "DestCountryAbbr": receive_country,
            "DestCurrency": receive_currency.upper(),
            "OriCountryAbbr": mapped_send_country,
            "OriStateAbbr": "NY",  # Default to New York
            "StyleId": "3",  # Default style
            "TranTypeId": tran_type_id,
            "DeliveryType": "W",  # Default delivery type
            "OriCurrency": send_currency.upper(),
            "ChannelId": "1",
            "SenderPaymentMethodId": payment_method_id,
        }

        # Set the appropriate amount parameter
        if is_amount_receiving:
            params["OriAmount"] = "0"
            params["DestAmount"] = str(receive_amount)
        else:
            params["OriAmount"] = str(send_amount)
            params["DestAmount"] = "0"

        try:
            # Add required headers for the Intermex API
            headers = {
                "Pragma": "no-cache",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Origin": "https://www.intermexonline.com",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
                "Referer": "https://www.intermexonline.com/",
                "Ocp-Apim-Subscription-Key": self.config.get(
                    "api_key", "2162a586e2164623a1cd9b6b2d300b4c"
                ),
                "LanguageId": "1",
            }

            response = self.session.get(endpoint, params=params, headers=headers)
            if response.status_code != 200:
                error_msg = (
                    f"API request failed with status {response.status_code}: {response.text}"
                )
                logger.error(error_msg)
                return self.standardize_response({"success": False, "error_message": error_msg})

            quote_data = response.json()
            if "error" in quote_data:
                error_msg = f"API returned an error: {quote_data['error']}"
                logger.error(error_msg)
                return self.standardize_response({"success": False, "error_message": error_msg})

            # Build aggregator-friendly result using the actual response structure
            local_result = {
                "success": True,
                "send_amount": float(quote_data.get("origAmount", 0.0)),
                "send_currency": send_currency,
                "receive_amount": float(quote_data.get("destAmount", 0.0)),
                "receive_currency": receive_currency,
                "exchange_rate": float(quote_data.get("rate", 0.0)),
                "fee": float(quote_data.get("feeAmount", 0.0)),
                "total_cost": float(quote_data.get("totalAmount", 0.0)),
                "payment_method": payment_method,
                "delivery_method": delivery_method,
                "timestamp": datetime.now().isoformat(),
            }

            # Extract available payment methods if present
            if "paymentMethods" in quote_data and quote_data["paymentMethods"]:
                payment_methods = {}
                for method in quote_data["paymentMethods"]:
                    method_id = str(method.get("senderPaymentMethodId"))
                    method_name = method.get("senderPaymentMethodName")
                    fee = method.get("feeAmount", 0.0)
                    payment_methods[method_id] = {"name": method_name, "fee": fee}
                local_result["available_payment_methods"] = payment_methods

            # Optionally attach raw response
            if kwargs.get("include_raw", False):
                local_result["raw_response"] = quote_data

            return self.standardize_response(
                local_result, provider_specific_data=kwargs.get("include_raw", False)
            )

        except Exception as exc:
            error_msg = f"Failed to get quote: {str(exc)}"
            logger.error(error_msg)
            return self.standardize_response({"success": False, "error_message": error_msg})

    def get_exchange_rate(
        self,
        send_currency: str,
        receive_currency: str,
        send_country: str = "US",
        receive_country: str = "MX",
        amount: Decimal = Decimal("1000"),
    ) -> Dict[str, Any]:
        """
        Get aggregator-friendly dictionary with minimal fields for exchange rate tests.
        """
        try:
            # Map the country code for the API
            mapped_send_country = "USA" if send_country.upper() == "US" else send_country

            # Build endpoint URL and parameters for direct API call
            endpoint = f"{self.BASE_URL}/pricing/api/v2/feesrates"
            params = {
                "DestCountryAbbr": receive_country,
                "DestCurrency": receive_currency.upper(),
                "OriCountryAbbr": mapped_send_country,
                "OriStateAbbr": "NY",  # Default to New York
                "StyleId": "3",
                "TranTypeId": "1",  # Default to Cash Pickup
                "DeliveryType": "W",
                "OriCurrency": send_currency.upper(),
                "ChannelId": "1",
                "OriAmount": str(amount),
                "DestAmount": "0",
                "SenderPaymentMethodId": "3",  # Default to Debit Card
            }

            # Add required headers for the Intermex API
            headers = {
                "Pragma": "no-cache",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Origin": "https://www.intermexonline.com",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
                "Referer": "https://www.intermexonline.com/",
                "Ocp-Apim-Subscription-Key": self.config.get(
                    "api_key", "2162a586e2164623a1cd9b6b2d300b4c"
                ),
                "LanguageId": "1",
            }

            response = self.session.get(endpoint, params=params, headers=headers)
            if response.status_code != 200:
                error_msg = (
                    f"API request failed with status {response.status_code}: {response.text}"
                )
                logger.error(error_msg)
                return self.standardize_response(
                    {
                        "success": False,
                        "error_message": error_msg,
                        "source_currency": send_currency,
                        "target_currency": receive_currency,
                    }
                )

            data = response.json()

            # Format into aggregator-friendly response
            rate_info = {
                "success": True,
                "error_message": None,
                "source_currency": send_currency,
                "send_currency": send_currency,
                "target_currency": receive_currency,
                "receive_currency": receive_currency,
                "rate": float(data.get("rate", 0.0)),
                "fee": float(data.get("feeAmount", 0.0)),
                "send_amount": float(data.get("origAmount", 0.0)),
                "receive_amount": float(data.get("destAmount", 0.0)),
                "timestamp": datetime.now().isoformat(),
            }

            return self.standardize_response(rate_info)

        except Exception as exc:
            logger.error(f"Failed to get exchange rate: {exc}")
            return self.standardize_response(
                {
                    "success": False,
                    "error_message": str(exc),
                    "source_currency": send_currency,
                    "target_currency": receive_currency,
                }
            )

    def close(self):
        """Close the underlying HTTP session if needed."""
        if self.session:
            self.session.close()
