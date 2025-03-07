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
import random
import time
import uuid
import pprint
from datetime import datetime, UTC
from decimal import Decimal
from typing import Dict, Optional, Any
from urllib.parse import urljoin

import requests

# Import base provider class and exceptions
from apps.providers.base.provider import RemittanceProvider
from apps.providers.westernunion.exceptions import (
    WUError,
    WUAuthenticationError,
    WUValidationError,
    WUConnectionError
)
# Import mappings
from apps.providers.westernunion.westernunion_mappings import (
    COUNTRY_CURRENCY_MAP,
    API_CONFIG,
    DEFAULT_VALUES,
    DELIVERY_METHOD_TO_AGGREGATOR,
    PAYMENT_METHOD_TO_AGGREGATOR,
    get_delivery_methods_for_country,
    get_service_code_for_delivery_method,
    get_payment_code_for_payment_method,
    is_corridor_supported
)

logger = logging.getLogger(__name__)

def log_request_details(logger, method: str, url: str, headers: Dict,
                        params: Dict = None, data: Dict = None):
    """Utility to log outgoing request details."""
    logger.debug("\n" + "=" * 80 + f"\nOUTGOING REQUEST:\n{'=' * 80}")
    logger.debug(f"Method: {method}")
    logger.debug(f"URL: {url}")
    sensitive_keys = {'Authorization', 'Cookie', 'X-WU-Correlation-ID', 'X-WU-Transaction-ID'}

    safe_headers = {}
    for k, v in headers.items():
        if k in sensitive_keys:
            safe_headers[k] = '***MASKED***'
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
        logger.debug(body[:1000] + '...' if len(body) > 1000 else body)

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
                "error_message": error_msg or "Unknown error"
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
            "raw_response": raw.get("raw_response")
        }

    def _initialize_session(self) -> None:
        """
        Perform a GET to the start page to load cookies, then an OPTIONS for /catalog.
        This is necessary for WU's security handshake.
        """
        if self._configured:
            return

        self.correlation_id = f"web-{uuid.uuid4()}"
        self.transaction_id = f"{self.correlation_id}-{int(time.time() * 1000)}"

        self._session.headers.update({
            "User-Agent": self.user_agent,
            **API_CONFIG["HEADERS"],
            "X-WU-Correlation-ID": self.correlation_id,
            "X-WU-Transaction-ID": self.transaction_id
        })

        # Basic cookies
        for ck, cv in API_CONFIG["DEFAULT_COOKIES"].items():
            self._session.cookies.set(ck, cv, domain=".westernunion.com")

        try:
            # 1. GET start page
            log_request_details(self.logger, "GET", self.START_PAGE_URL, dict(self._session.headers))
            resp = self._session.get(self.START_PAGE_URL, timeout=self.timeout, allow_redirects=True)
            log_response_details(self.logger, resp)
            resp.raise_for_status()

            for c in resp.cookies:
                self._session.cookies.set_cookie(c)

            # 2. OPTIONS for CORS preflight on /catalog
            preflight_headers = {
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "content-type,x-wu-correlation-id,x-wu-transaction-id"
                )
            }
            old_headers = {}
            for k, v in preflight_headers.items():
                old_headers[k] = self._session.headers.get(k)
                self._session.headers[k] = v

            log_request_details(self.logger, "OPTIONS", self.CATALOG_URL, dict(self._session.headers))
            opt_resp = self._session.options(self.CATALOG_URL, timeout=self.timeout)
            log_response_details(self.logger, opt_resp)
            opt_resp.raise_for_status()

            # restore old headers
            for k, v in preflight_headers.items():
                if old_headers[k] is not None:
                    self._session.headers[k] = old_headers[k]
                else:
                    del self._session.headers[k]

            self._configured = True
            self.logger.debug("WU session init success.")

        except requests.RequestException as e:
            msg = f"Failed to init WU session: {e}"
            self.logger.error(msg, exc_info=True)
            raise WUConnectionError(msg)

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
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get quote from Western Union for a money transfer.
        
        This is the main aggregator interface method - it delegates to get_exchange_rate
        but can be extended to support receive_amount calculations and more.
        
        Args:
            amount: Amount to send (source amount)
            receive_amount: Amount to receive (destination amount) - not implemented yet
            source_currency: Currency to send
            destination_currency: Currency to receive - will be auto-detected by WU in most cases
            source_country: Country sending from
            destination_country: Country sending to
            payment_method: Payment method (bank, card, etc)
            delivery_method: Delivery method (bank, cash, etc)
            
        Returns:
            Standardized response with either success+data or error message
        """
        if receive_amount is not None:
            # To implement receive amount, you'd need to adjust the catalog request
            # with a different approach. For now we don't support it.
            return self.standardize_response({
                "success": False,
                "error_message": "Receive amount quotes not yet supported for Western Union"
            })
            
        if not amount or amount <= 0:
            return self.standardize_response({
                "success": False,
                "error_message": "Invalid send amount"
            })
            
        if not destination_country:
            return self.standardize_response({
                "success": False,
                "error_message": "Destination country is required"
            })
        
        # Check if corridor is supported before making API call
        if not is_corridor_supported(source_country, destination_country):
            return self.standardize_response({
                "success": False,
                "error_message": f"Corridor {source_country} → {destination_country} not supported"
            })
            
        # If no destination currency specified, get it from mapping
        if not destination_currency:
            destination_currency = COUNTRY_CURRENCY_MAP.get(destination_country.upper())
            if not destination_currency:
                return self.standardize_response({
                    "success": False,
                    "error_message": f"Could not determine currency for country: {destination_country}"
                })
            
        # Get the exchange rate quote
        params = {
            "send_amount": amount,
            "send_currency": source_currency,
            "receive_country": destination_country,
            "send_country": source_country
        }
        
        # Add delivery method if specified
        if delivery_method:
            wu_service_code = get_service_code_for_delivery_method(delivery_method)
            params["service_code"] = wu_service_code
            
        # Add payment method if specified
        if payment_method:
            wu_payment_code = get_payment_code_for_payment_method(payment_method)
            params["payment_code"] = wu_payment_code
            
        return self.get_exchange_rate(**params)

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        send_country: str = "US",
        service_code: Optional[str] = None,
        payment_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregator-level interface: get exchange rate from WU for corridor.

        Args:
            send_amount: Decimal amount to send
            send_currency: e.g. "USD"
            receive_country: e.g. "MX" or "EG"
            send_country: e.g. "US"
            service_code: Optional WU service code (delivery method)
            payment_code: Optional WU payment code (payment method)

        Returns aggregator-standard dict with either success=True or success=False + error_message.
        """
        base_result = {
            "success": False,
            "send_amount": float(send_amount),
            "send_currency": send_currency.upper(),
            "receive_country": receive_country.upper()
        }

        if send_amount <= 0:
            base_result["error_message"] = "Invalid send_amount"
            return self.standardize_response(base_result)

        try:
            self._initialize_session()
        except WUConnectionError as e:
            base_result["error_message"] = str(e)
            return self.standardize_response(base_result)

        try:
            catalog_data = self.get_catalog_data(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
        except (WUError, WUConnectionError, WUValidationError) as e:
            base_result["error_message"] = str(e)
            return self.standardize_response(base_result)

        # Parse best rate from catalog
        try:
            best_option = self._find_best_exchange_option(catalog_data, service_code, payment_code)
            if not best_option:
                base_result["error_message"] = "No valid exchange rate found in WU catalog data"
                return self.standardize_response(base_result)

            # success result
            base_result.update({
                "success": True,
                "exchange_rate": best_option["exchange_rate"],
                "fee": best_option["fee"],
                "receive_amount": best_option["receive_amount"],
                "receive_currency": best_option.get("receive_currency", ""),
                "delivery_method": best_option.get("delivery_method", DEFAULT_VALUES["DEFAULT_DELIVERY_METHOD"]),
                "payment_method": best_option.get("payment_method", DEFAULT_VALUES["DEFAULT_PAYMENT_METHOD"]),
                "delivery_time_minutes": best_option.get("delivery_minutes", self.DEFAULT_DELIVERY_TIME),
                "timestamp": datetime.now(UTC).isoformat(),
                "raw_response": catalog_data
            })
            return self.standardize_response(base_result)

        except Exception as e:
            msg = f"Parse error: {e}"
            self.logger.error(msg, exc_info=True)
            base_result["error_message"] = msg
            return self.standardize_response(base_result)

    def get_catalog_data(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        send_country: str = "US",
        sender_postal_code: Optional[str] = None,
        sender_city: Optional[str] = None,
        sender_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make the POST call to /prices/catalog to get Western Union's data about
        exchange rates, fees, service groups, etc.

        Raises exceptions if the request fails or response is invalid.
        """
        # Western Union requires receive currency to be set
        receive_currency = COUNTRY_CURRENCY_MAP.get(receive_country.upper())
        
        if not receive_currency:
            self.logger.warning(f"No currency mapping found for country: {receive_country}")
            # If we don't have a mapping, we'll fail more gracefully
            raise WUValidationError(f"Unsupported destination country: {receive_country}")
        
        payload = {
            "header_reply": {
                "response_type": "not_present",
                "source_app": "defaultSource",
                "correlation_id": self.correlation_id
            },
            "sender": {
                "channel": "WWEB",
                "client": "WUCOM",
                "cty_iso2_ext": send_country.upper(),
                "curr_iso3": send_currency.upper(),
                "cpc": send_country.upper(),
                "funds_in": "*",
                "segment": "N00",
                "send_amount": float(send_amount)
            },
            "receiver": {
                "cty_iso2_ext": receive_country.upper(),
                "curr_iso3": receive_currency
            }
        }

        # Add optional sender location details if provided
        if sender_postal_code or sender_city or sender_state:
            sender_location = {}
            if sender_postal_code:
                sender_location["postal_code"] = sender_postal_code
            if sender_city:
                sender_location["city"] = sender_city
            if sender_state:
                sender_location["state"] = sender_state
            
            if sender_location:
                payload["sender"]["location"] = sender_location

        log_request_details(self.logger, "POST", self.CATALOG_URL, dict(self._session.headers), data=payload)
        try:
            resp = self._session.post(self.CATALOG_URL, json=payload, timeout=self.timeout)
            log_response_details(self.logger, resp)
            if resp.status_code >= 400:
                try:
                    # Try to parse error as JSON
                    try:
                        error_data = resp.json()
                        # Handle different error formats
                        if isinstance(error_data, dict):
                            # Standard JSON error format
                            err_msg = error_data.get("error", {}).get("message", "Unknown error")
                        elif isinstance(error_data, str):
                            # String error message
                            err_msg = error_data
                        else:
                            # Fallback for other formats
                            err_msg = f"Unknown error format: {error_data}"
                    except json.JSONDecodeError:
                        # Not valid JSON, use text response
                        err_msg = resp.text
                    
                    raise WUConnectionError(f"WU catalog request failed with status {resp.status_code}: {err_msg}")
                except Exception as e:
                    # Catch-all for any other errors
                    raise WUConnectionError(f"WU catalog request failed with status={resp.status_code}, body={resp.text}")

            data = resp.json()
            if not data.get("services_groups"):
                raise WUValidationError("No 'services_groups' in WU catalog response")

            return data

        except requests.RequestException as e:
            msg = f"WU connection error on catalog request: {e}"
            self.logger.error(msg, exc_info=True)
            raise WUConnectionError(msg)
        except ValueError as ve:
            msg = f"WU catalog response not valid JSON: {ve}"
            self.logger.error(msg, exc_info=True)
            raise WUValidationError(msg)

    def _find_best_exchange_option(self, catalog_data: Dict[str, Any], 
                                   preferred_service: Optional[str] = None,
                                   preferred_payment: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Inspect catalog_data for the best exchange rate. "Best" might be highest rate or
        lowest fee. We try to find 'bestfx' category first, otherwise pick from 'services_groups'.

        Args:
            catalog_data: The catalog response from the API
            preferred_service: Optional service code to filter by (e.g., "000" for cash pickup)
            preferred_payment: Optional payment code to filter by (e.g., "CC" for credit card)

        Returns:
            dict with keys: exchange_rate, fee, receive_amount, receive_currency, etc.
        """
        best_rate = None
        best_option = None
        
        # Get the receiver currency from the catalog data
        receive_currency = catalog_data.get("receiver", {}).get("curr_iso3", "")
        
        # If specific service/payment methods were requested, log them
        if preferred_service:
            self.logger.debug(f"Looking for preferred service code: {preferred_service}")
        if preferred_payment:
            self.logger.debug(f"Looking for preferred payment code: {preferred_payment}")

        # Check 'categories' for 'bestfx' first
        categories = catalog_data.get("categories", [])
        for cat in categories:
            if cat.get("type") == "bestfx":
                for svc in cat.get("services", []):
                    # Skip if it doesn't match the preferred service if specified
                    if preferred_service and svc.get("pay_out") != preferred_service:
                        continue
                    
                    # Skip if it doesn't match the preferred payment if specified
                    if preferred_payment and svc.get("pay_in") != preferred_payment:
                        continue
                    
                    rate = float(svc.get("fx_rate", 0.0))
                    if rate > 0 and (best_rate is None or rate > best_rate):
                        best_rate = rate
                        pay_out = svc.get("pay_out")
                        pay_in = svc.get("pay_in")
                        resolved = self._find_service_group(catalog_data, pay_out, pay_in)
                        if resolved:
                            # Map the internal service codes to aggregator format
                            wu_delivery_method = self._get_service_name_for_code(pay_out)
                            wu_payment_method = self._get_payment_name_for_code(pay_in)
                            
                            delivery_method = DELIVERY_METHOD_TO_AGGREGATOR.get(wu_delivery_method, DEFAULT_VALUES["DEFAULT_DELIVERY_METHOD"])
                            # If user requested a specific delivery method, use that in the response
                            if preferred_service and wu_delivery_method:
                                delivery_method = DELIVERY_METHOD_TO_AGGREGATOR.get(wu_delivery_method, delivery_method)
                            
                            best_option = {
                                "exchange_rate": rate,
                                "fee": resolved.get("fee", 0.0),
                                "receive_amount": resolved.get("receive_amount", 0.0),
                                "receive_currency": receive_currency,
                                "delivery_method": delivery_method,
                                "payment_method": PAYMENT_METHOD_TO_AGGREGATOR.get(wu_payment_method, DEFAULT_VALUES["DEFAULT_PAYMENT_METHOD"]),
                                "delivery_minutes": resolved.get("delivery_time", 1) * 1440  # Convert days to minutes
                            }

        # If we didn't find any 'bestfx', iterate services_groups
        if best_option is None:
            for group in catalog_data.get("services_groups", []):
                # Skip if it doesn't match the preferred service if specified
                service_code = group.get("service")
                if preferred_service and service_code != preferred_service:
                    continue
                
                wu_delivery_method = self._get_service_name_for_code(service_code)
                delivery_method = DELIVERY_METHOD_TO_AGGREGATOR.get(wu_delivery_method, DEFAULT_VALUES["DEFAULT_DELIVERY_METHOD"])
                
                # If a service code was specified, log the delivery method resolved
                if preferred_service:
                    self.logger.debug(f"Found service code {service_code} mapped to {wu_delivery_method} -> {delivery_method}")
                
                for payg in group.get("pay_groups", []):
                    # Skip if it doesn't match the preferred payment if specified
                    fund_in = payg.get("fund_in")
                    if preferred_payment and fund_in != preferred_payment:
                        continue
                    
                    wu_payment_method = self._get_payment_name_for_code(fund_in)
                    
                    rate_val = float(payg.get("fx_rate", 0.0))
                    if rate_val > 0 and (best_rate is None or rate_val > best_rate):
                        best_rate = rate_val
                        best_option = {
                            "exchange_rate": rate_val,
                            "fee": float(payg.get("gross_fee", 0.0)),
                            "receive_amount": float(payg.get("receive_amount", 0.0)),
                            "receive_currency": receive_currency,
                            "delivery_method": delivery_method,
                            "payment_method": PAYMENT_METHOD_TO_AGGREGATOR.get(wu_payment_method, DEFAULT_VALUES["DEFAULT_PAYMENT_METHOD"]),
                            "delivery_minutes": int(group.get("speed_days", 1)) * 1440  # Convert days to minutes
                        }

        if best_option is None:
            self.logger.warning(f"No valid exchange option found for the given parameters. Service: {preferred_service}, Payment: {preferred_payment}")
            
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
                            "delivery_time": group.get('speed_days', 1)                             
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
