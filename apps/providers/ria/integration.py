"""
RIA Money Transfer Integration

This module implements the integration with RIA Money Transfer API for remittance services.
The primary focus of this integration is to retrieve accurate exchange rates.

DELIVERY METHODS:
---------------------------------
- BankDeposit: Bank account deposit (Primary method we use for exchange rates)
- CashPickup: Cash pickup at agent locations

PAYMENT METHODS:
---------------------------------
- DebitCard: Debit card payment (Primary method we use for exchange rates)
- BankAccount: Bank account transfer
"""

import json
import logging
import os
import random
import string
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import certifi
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util import SSLContext
from urllib3.util.retry import Retry
from urllib3.util.ssl_ import create_urllib3_context

from apps.providers.base.provider import RemittanceProvider
from apps.providers.ria.exceptions import (
    RIAAuthenticationError,
    RIAConnectionError,
    RIAError,
    RIAValidationError,
)

urllib3.add_stderr_logger()


class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.options |= 0x4
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = create_urllib3_context()
        return super().proxy_manager_for(*args, **kwargs)


class RIAProvider(RemittanceProvider):
    BASE_URL = "https://public.riamoneytransfer.com"
    DEFAULT_PAYMENT_METHOD = "debitCard"
    DEFAULT_DELIVERY_METHOD = "bankDeposit"
    DEFAULT_DELIVERY_TIME = 48 * 60

    # Mapping of RIA delivery method codes to standardized names
    DELIVERY_METHOD_MAP = {
        "BankDeposit": "bank_deposit",
        "OfficePickup": "cash_pickup",
        "UPI": "mobile_wallet",  # Universal Payment Interface (India)
        "HomeDelivery": "home_delivery",
        "MobileWallet": "mobile_wallet",
        "MobilePayment": "mobile_wallet",
        "MobileTopup": "mobile_topup",
        "CardDeposit": "card_deposit",
    }

    # Mapping of RIA payment method codes to standardized names
    PAYMENT_METHOD_MAP = {
        "DebitCard": "debit_card",
        "CreditCard": "credit_card",
        "BankAccount": "bank_account",
        "PayNearMe": "cash",
    }

    def __init__(self, timeout: int = 30):
        super().__init__(name="ria", base_url=self.BASE_URL)

        self.logger = logging.getLogger("providers.ria")
        self.timeout = timeout
        self.session = requests.Session()

        self.session.verify = certifi.where()

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
                "Origin": "https://www.riamoneytransfer.com",
                "Referer": "https://www.riamoneytransfer.com/",
                "Content-Type": "application/json",
                "AppType": "2",
                "AppVersion": "4.0",
                "Client-Type": "PublicSite",
                "CultureCode": "en-US",
                "X-Client-Platform": "Web",
                "X-Client-Version": "4.0.0",
                "IAmFrom": "US",
                "CountryId": "US",
                "IsoCode": "US",
                "X-Device-Id": "WEB-"
                + "".join(random.choices(string.ascii_uppercase + string.digits, k=16)),
            }
        )

        adapter = TLSAdapter()
        self.session.mount("https://", adapter)

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        self.session.mount("https://", TLSAdapter(max_retries=retry_strategy))

        self.bearer_token: Optional[str] = None
        self.token_expiry: Optional[float] = None
        self.calculator_data: Optional[Dict[str, Any]] = None

        self._session_init()
        self._calculator_init()

    def standardize_response(
        self, raw_result: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Convert local results to aggregator's standard shape:
            provider_id, success, error_message,
            send_amount, source_currency,
            destination_amount, destination_currency,
            exchange_rate, fee,
            payment_method, delivery_method,
            delivery_time_minutes, timestamp
        """
        now_ts = datetime.now().isoformat()
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
            "timestamp": raw_result.get("timestamp", now_ts),
        }

        # Ensure delivery methods are preserved
        if "available_delivery_methods" in raw_result:
            self.logger.debug(
                f"Preserving {len(raw_result['available_delivery_methods'])} delivery methods in standardized response"
            )
            output["available_delivery_methods"] = raw_result["available_delivery_methods"]

        # Ensure payment methods are preserved
        if "available_payment_methods" in raw_result:
            self.logger.debug(
                f"Preserving {len(raw_result['available_payment_methods'])} payment methods in standardized response"
            )
            output["available_payment_methods"] = raw_result["available_payment_methods"]

        # Include any raw data if aggregator wants it
        if provider_specific_data and "raw_response" in raw_result:
            output["raw_response"] = raw_result["raw_response"]

        return output

    def _session_init(self) -> None:
        try:
            url = f"{self.BASE_URL}/Authorization/session"
            self.logger.debug("GET session info from %s", url)
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()

            if "bearer" in resp.headers:
                self.bearer_token = resp.headers["bearer"]
                self.session.headers["Authorization"] = f"Bearer {self.bearer_token}"
                if "expiresIn" in resp.headers:
                    expires_in = int(resp.headers["expiresIn"])
                    self.token_expiry = time.time() + expires_in
                else:
                    self.token_expiry = time.time() + 1800
            else:
                self.logger.warning("No bearer token in session response headers")
                self.bearer_token = None

        except requests.RequestException as e:
            self.logger.error("Session init failed: %s", e, exc_info=True)
            raise RIAConnectionError("Failed to initialize RIA session") from e

    def _calculator_init(self) -> None:
        try:
            url = f"{self.BASE_URL}/Calculator/Initialize"
            self.logger.debug("GET calculator init from %s", url)
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()

            self.calculator_data = resp.json()
            if "bearer" in resp.headers:
                new_bearer = resp.headers["bearer"]
                if new_bearer != self.bearer_token:
                    self.bearer_token = new_bearer
                    self.session.headers["Authorization"] = f"Bearer {self.bearer_token}"
                if "expiresIn" in resp.headers:
                    expires_in = int(resp.headers["expiresIn"])
                    self.token_expiry = time.time() + expires_in

            self.logger.debug("RIA calculator init successful")

        except requests.RequestException as e:
            self.logger.error("Calculator init failed: %s", e, exc_info=True)
            raise RIAConnectionError("Failed to initialize RIA calculator") from e

    def _ensure_token_valid(self):
        if not self.bearer_token:
            raise RIAAuthenticationError("RIA bearer token missing")
        if self.token_expiry and time.time() > (self.token_expiry - 60):
            self.logger.debug("Token near expiry, re-initializing session")
            self._session_init()
            self._calculator_init()

    def _calculate_rate(
        self,
        send_amount: float,
        send_currency: str,
        receive_country: str,
        payment_method: str,
        delivery_method: str,
        send_country: str,
    ) -> Optional[Dict[str, Any]]:
        self._ensure_token_valid()

        body = {
            "selections": {
                "countryTo": receive_country.upper(),
                "amountFrom": float(send_amount),
                "amountTo": None,
                "currencyFrom": send_currency.upper(),
                "currencyTo": None,
                "paymentMethod": payment_method,
                "deliveryMethod": delivery_method,
                "shouldCalcAmountFrom": False,
                "shouldCalcVariableRates": True,
                "countryFrom": send_country.upper(),
                "promoCode": None,
                "promoId": 0,
            }
        }

        url = f"{self.BASE_URL}/MoneyTransferCalculator/Calculate"
        correlation_id = str(uuid.uuid4())

        for attempt in range(3):
            try:
                resp = self.session.post(
                    url,
                    json=body,
                    headers={"CorrelationId": correlation_id},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data
                if resp.status_code >= 500:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                self.logger.error(
                    "RIA calc error: status=%s, body=%s",
                    resp.status_code,
                    resp.text[:500],
                )
                return None
            except requests.RequestException as e:
                self.logger.warning("Calc attempt %d failed: %s", attempt + 1, e, exc_info=True)
                time.sleep(1.5 * (attempt + 1))

        return None

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        dest_currency: str,
        source_country: str,
        dest_country: str,
        payment_method: str = None,
        delivery_method: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Aggregator-standard method: returns the quote as a dictionary.
        No fallback. If fails, success=False + error message.

        Args:
            amount: Decimal, the send amount
            source_currency: e.g. "USD"
            dest_currency: We let RIA pick automatically if not needed. But aggregator calls might pass it.
            source_country: e.g. "US"
            dest_country: e.g. "MX"
            payment_method: "debitCard", "bankAccount", ...
            delivery_method: "bankDeposit", "cashPickup", ...
        """
        # Use defaults if not provided
        if payment_method is None:
            payment_method = self.DEFAULT_PAYMENT_METHOD
        if delivery_method is None:
            delivery_method = self.DEFAULT_DELIVERY_METHOD

        # Enable debug mode from kwargs
        debug_mode = kwargs.get("debug_mode", False)

        # We'll unify everything in one standard result
        base_result = {
            "success": False,
            "error_message": None,
            "send_amount": float(amount),
            "source_currency": source_currency,
            "destination_currency": dest_currency,  # RIA might override
            "payment_method": payment_method,
            "delivery_method": delivery_method,
        }

        try:
            # Call the rate calculator
            raw_calc = self._calculate_rate(
                send_amount=float(amount),
                send_currency=source_currency,
                receive_country=dest_country,
                payment_method=payment_method,
                delivery_method=delivery_method,
                send_country=source_country,
            )
            if not raw_calc:
                base_result["error_message"] = "RIA calculator returned no data (None)."
                return self.standardize_response(base_result)

            # Debug raw structure
            if debug_mode:
                # Save the raw response to a file for inspection
                debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f"ria_response_{dest_country}.json")
                with open(debug_file, "w") as f:
                    json.dump(raw_calc, f, indent=2)
                self.logger.info(f"Saved raw response to {debug_file}")

                # Log the path to delivery methods
                self.logger.info("Raw response keys: %s", list(raw_calc.keys()))
                if "model" in raw_calc:
                    model = raw_calc["model"]
                    self.logger.info("Model keys: %s", list(model.keys()))
                    if "transferDetails" in model:
                        td = model["transferDetails"]
                        self.logger.info("TransferDetails keys: %s", list(td.keys()))
                        if "transferOptions" in td:
                            to = td["transferOptions"]
                            self.logger.info("TransferOptions keys: %s", list(to.keys()))
                            if "deliveryMethods" in to:
                                dm = to["deliveryMethods"]
                                self.logger.info("Found %d delivery methods", len(dm))
                                for i, method in enumerate(dm):
                                    self.logger.info("  Method %d: %s", i + 1, method)

            # Possibly the data is inside raw_calc["model"]["calculations"] or raw_calc["calculations"]
            calculations = self._extract_calculations(raw_calc)
            if not calculations:
                # If we can't extract, consider failure
                base_result["error_message"] = "No valid calculations in RIA response"
                base_result["raw_response"] = raw_calc
                return self.standardize_response(base_result, provider_specific_data=True)

            # Extract available delivery and payment methods
            available_delivery_methods = self._extract_delivery_methods(raw_calc)
            available_payment_methods = self._extract_payment_methods(raw_calc)

            # Log extraction results
            self.logger.debug(
                f"Extracted {len(available_delivery_methods)} delivery methods and {len(available_payment_methods)} payment methods"
            )
            if available_delivery_methods:
                for i, m in enumerate(available_delivery_methods):
                    self.logger.debug(f"  Delivery method {i+1}: {m}")

            # Retrieve core fields
            exchange_rate = calculations.get("exchangeRate")
            transfer_fee = calculations.get("transferFee", 0.0)
            amount_to = calculations.get("amountTo", 0.0)
            currency_to = calculations.get("currencyTo")
            total_fee = calculations.get("totalFeesAndTaxes", 0.0)

            if not exchange_rate:
                base_result["error_message"] = "Missing exchangeRate in RIA calculations"
                base_result["raw_response"] = raw_calc
                return self.standardize_response(base_result, provider_specific_data=True)

            # If RIA decided a different currency for the receiving side
            if currency_to and currency_to != dest_currency:
                base_result["destination_currency"] = currency_to

            # Mark success and add additional data
            base_result.update(
                {
                    "success": True,
                    "destination_amount": amount_to,
                    "exchange_rate": exchange_rate,
                    "fee": total_fee,
                    "raw_response": raw_calc,
                }
            )

            # Add delivery and payment methods if available
            if available_delivery_methods:
                self.logger.info(
                    f"Adding {len(available_delivery_methods)} delivery methods to response"
                )
                base_result["available_delivery_methods"] = available_delivery_methods

            if available_payment_methods:
                self.logger.info(
                    f"Adding {len(available_payment_methods)} payment methods to response"
                )
                base_result["available_payment_methods"] = available_payment_methods

            # Create the standardized response, passing any extracted methods
            response = self.standardize_response(base_result, provider_specific_data=True)

            # Double-check that standardized method preserves our delivery methods
            if available_delivery_methods and "available_delivery_methods" not in response:
                self.logger.warning("Delivery methods lost in standardization! Adding them back.")
                response["available_delivery_methods"] = available_delivery_methods

            return response

        except (RIAConnectionError, RIAAuthenticationError) as ce:
            base_result["error_message"] = f"RIA connection/auth error: {str(ce)}"
            return self.standardize_response(base_result)
        except Exception as exc:
            self.logger.error("RIA get_quote unexpected error: %s", exc, exc_info=True)
            base_result["error_message"] = f"Unexpected RIA error: {str(exc)}"
            return self.standardize_response(base_result)

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_country: str,
        send_currency: str,
        receive_currency: str,
        **kwargs,
    ) -> Dict[str, Any]:
        dest_country = kwargs.get("dest_country", "")
        payment_method = kwargs.get("payment_method", self.DEFAULT_PAYMENT_METHOD)
        delivery_method = kwargs.get("delivery_method", self.DEFAULT_DELIVERY_METHOD)

        return self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            dest_currency=receive_currency,
            source_country=send_country,
            dest_country=dest_country,
            payment_method=payment_method,
            delivery_method=delivery_method,
        )

    def _extract_calculations(self, full_response: Dict[str, Any]) -> Dict[str, Any]:
        if "calculations" in full_response:
            return full_response["calculations"]

        model = full_response.get("model", {})
        if "calculations" in model:
            return model["calculations"]

        transfer_details = model.get("transferDetails", {})
        if "calculations" in transfer_details:
            return transfer_details["calculations"]

        return {}

    def _extract_delivery_methods(self, raw_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract available delivery methods and their rates from the response.

        Returns a list of delivery method objects with standardized names and rates.
        """
        # Simple, direct approach to extract delivery methods
        result = []

        try:
            # Get transfer details
            model = raw_response.get("model", {})
            transfer_details = model.get("transferDetails", {})
            transfer_options = transfer_details.get("transferOptions", {})
            delivery_methods = transfer_options.get("deliveryMethods", [])

            # Get rates if available
            calculations = transfer_details.get("calculations", {})
            variable_rates = calculations.get("variableRates", [])

            # Create rate map
            rate_map = {}
            for rate in variable_rates:
                if isinstance(rate, dict) and "value" in rate and "exchangeRate" in rate:
                    rate_map[rate["value"]] = {
                        "exchange_rate": rate["exchangeRate"],
                        "is_best_rate": rate.get("isBestRate", False),
                    }

            # Log basic info
            self.logger.debug(
                f"Found {len(delivery_methods)} delivery methods and {len(rate_map)} rate entries"
            )

            # Simply iterate and add to result
            for i, method in enumerate(delivery_methods):
                if not isinstance(method, dict):
                    self.logger.warning(
                        f"Delivery method at index {i} is not a dictionary: {method}"
                    )
                    continue

                if "value" not in method or "text" not in method:
                    self.logger.warning(
                        f"Delivery method at index {i} missing required keys: {method}"
                    )
                    continue

                code = method["value"]
                name = method["text"]
                standardized_name = self.DELIVERY_METHOD_MAP.get(code, code.lower())

                method_info = {
                    "method_code": code,
                    "method_name": name,
                    "standardized_name": standardized_name,
                }

                # Add rate if available
                if code in rate_map:
                    method_info["exchange_rate"] = rate_map[code]["exchange_rate"]
                    method_info["is_best_rate"] = rate_map[code]["is_best_rate"]

                result.append(method_info)
                self.logger.debug(f"Added delivery method: {method_info}")

            # Final check and fallback if extraction failed
            if not result and delivery_methods:
                self.logger.warning(
                    f"Extraction failed despite finding methods. Using direct extraction."
                )
                # Last resort: directly add methods without transformation
                for method in delivery_methods:
                    if isinstance(method, dict) and "value" in method and "text" in method:
                        result.append(
                            {
                                "method_code": method["value"],
                                "method_name": method["text"],
                                "standardized_name": self.DELIVERY_METHOD_MAP.get(
                                    method["value"], method["value"].lower()
                                ),
                            }
                        )

            return result
        except Exception as e:
            self.logger.error(f"Error extracting delivery methods: {str(e)}", exc_info=True)
            return []

    def _extract_payment_methods(self, raw_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract available payment methods from the response.

        Returns a list of payment method objects with standardized names.
        """
        result = []

        try:
            # Get payment methods in a simple, direct way
            model = raw_response.get("model", {})
            transfer_details = model.get("transferDetails", {})
            transfer_options = transfer_details.get("transferOptions", {})
            payment_methods = transfer_options.get("paymentMethods", [])

            # Simply iterate and add to result
            for i, method in enumerate(payment_methods):
                if not isinstance(method, dict):
                    self.logger.warning(
                        f"Payment method at index {i} is not a dictionary: {method}"
                    )
                    continue

                if "value" not in method or "text" not in method:
                    self.logger.warning(
                        f"Payment method at index {i} missing required keys: {method}"
                    )
                    continue

                code = method["value"]
                name = method["text"]
                standardized_name = self.PAYMENT_METHOD_MAP.get(code, code.lower())

                method_info = {
                    "method_code": code,
                    "method_name": name,
                    "standardized_name": standardized_name,
                }

                result.append(method_info)
                self.logger.debug(f"Added payment method: {method_info}")

            return result
        except Exception as e:
            self.logger.error(f"Error extracting payment methods: {str(e)}", exc_info=True)
            return []

    def close(self):
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
