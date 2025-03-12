"""
Western Union Money Transfer Integration

This module implements the integration with Western Union's money transfer API.
Unlike other providers that have explicit delivery methods, Western Union uses
service groups (delivery channels) with different naming conventions:

DELIVERY METHODS (service groups):
---------------------------------
- CASH_PICKUP: Cash pickup at agent locations
- ACCOUNT_DEPOSIT: Bank account deposit
- WALLET_ACCOUNT: Mobile wallet transfer
- MOBILE_MONEY: Mobile money services (specific to certain markets)
- PREPAID_CARD: Transfer to prepaid cards
- CASH_HOME_DELIVERY: Cash delivery to home address (specific markets only)
- UPI: Unified Payments Interface (specific to India)

Each delivery method supports specific payment methods, which vary by corridor.

PAYMENT METHODS (fund_in types):
-------------------------------
- BANKACCOUNT: Bank account 
- CREDITCARD: Credit card payment
- DEBITCARD: Debit card payment
- CASH: Cash payment at agent location

Important API notes:
1. The catalog_data endpoint returns all available service groups and payment methods
2. Each corridor (send country → receive country) supports different combinations
3. Some options may be rate-limited or have minimum/maximum amount restrictions
4. Exchange rates and fees vary by delivery method and payment method
5. Always check transferOptions before assuming a payment/delivery combination works

For more details, see the test_discover_supported_methods test method in tests.py
"""

import json
import logging
import os
import pprint
import random
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

# Import base provider class and exceptions
from apps.providers.base.provider import RemittanceProvider
from apps.providers.westernunion.exceptions import (
    WUAuthenticationError,
    WUConnectionError,
    WUError,
    WUValidationError,
)

# Import mappings
from apps.providers.westernunion.westernunion_mappings import (
    API_CONFIG,
    COUNTRY_CURRENCY_MAP,
    DEFAULT_VALUES,
    DELIVERY_METHOD_TO_AGGREGATOR,
    PAYMENT_METHOD_TO_AGGREGATOR,
    get_delivery_methods_for_country,
    get_payment_code_for_payment_method,
    get_service_code_for_delivery_method,
    is_corridor_supported,
)

logger = logging.getLogger(__name__)


def log_request_details(
    logger, method: str, url: str, headers: Dict, params: Dict = None, data: Dict = None
):
    """Utility to log outgoing request details."""
    logger.debug("\n" + "=" * 80 + f"\nOUTGOING REQUEST:\n{'=' * 80}")
    logger.debug(f"Method: {method}")
    logger.debug(f"URL: {url}")
    sensitive_keys = {
        "Authorization",
        "Cookie",
        "X-WU-Correlation-ID",
        "X-WU-Transaction-ID",
    }

    safe_headers = {}
    for k, v in headers.items():
        if k in sensitive_keys:
            safe_headers[k] = "***MASKED***"
        else:
            safe_headers[k] = v

    logger.debug("\nHeaders:")
    logger.debug(pprint.pformat(safe_headers))

    if params:
        logger.debug("\nParams:")
        logger.debug(pprint.pformat(params))
    if data:
        logger.debug("\nData:")
        logger.debug(pprint.pformat(data))


def log_response_details(logger, response):
    """Utility to log incoming response details."""
    logger.debug("\n" + "=" * 80 + f"\nRESPONSE DETAILS:\n{'=' * 80}")
    logger.debug(f"Status Code: {response.status_code}")
    logger.debug(f"Reason: {response.reason}")
    logger.debug("\nHeaders:")
    logger.debug(pprint.pformat(dict(response.headers)))

    try:
        body = response.json()
        logger.debug("\nJSON Body:")
        logger.debug(pprint.pformat(body))
    except ValueError:
        body = response.text
        logger.debug("\nRaw Body:")
        logger.debug(body[:1000] + "..." if len(body) > 1000 else body)

    logger.debug("=" * 80)


