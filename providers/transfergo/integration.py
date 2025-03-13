"""
TransferGo provider implementation - aggregator-ready version.

This module implements a provider for TransferGo that follows the aggregator pattern.
It does not use any fallback or mock data: if the TransferGo API call fails or the corridor
is unsupported, it returns success=False with an error_message. Otherwise, it returns real
data from TransferGo in the standard aggregator format.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import base provider class and exceptions
from providers.base.provider import RemittanceProvider
from providers.transfergo.exceptions import (
    TransferGoAuthenticationError,
    TransferGoConnectionError,
    TransferGoError,
    TransferGoRateLimitError,
    TransferGoValidationError,
)

# Import mappings and utility functions
from providers.transfergo.transfergo_mappings import (
    API_CONFIG,
    DEFAULT_VALUES,
    DELIVERY_METHODS,
    PAYMENT_METHODS,
    get_delivery_methods_for_country,
    get_payment_methods_for_country,
    guess_country_for_currency,
    is_corridor_supported,
    parse_delivery_time,
)

logger = logging.getLogger(__name__)


class TransferGoProvider(RemittanceProvider):
    """
    Aggregator-ready TransferGo integration.

    No fallback or mock data is used: if TransferGo's API call fails
    or a corridor is unsupported, returns success=False with an error_message.
    Otherwise returns real data from TransferGo in aggregator-standard format.

    Usage:
        provider = TransferGoProvider()
        quote = provider.get_quote(
            amount=Decimal("1000"),
            source_currency="EUR",
            destination_currency="UAH",
            source_country="DE",
            destination_country="UA"
        )
    """

    # Base URL for TransferGo
    BASE_URL = API_CONFIG["base_url"]

    # Default values
    DEFAULT_PAYMENT_METHOD = DEFAULT_VALUES["payment_method"]
    DEFAULT_DELIVERY_METHOD = DEFAULT_VALUES["delivery_method"]
    DEFAULT_DELIVERY_TIME = DEFAULT_VALUES["delivery_time_minutes"]

    def __init__(self, user_agent: Optional[str] = None, timeout: int = API_CONFIG["timeout"]):
        """
        Initialize the aggregator-friendly TransferGo provider.

        Args:
            user_agent: Custom user agent string (optional)
            timeout: Request timeout in seconds
        """
        super().__init__(name="transfergo", base_url=self.BASE_URL)
        self.timeout = timeout
        self.user_agent = user_agent or API_CONFIG["user_agent"]

        self.session = requests.Session()
        self._configure_session()

    def _configure_session(self):
        """Configure the requests session with headers and retry logic."""
        self.session.headers.update({"User-Agent": self.user_agent, **API_CONFIG["headers"]})

        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def standardize_response(
        self, raw_result: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Convert a raw result dictionary into aggregator's standard shape.

        Args:
            raw_result: Raw response from the provider
            provider_specific_data: Whether to include provider-specific data

        Returns:
            Standardized response dictionary
        """
        now_ts = datetime.utcnow().isoformat()
        standardized = {
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

        # Preserve available delivery methods if present
        if "available_delivery_methods" in raw_result and raw_result["available_delivery_methods"]:
            delivery_methods = raw_result["available_delivery_methods"]
            logger.debug(
                f"Preserving {len(delivery_methods)} delivery methods in standardized response"
            )
            standardized["available_delivery_methods"] = delivery_methods

        # Preserve available payment methods if present
        if "available_payment_methods" in raw_result and raw_result["available_payment_methods"]:
            payment_methods = raw_result["available_payment_methods"]
            logger.debug(
                f"Preserving {len(payment_methods)} payment methods in standardized response"
            )
            standardized["available_payment_methods"] = payment_methods

        # Include raw response if requested
        if provider_specific_data and "raw_response" in raw_result:
            standardized["raw_response"] = raw_result["raw_response"]

        return standardized

    def _request_quotes(
        self,
        from_country: str,
        to_country: str,
        from_currency: str,
        to_currency: str,
        amount: Decimal,
        calc_base: str = "sendAmount",
        business: int = 0,
    ) -> Dict[str, Any]:
        """
        Request quotes from TransferGo API.

        Args:
            from_country: Source country code (ISO-2)
            to_country: Destination country code (ISO-2)
            from_currency: Source currency code (ISO-3)
            to_currency: Destination currency code (ISO-3)
            amount: Amount to transfer
            calc_base: Calculation base ('sendAmount' or 'receiveAmount')
            business: Business account flag (0 or 1)

        Returns:
            API response as Dict
        """
        url = f"{self.BASE_URL}/api/booking/quotes"
        params = {
            "fromCurrencyCode": from_currency,
            "toCurrencyCode": to_currency,
            "fromCountryCode": from_country,
            "toCountryCode": to_country,
            "amount": f"{amount:.2f}",
            "calculationBase": calc_base,
            "business": business,
        }

        try:
            response = self.session.get(url, params=params)

            # Handle non-2xx responses
            if not response.ok:
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        err_msg = error_data.get("error", {}).get("message", "Unknown error")
                    else:
                        err_msg = str(error_data)
                except (ValueError, AttributeError):
                    # Handle case where response is not valid JSON
                    err_msg = f"Invalid response: {response.text[:100]}..."

                # Handle specific error types
                if response.status_code == 401:
                    raise TransferGoAuthenticationError(f"Authentication error: {err_msg}")
                elif response.status_code == 429:
                    raise TransferGoRateLimitError("Rate limit exceeded")
                elif response.status_code == 422:
                    return {
                        "success": False,
                        "error_message": f"Validation error: Corridor not supported or invalid parameters",
                    }
                else:
                    raise TransferGoError(f"API error ({response.status_code}): {err_msg}")

            # Parse successful response
            data = response.json()
            return data

        except requests.RequestException as e:
            raise TransferGoConnectionError(f"Connection error: {str(e)}")
        except ValueError as e:
            raise TransferGoError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected TransferGo error: {str(e)}", exc_info=True)
            return {"success": False, "error_message": f"Unexpected error: {str(e)}"}

    def validate_corridor(
        self,
        source_country: str,
        source_currency: str,
        destination_country: str,
        destination_currency: str,
    ) -> bool:
        """
        Validate if a corridor is supported by TransferGo.

        Args:
            source_country: ISO country code of the source country
            source_currency: ISO currency code of the source currency
            destination_country: ISO country code of the destination country
            destination_currency: ISO currency code of the destination currency

        Returns:
            True if the corridor is supported, False otherwise

        Raises:
            TransferGoValidationError: If the corridor is not supported
        """
        if not is_corridor_supported(
            source_country, source_currency, destination_country, destination_currency
        ):
            error_message = (
                f"Unsupported corridor: {source_country}({source_currency}) to "
                f"{destination_country}({destination_currency})"
            )
            logger.error(error_message)
            raise TransferGoValidationError(error_message)
        return True

    def get_quote(
        self,
        amount: Optional[Decimal] = None,
        receive_amount: Optional[Decimal] = None,
        source_currency: str = "EUR",
        destination_currency: str = "UAH",
        source_country: str = "DE",
        destination_country: str = "UA",
        payment_method: Optional[str] = None,
        delivery_method: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get a quote from TransferGo for a money transfer.

        Args:
            amount: The amount to send (mutually exclusive with receive_amount)
            receive_amount: The amount to receive (mutually exclusive with amount)
            source_currency: ISO currency code of the source currency
            destination_currency: ISO currency code of the destination currency
            source_country: ISO country code of the source country
            destination_country: ISO country code of the destination country
            payment_method: Method to use for payment (e.g., "bank_transfer", "card")
            delivery_method: Method to use for delivery (e.g., "bank_deposit", "cash_pickup")
            **kwargs: Additional optional arguments

        Returns:
            A dictionary containing the quote information or error details
        """
        # Determine calculation mode
        calc_base = "sendAmount"
        if receive_amount is not None and amount is None:
            calc_base = "receiveAmount"
            amount = receive_amount
        elif amount is None:
            amount = Decimal("1000")  # Default amount if none provided

        # Use default payment and delivery methods if not specified
        payment_method = payment_method or self.DEFAULT_PAYMENT_METHOD
        delivery_method = delivery_method or self.DEFAULT_DELIVERY_METHOD

        # Is this a business transfer?
        business = int(kwargs.get("business", 0))

        # Prepare the base result with input values
        base_result = {
            "success": False,
            "error_message": None,
            "send_amount": float(amount) if calc_base == "sendAmount" else None,
            "source_currency": source_currency.upper(),
            "destination_currency": destination_currency.upper(),
            "destination_amount": float(amount) if calc_base == "receiveAmount" else None,
            "payment_method": payment_method,
            "delivery_method": delivery_method,
        }

        try:
            # Validate the corridor
            self.validate_corridor(
                source_country,
                source_currency,
                destination_country,
                destination_currency,
            )

            # Request quotes from TransferGo
            data = self._request_quotes(
                from_country=source_country,
                to_country=destination_country,
                from_currency=source_currency,
                to_currency=destination_currency,
                amount=amount,
                calc_base=calc_base,
                business=business,
            )

            # "options" is typically a list of different speed/fee combos
            options_list = data.get("options", [])
            if not options_list:
                base_result["error_message"] = "No quote options returned by TransferGo"
                return self.standardize_response(base_result)

            # Find the default option or the one matching requested delivery method
            selected_option = None

            # First try to match the requested delivery method
            if delivery_method:
                for opt in options_list:
                    delivery_type = opt.get("payOutMethod", {}).get("type", "")
                    if DELIVERY_METHODS.get(delivery_type, "").lower() == delivery_method.lower():
                        selected_option = opt
                        break

            # If no matching delivery method found, look for default option
            if not selected_option:
                for opt in options_list:
                    if opt.get("isDefault", False):
                        selected_option = opt
                        break

            # If still no option found, use the first one
            if not selected_option and options_list:
                selected_option = options_list[0]

            if not selected_option:
                base_result["error_message"] = "Could not find a suitable quote option"
                return self.standardize_response(base_result)

            # Extract data from the selected option
            fee = float(selected_option["fee"]["value"])
            rate = float(selected_option["rate"]["value"])
            sending_amount = float(selected_option["sendingAmount"]["value"])
            receiving_amount = float(selected_option["receivingAmount"]["value"])

            # Extract delivery time if available
            delivery_time_str = selected_option.get("delivery", {}).get("time", "")
            delivery_time_minutes = parse_delivery_time(delivery_time_str)

            # Extract payment and delivery methods
            payment_method_raw = selected_option.get("payInMethod", {}).get("type", "")
            delivery_method_raw = selected_option.get("payOutMethod", {}).get("type", "")

            payment_method = PAYMENT_METHODS.get(payment_method_raw, self.DEFAULT_PAYMENT_METHOD)
            delivery_method = DELIVERY_METHODS.get(
                delivery_method_raw, self.DEFAULT_DELIVERY_METHOD
            )

            # Extract all available delivery methods
            available_delivery_methods = []
            unique_delivery_methods = set()

            for opt in options_list:
                delivery_type = opt.get("payOutMethod", {}).get("type", "")
                standardized_name = DELIVERY_METHODS.get(
                    delivery_type, self.DEFAULT_DELIVERY_METHOD
                )

                # Skip duplicates
                if standardized_name in unique_delivery_methods:
                    continue

                unique_delivery_methods.add(standardized_name)

                # Add to available methods
                available_delivery_methods.append(
                    {
                        "method_code": standardized_name,
                        "method_name": delivery_type.replace("_", " ").title(),
                        "standardized_name": standardized_name,
                        "exchange_rate": float(opt["rate"]["value"]),
                        "is_best_rate": opt.get("isDefault", False),
                    }
                )

            # Extract all available payment methods
            available_payment_methods = []
            unique_payment_methods = set()

            for opt in options_list:
                payment_type = opt.get("payInMethod", {}).get("type", "")
                standardized_name = PAYMENT_METHODS.get(payment_type, self.DEFAULT_PAYMENT_METHOD)

                # Skip duplicates
                if standardized_name in unique_payment_methods:
                    continue

                unique_payment_methods.add(standardized_name)

                # Add to available methods
                available_payment_methods.append(
                    {
                        "method_code": standardized_name,
                        "method_name": payment_type.replace("_", " ").title(),
                        "standardized_name": standardized_name,
                    }
                )

            # Log the extracted data
            logger.info(
                f"TransferGo quote success: {sending_amount} {source_currency} → "
                f"{receiving_amount} {destination_currency} (rate={rate}, fee={fee})"
            )

            # Build the successful result
            base_result.update(
                {
                    "success": True,
                    "fee": fee,
                    "exchange_rate": rate,
                    "send_amount": sending_amount,
                    "destination_amount": receiving_amount,
                    "payment_method": payment_method,
                    "delivery_method": delivery_method,
                    "delivery_time_minutes": delivery_time_minutes
                    if delivery_time_minutes is not None
                    else self.DEFAULT_DELIVERY_TIME,
                    "timestamp": datetime.utcnow().isoformat(),
                    "available_delivery_methods": available_delivery_methods,
                    "available_payment_methods": available_payment_methods,
                    "raw_response": data,
                }
            )

            logger.debug(
                f"Preserving {len(available_delivery_methods)} delivery methods in response"
            )
            logger.debug(f"Preserving {len(available_payment_methods)} payment methods in response")

            return self.standardize_response(
                base_result,
                provider_specific_data=kwargs.get("provider_specific_data", False),
            )

        except (
            TransferGoError,
            TransferGoConnectionError,
            TransferGoValidationError,
        ) as e:
            # Return a standardized error response
            err_msg = f"TransferGo error: {str(e)}"
            logger.error(err_msg)
            base_result["error_message"] = err_msg
            return self.standardize_response(base_result)

        except Exception as e:
            # Catch all other exceptions
            err_msg = f"Unexpected TransferGo error: {str(e)}"
            logger.error(err_msg, exc_info=True)
            base_result["error_message"] = err_msg
            return self.standardize_response(base_result)

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        receive_currency: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get an exchange rate from TransferGo for a money transfer.

        Args:
            send_amount: The amount to send
            send_currency: ISO currency code of the source currency
            receive_country: ISO country code of the destination country
            receive_currency: ISO currency code of the destination currency
            **kwargs: Additional optional arguments

        Returns:
            A dictionary containing the exchange rate information or error details
        """
        base_result = {
            "success": False,
            "error_message": None,
            "send_amount": float(send_amount),
            "source_currency": send_currency.upper(),
            "destination_currency": receive_currency.upper(),
        }

        if not send_amount or send_amount <= 0:
            base_result["error_message"] = "Send amount must be positive"
            return self.standardize_response(base_result)

        if not send_currency or not receive_country or not receive_currency:
            base_result["error_message"] = "Missing required parameters"
            return self.standardize_response(base_result)

        # Guess a source country if not provided
        source_country = kwargs.get("source_country")
        if not source_country:
            source_country = guess_country_for_currency(send_currency)
            logger.debug(f"Guessed source country {source_country} for currency {send_currency}")

        try:
            # Get a quote using the source country
            return self.get_quote(
                amount=send_amount,
                source_currency=send_currency,
                destination_currency=receive_currency,
                source_country=source_country,
                destination_country=receive_country,
                payment_method=kwargs.get("payment_method"),
                delivery_method=kwargs.get("delivery_method"),
                provider_specific_data=kwargs.get("provider_specific_data", False),
            )

        except Exception as e:
            msg = f"Error in TransferGo get_exchange_rate: {str(e)}"
            logger.error(msg, exc_info=True)
            base_result["error_message"] = msg
            return self.standardize_response(base_result)

    def close(self):
        """Close the session if needed."""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Alias for backward compatibility
TransferGoAggregatorProvider = TransferGoProvider