class WesternUnionProvider(RemittanceProvider):
    """
    Western Union money transfer integration (aggregator-ready).

    This provider is fully compliant with the aggregator pattern:
    - No mock/fallback data: fails with "success": false, "error_message" on error.
    - On success, returns real WU data in standard aggregator fields.

    Example usage:
        provider = WesternUnionProvider()
        result = provider.get_quote(
            amount=Decimal("1000"),
            source_currency="USD",
            destination_currency="MXN",
            source_country="US",
            destination_country="MX"
        )
    """

    BASE_URL = API_CONFIG["BASE_URL"]
    START_PAGE_URL = API_CONFIG["START_PAGE_URL"]
    CATALOG_URL = API_CONFIG["CATALOG_URL"]

    DEFAULT_USER_AGENT = API_CONFIG["DEFAULT_USER_AGENT"]

    # Provider ID for aggregator system
    provider_id = "westernunion"

    def __init__(self, timeout: int = 30, user_agent: Optional[str] = None):
        """
        Initialize the Western Union provider.

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string, or default if None
        """
        super().__init__(name="Western Union", base_url=self.START_PAGE_URL)
        self.logger = logger
        self.timeout = timeout
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT

        self._session = requests.Session()
        self.correlation_id = ""
        self.transaction_id = ""
        self._configured = False  # tracks if session init done

        # Default values for aggregator standard response
        self.DEFAULT_DELIVERY_TIME = DEFAULT_VALUES["DEFAULT_DELIVERY_TIME_MINUTES"]
        self.logger.debug("WU provider init complete.")

    def standardize_response(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw result dict to aggregator-standard format.
        """
        now_str = datetime.now(UTC).isoformat()

        # If success is not indicated, default to False
        success_flag = raw.get("success", False)
        error_msg = raw.get("error_message")

        # If the aggregator call failed, the minimal aggregator structure:
        if not success_flag:
            return {
                "provider_id": self.name,
                "success": False,
                "error_message": error_msg or "Unknown error",
            }

        # If success, fill aggregator fields
        return {
            "provider_id": self.name,
            "success": True,
            "error_message": None,
            "send_amount": raw.get("send_amount", 0.0),
            "source_currency": raw.get("send_currency", "").upper(),
            "destination_amount": raw.get("receive_amount", 0.0),
            "destination_currency": raw.get("receive_currency", ""),
            "exchange_rate": raw.get("exchange_rate", 0.0),
            "fee": raw.get("fee", 0.0),
            "payment_method": DEFAULT_VALUES["DEFAULT_PAYMENT_METHOD"],
            "delivery_method": DEFAULT_VALUES["DEFAULT_DELIVERY_METHOD"],
            "delivery_time_minutes": raw.get("delivery_time_minutes", self.DEFAULT_DELIVERY_TIME),
            "timestamp": raw.get("timestamp", now_str),
            # pass along raw data if you want debug info
            "raw_response": raw.get("raw_response"),
        }

    def _initialize_session(self) -> bool:
        """
        Initialize a session with Western Union's website.
        Gets cookies and credentials needed for API calls.

        Returns:
            True if session was initialized successfully, False otherwise
        """
        logger.info("Initializing Western Union session...")

        if not self._session:
            self._session = requests.Session()

            # Set up user agent and other default headers that match browser behavior
            self._session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Content-Type": "text/plain;charset=UTF-8",
                    "Origin": "https://www.westernunion.com",
                    "Referer": "https://www.westernunion.com/us/en/home.html",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Priority": "u=3, i",
                }
            )

        # Skip further initialization if we already have a valid session
        if self._is_token_valid():
            logger.debug("Using existing valid WU session")
            return True

        # Generate a session ID and transaction ID
        # These help with correlation but don't need to be real GUIDs
        session_id = str(uuid.uuid4())
        transaction_id = str(uuid.uuid4())

        self._session.headers.update(
            {
                "X-WU-Correlation-ID": session_id,
                "X-WU-Transaction-ID": transaction_id,
            }
        )

        # Visit the start page to get initial cookies
        logger.debug(f"Accessing start page: {self.START_PAGE_URL}")

        try:
            response = self._session.get(self.START_PAGE_URL, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to load start page: {response.status_code}")
                return False

            logger.debug(
                f"Successfully loaded cookies from start page. Status: {response.status_code}"
            )
            cookies = [c.name for c in self._session.cookies]
            logger.debug(f"Cookies received: {cookies}")

            # Don't bother with the OPTIONS request - the curl example doesn't do it and it's failing
            # Just mark the session as configured
            self._configured = True
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to initialize session: {str(e)}")
            return False

    def get_quote(
        self,
        amount: Optional[Decimal] = None,
        receive_amount: Optional[Decimal] = None,
        source_currency: str = "USD",
        destination_currency: str = None,
        source_country: str = "US",
        destination_country: str = None,
        payment_method: Optional[str] = None,
        delivery_method: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get a money transfer quote from Western Union.

        Args:
            amount: Amount to send (in source currency)
            receive_amount: Amount to receive (if specified, used instead of send amount)
            source_currency: Currency to send (default: USD)
            destination_currency: Currency to receive
            source_country: Country sending from (default: US)
            destination_country: Country sending to
            payment_method: Optional payment method code
            delivery_method: Optional delivery method code

        Returns:
            Dictionary with quote details
        """
        # Check for dest_country/dest_currency in kwargs (for compatibility)
        if "dest_country" in kwargs and not destination_country:
            destination_country = kwargs.get("dest_country")
        if "dest_currency" in kwargs and not destination_currency:
            destination_currency = kwargs.get("dest_currency")

        logger.debug(
            f"Western Union get_quote called with amount={amount}, destination_country={destination_country}, source_country={source_country}, source_currency={source_currency}, destination_currency={destination_currency}"
        )

        # Validate required parameters
        if not destination_country:
            logger.debug("Western Union - destination country is required")
            return {
                "provider_id": "Western Union",
                "success": False,
                "error_message": "Destination country is required",
            }

        # Get exchange rate
        return self.get_exchange_rate(
            send_amount=amount,
            send_currency=source_currency,
            receive_country=destination_country,
            receive_currency=destination_currency,
            send_country=source_country,
            service_code=delivery_method,
            payment_code=payment_method,
        )

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        send_country: str = "US",
        service_code: Optional[str] = None,
        payment_code: Optional[str] = None,
        receive_currency: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get exchange rate between source and destination currencies.
        This implementation uses Western Union's catalog API to get accurate rates.

        Args:
            send_amount: Amount to send
            send_currency: Currency to send (e.g. 'USD')
            receive_country: Destination country code (e.g. 'MX')
            send_country: Source country code (default: 'US')
            service_code: Optional Western Union service code (e.g. '000' for cash)
            payment_code: Optional Western Union payment code (e.g. 'CC' for credit card)
            receive_currency: Optional currency to receive (default: inferred from country)

        Returns:
            Dictionary with exchange rate information
        """
        # Standard response format
        result = {
            "success": False,
            "provider_id": "Western Union",
            "source_amount": str(send_amount),
            "source_currency": send_currency,
            "destination_currency": receive_currency,
            "exchange_rate": None,
            "fee": None,
            "destination_amount": None,
            "error_message": None,
        }

        # If receive_currency not provided, try to infer from country
        if not receive_currency:
            # Define common country to currency mappings
            COUNTRY_TO_CURRENCY = {
                "MX": "MXN",
                "US": "USD",
                "CA": "CAD",
                "GB": "GBP",
                "IN": "INR",
                "PH": "PHP",
                "EG": "EGP",
                # Add more as needed
            }
            receive_currency = COUNTRY_TO_CURRENCY.get(receive_country)
            if not receive_currency:
                result[
                    "error_message"
                ] = f"Could not determine currency for country {receive_country}"
                return result
            result["destination_currency"] = receive_currency

        try:
            # Call get_catalog_data to fetch pricing information
            catalog_data = self.get_catalog_data(
                send_amount=float(send_amount),
                send_currency=send_currency,
                receive_country=receive_country,
                receive_currency=receive_currency,
                sender_country=send_country,
            )

            # Check if catalog call was successful
            if not catalog_data.get("success", True):
                result["error_message"] = catalog_data.get(
                    "error", "Failed to retrieve catalog data"
                )
                return result

            # Find the best exchange option from the catalog data
            best_option = self._find_best_exchange_option(
                catalog_data,
                preferred_service=service_code,
                preferred_payment=payment_code,
            )

            if not best_option:
                result["error_message"] = "No valid exchange rate found in WU catalog data"
                return result

            # Extract information from the best option
            result["exchange_rate"] = best_option.get("fx_rate")
            result["fee"] = best_option.get("fee")
            result["destination_amount"] = best_option.get("receive_amount")

            # Add additional information
            result["delivery_method"] = best_option.get("service_name")
            result["payment_method"] = best_option.get("payment_code")
            result["delivery_time_days"] = best_option.get("delivery_time")

            # Mark as successful
            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"Error in get_exchange_rate: {str(e)}", exc_info=True)
            result["error_message"] = f"Internal error: {str(e)}"
            return result

    def get_catalog_data(
        self,
        send_amount: float,
        send_currency: str,
        receive_country: str,
        receive_currency: str,
        sender_postal_code: Optional[str] = None,
        sender_country: Optional[str] = None,
    ) -> Dict:
        """
        Get catalog data from WU API.

        Args:
            send_amount: Amount to send
            send_currency: Currency being sent (e.g., 'USD')
            receive_country: Destination country code (e.g., 'MX')
            receive_currency: Currency being received (e.g., 'MXN')
            sender_postal_code: Optional postal code of sender
            sender_country: Optional country code of sender (defaults to US)

        Returns:
            Dictionary containing catalog data or error information
        """
        # Initialize session if needed
        if not self._initialize_session():
            logger.error("Failed to initialize WU session")
            return {"success": False, "error": "Failed to initialize WU session"}

        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        sender_country = sender_country or "US"

        # Update the payload to match Western Union's expected format
        payload = {
            "header_request": {"version": "0.5", "request_type": "PRICECATALOG"},
            "sender": {
                "client": "WUCOM",
                "channel": "WWEB",
                "funds_in": "*",
                "curr_iso3": send_currency,
                "cty_iso2_ext": sender_country,
                "send_amount": str(send_amount),
            },
            "receiver": {
                "curr_iso3": receive_currency,
                "cty_iso2_ext": receive_country,
                "cty_iso2": receive_country,
            },
        }

        logger.info(
            f"WU get_catalog_data: Preparing request for {sender_country} to {receive_country}, {send_currency}{send_amount} -> {receive_currency}"
        )
        logger.debug(f"WU get_catalog_data payload: {json.dumps(payload, indent=2)}")

        url = f"{self.CATALOG_URL}"
        logger.info(f"WU sending catalog request to: {url}")

        # Log request details
        log_request_details(logger, "POST", url, self._session.headers, data=payload)

        try:
            response = self._session.post(
                url, json=payload, headers=self._session.headers, timeout=30
            )

            # Log response details
            log_response_details(logger, response)

            if response.status_code != 200:
                # Improved error handling for non-JSON responses
                error_text = response.text
                try:
                    # Try to parse as JSON in case it still is
                    error_data = response.json()
                    error_message = error_data.get("message", error_text)
                    logger.error(f"Error response from Western Union API: {error_message}")
                    return {"success": False, "error": error_message}
                except json.JSONDecodeError:
                    # Handle plain text error responses
                    logger.error(f"Error response from Western Union API: {error_text}")
                    return {"success": False, "error": error_text}

            response_data = response.json()

            # Check if the response contains errors
            response_status = response_data.get("response_status", {})
            if response_status.get("status") != 0:
                message = response_status.get("message", "Unknown error")
                logger.error(f"WU API returned error: {message}")
                return {"success": False, "error": message}

            return response_data
        except Exception as e:
            logger.error(f"Unexpected error in get_catalog_data: {str(e)}")
            logger.debug("Falling back to searching services_groups directly")
            return {"success": False, "error": str(e)}

    def _normalize_delivery_method(self, service_type: str) -> str:
        """Normalize the service type to a standard delivery method."""
        service_type = service_type.upper() if service_type else ""

        if "CASH" in service_type:
            return "Cash Pickup"
        elif "BANK" in service_type or "ACCOUNT" in service_type:
            return "Bank Deposit"
        elif "MOBILE" in service_type:
            return "Mobile Money"
        else:
            return service_type

    def _parse_delivery_time(self, time_str: Optional[str]) -> int:
        """Parse delivery time string into minutes."""
        if not time_str:
            return 1440  # Default to 24 hours

        time_str = time_str.lower()

        if "minutes" in time_str:
            match = re.search(r"(\d+)\s*minutes", time_str)
            if match:
                return int(match.group(1))
        elif "hour" in time_str:
            match = re.search(r"(\d+)\s*hour", time_str)
            if match:
                return int(match.group(1)) * 60
        elif "day" in time_str:
            match = re.search(r"(\d+)\s*day", time_str)
            if match:
                return int(match.group(1)) * 1440

        # If we can't parse, return 24 hours as default
        return 1440

    def _find_best_exchange_option(
        self,
        catalog_data: Dict[str, Any],
        preferred_service: Optional[str] = None,
        preferred_payment: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Finds the best exchange rate option from the catalog data.

        Args:
            catalog_data: The catalog data from the WU API
            preferred_service: Optional service code preference (e.g., '000' for Money in Minutes)
            preferred_payment: Optional payment method preference (e.g., 'CC' for credit card)

        Returns:
            Dictionary with the best exchange option details or None if no valid options found
        """
        if not catalog_data.get("success", True):
            # Return None if the catalog data contains an error
            return None

        # First check if we have services_groups in the response
        services_groups = catalog_data.get("services_groups", [])
        if not services_groups:
            # No services found
            return None

        # Initialize variables to track best option
        best_option = None
        best_rate = 0

        # Map the service and payment preferences to search for
        service_code = preferred_service
        payment_code = preferred_payment

        # Iterate through service groups
        for service_group in services_groups:
            current_service_code = service_group.get("service")

            # Skip if we're looking for a specific service and this isn't it
            if service_code and current_service_code != service_code:
                continue

            pay_groups = service_group.get("pay_groups", [])

            for pay_group in pay_groups:
                current_payment_code = pay_group.get("fund_in")

                # Skip if we're looking for a specific payment method and this isn't it
                if payment_code and current_payment_code != payment_code:
                    continue

                fx_rate = pay_group.get("fx_rate")

                # If this is a valid rate and better than what we've seen so far
                if fx_rate and (best_option is None or fx_rate > best_rate):
                    best_rate = fx_rate
                    best_option = {
                        "service_code": current_service_code,
                        "service_name": service_group.get("service_name"),
                        "payment_code": current_payment_code,
                        "fx_rate": fx_rate,
                        "fee": pay_group.get("gross_fee", 0),
                        "send_amount": pay_group.get("send_amount"),
                        "receive_amount": pay_group.get("receive_amount"),
                        "delivery_time": service_group.get("speed_days", 0),
                    }

        # If no option was found through direct iteration, try to find in categories (Best FX section)
        if best_option is None:
            categories = catalog_data.get("categories", [])
            for category in categories:
                if category.get("type") == "bestfx":
                    services = category.get("services", [])
                    if services:
                        # Take the first one as the best FX rate (they should be sorted)
                        best_service = services[0]

                        # Find the corresponding service group and pay group to get all details
                        for service_group in services_groups:
                            if service_group.get("service") == best_service.get("pay_out"):
                                for pay_group in service_group.get("pay_groups", []):
                                    if pay_group.get("fund_in") == best_service.get("pay_in"):
                                        best_option = {
                                            "service_code": best_service.get("pay_out"),
                                            "service_name": service_group.get("service_name"),
                                            "payment_code": best_service.get("pay_in"),
                                            "fx_rate": best_service.get("fx_rate"),
                                            "fee": pay_group.get("gross_fee", 0),
                                            "send_amount": pay_group.get("send_amount"),
                                            "receive_amount": pay_group.get("receive_amount"),
                                            "delivery_time": service_group.get("speed_days", 0),
                                        }
                                        break
                                if best_option:
                                    break

                        if best_option:
                            break

        return best_option

    def _find_service_group(self, data, pay_out_val, pay_in_val):
        """
        From the big catalog data, find the matching services_groups pay_groups
        for the given pay_out (WU service) and pay_in (fund_in).
        """
        for group in data.get("services_groups", []):
            if group.get("service") == pay_out_val:
                for pay_group in group.get("pay_groups", []):
                    if pay_group.get("fund_in") == pay_in_val:
                        return {
                            "name": group.get("service_name", "Unknown"),
                            "fee": float(pay_group.get("gross_fee", 0)),
                            "receive_amount": float(pay_group.get("receive_amount", 0)),
                            "delivery_time": group.get("speed_days", 1),
                        }
        return None

    def _get_service_name_for_code(self, service_code: str) -> str:
        """Map WU service code to internal delivery method name."""
        from apps.providers.westernunion.westernunion_mappings import DELIVERY_SERVICE_CODES

        return DELIVERY_SERVICE_CODES.get(service_code, "ACCOUNT_DEPOSIT")

    def _get_payment_name_for_code(self, payment_code: str) -> str:
        """Map WU payment code to internal payment method name."""
        from apps.providers.westernunion.westernunion_mappings import PAYMENT_METHOD_CODES

        return PAYMENT_METHOD_CODES.get(payment_code, "BANKACCOUNT")

    # Maintain these methods for backward compatibility
    def _is_token_valid(self) -> bool:
        return True

    def _refresh_token(self):
        pass

    def close(self):
        """Close requests session if needed."""
        if self._session:
            self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
