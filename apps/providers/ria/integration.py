"""
RIA Money Transfer Integration

This module implements the integration with RIA Money Transfer API for remittance services.
Unlike Western Union, RIA provides explicit delivery methods and payment methods.

DELIVERY METHODS:
---------------------------------
- BankDeposit: Bank account deposit
- CashPickup: Cash pickup at agent locations
- HomeDelivery: Cash delivery to home (select markets)
- MobileWallet: Mobile wallet transfer
- OfficePickup: Pickup at RIA office
- MobilePayment: Mobile payment services

PAYMENT METHODS:
---------------------------------
- BankAccount: Bank account transfer
- DebitCard: Debit card payment
- CreditCard: Credit card payment

Important API notes:
1. RIA requires token-based authentication via the /Authorization/session endpoint
2. The calculator must be initialized to get country codes and options
3. Each corridor (send country → receive country) supports different combinations
4. Exchange rates and fees vary by delivery method and payment method
5. The API response structure has calculations in two possible locations

For more details, see the test_discover_supported_methods test method in tests.py
"""

import logging
import requests
import time
import json
from urllib3.util import SSLContext
from urllib3.util.ssl_ import create_urllib3_context
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
import random
import string
from datetime import datetime
import uuid
import certifi
from typing import Dict, Optional, Any

from apps.providers.ria.exceptions import (
    RIAError,
    RIAAuthenticationError,
    RIAValidationError,
    RIAConnectionError
)

# Enable debug logging for urllib3 if needed
urllib3.add_stderr_logger()

class TLSAdapter(HTTPAdapter):
    """Custom adapter to handle RIA's TLS requirements."""
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = create_urllib3_context()
        return super().proxy_manager_for(*args, **kwargs)

class RIAProvider:
    """RIA Money Transfer API integration provider."""
    
    BASE_URL = "https://public.riamoneytransfer.com"

    def __init__(self, timeout: int = 30):
        """
        Initialize RIA provider with automatic token retrieval.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.name = "RIA"
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self._session = requests.Session()
        self.bearer_token = None
        self.token_expiry = None
        self.calculator_data = None
        self.debug_mode = True  # Always on debug mode to capture full responses

        # Use certifi's CA bundle for SSL verification
        self._session.verify = certifi.where()
        self.logger.debug("Using certifi CA bundle from: %s", certifi.where())

        # Set default Country/ISO headers to US
        country_code = "US"
        
        # Safari-based browser headers for better compatibility
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-Dest': 'empty',
            'Priority': 'u=3, i',
            'AppType': '2',
            'AppVersion': '4.0',
            'Client-Type': 'PublicSite',
            'CultureCode': 'en-US',
            'Content-Type': 'application/json',
            'Origin': 'https://www.riamoneytransfer.com',
            'Referer': 'https://www.riamoneytransfer.com/',
            'X-Client-Platform': 'Web',
            'X-Client-Version': '4.0.0',
            'X-Device-Id': 'WEB-'+''.join(random.choices(string.ascii_uppercase + string.digits, k=16)),
            'Connection': 'keep-alive',
            'IAmFrom': country_code,
            'CountryId': country_code,
            'IsoCode': country_code
        })

        # Configure modern TLS settings
        self._session.mount('https://', TLSAdapter())
        self._configure_tls()

        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        self._session.mount('https://', TLSAdapter(max_retries=retry_strategy))

        # Initialize by getting session token and initializing calculator
        self.get_session_info()
        self.initialize_calculator()

    def _configure_tls(self):
        """Force modern TLS configuration."""
        ctx = create_urllib3_context()
        ctx.options |= (
            0x4  # OP_LEGACY_SERVER_CONNECT
            | 0x80000  # OP_ENABLE_MIDDLEBOX_COMPAT
        )
        ctx.load_default_certs()

    def get_session_info(self) -> dict:
        """
        Get session info and bearer token via GET /Authorization/session.
        
        Returns:
            Dict containing session information.
        
        Raises:
            RIAConnectionError: If connection to API fails
            RIAError: For other RIA-specific errors
        """
        try:
            self.logger.debug("Getting session info and token from /Authorization/session")
            
            response = self._session.get(
                f"{self.BASE_URL}/Authorization/session",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            self.logger.debug("Response headers: %s", dict(response.headers))
            
            session_data = response.json()
            
            # Check for bearer token in response headers
            if 'bearer' in response.headers:
                self.bearer_token = response.headers['bearer']
                self._session.headers['Authorization'] = f'Bearer {self.bearer_token}'
                self.logger.info("Acquired bearer token from session response headers")
                
                # Check for expiry information
                if 'expiresIn' in response.headers:
                    expires_in = int(response.headers['expiresIn'])
                    self.token_expiry = time.time() + expires_in
                else:
                    self.token_expiry = time.time() + 1800  # Default 30 minutes
            else:
                self.logger.warning("No bearer token in session response headers")
            
            # Store any cookies that were set
            if response.cookies:
                self.logger.debug("Received cookies: %s", dict(response.cookies))
            
            return session_data
            
        except requests.RequestException as e:
            self.logger.error("Session initialization failed: %s", str(e), exc_info=True)
            if hasattr(e, 'response') and e.response is not None:
                raise RIAConnectionError(f"Failed to get session info: {e.response.status_code}")
            raise RIAConnectionError(f"Failed to get session info: {str(e)}")

    def initialize_calculator(self) -> dict:
        """
        Initialize calculator and handle any new token from response.
        
        Returns:
            Dict containing calculator initialization data.
            
        Raises:
            RIAConnectionError: If connection to API fails
            RIAError: For other RIA-specific errors
        """
        try:
            response = self._session.get(
                f"{self.BASE_URL}/Calculator/Initialize",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            self.logger.debug("Initialize calculator headers: %s", dict(response.headers))
            
            init_data = response.json()
            
            # Store calculator data for future use
            self.calculator_data = init_data
            
            # Check for updated bearer token
            if 'bearer' in response.headers:
                new_token = response.headers['bearer']
                if new_token != self.bearer_token:
                    self.bearer_token = new_token
                    self._session.headers['Authorization'] = f'Bearer {new_token}'
                    self.logger.info("Updated bearer token from calculator init response")
                    
                    if 'expiresIn' in response.headers:
                        expires_in = int(response.headers['expiresIn'])
                        self.token_expiry = time.time() + expires_in
            
            self.logger.debug("Calculator initialized successfully")
            return init_data
            
        except requests.RequestException as e:
            self.logger.error("Calculator init failed: %s", str(e), exc_info=True)
            if hasattr(e, 'response') and e.response is not None:
                raise RIAConnectionError(f"Failed to initialize calculator: {e.response.status_code}")
            raise RIAConnectionError(f"Failed to initialize calculator: {str(e)}")

    def _ensure_valid_token(self):
        """
        Check token expiry and refresh if needed.
        
        Raises:
            RIAAuthenticationError: If no bearer token is available
        """
        if not self.bearer_token:
            self.logger.error("No bearer token available")
            raise RIAAuthenticationError("No bearer token available")
            
        if self.token_expiry and time.time() > (self.token_expiry - 60):
            self.logger.debug("Token expired or about to expire; refreshing session")
            self.get_session_info()

    def get_available_delivery_methods(self, receive_country: str, send_country: str = "US") -> dict:
        """
        Get all available delivery methods for a specific corridor.
        
        Args:
            receive_country: 2-letter country code for destination
            send_country: 2-letter country code for source (default: US)
            
        Returns:
            Dictionary of available delivery methods with supported payment methods
        """
        if not self.calculator_data:
            self.initialize_calculator()
            
        # Standard delivery methods to test
        delivery_methods = {
            "BankDeposit": "Bank Deposit",
            "CashPickup": "Cash Pickup",
            "HomeDelivery": "Home Delivery",
            "MobileWallet": "Mobile Wallet", 
            "OfficePickup": "Office Pickup",
            "MobilePayment": "Mobile Payment"
        }
        
        # Payment methods to try with each delivery method
        payment_methods = ["BankAccount", "DebitCard", "CreditCard"]
        
        results = {}
        
        # Use a higher amount to improve success rate
        test_amount = 300
        send_currency = "USD" if send_country == "US" else "EUR"
        
        # Make a call that will allow us to check all delivery methods at once if possible
        try:
            # First try a general check with BankDeposit to get info
            general_result = self.calculate_rate(
                send_amount=test_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                payment_method="DebitCard",
                delivery_method="BankDeposit",
                send_country=send_country
            )
            
            # Log the full raw response for analysis
            if general_result and "raw_response" in general_result:
                self.logger.debug(f"Raw response for {receive_country}: {json.dumps(general_result['raw_response'], indent=2)}")
                
                # Check if we can extract available methods from the response
                if "transferOptions" in general_result["raw_response"].get("model", {}):
                    options = general_result["raw_response"]["model"]["transferOptions"]
                    self.logger.info(f"Found transfer options in response: {options}")
            
        except Exception as e:
            self.logger.error(f"Error checking general availability: {str(e)}")
        
        # Make minimum amount API calls (one per delivery method) to test availability
        for delivery_method, display_name in delivery_methods.items():
            method_result = {
                "supported": False,
                "working_payment_methods": [],
                "response": None
            }
            
            for payment_method in payment_methods:
                try:
                    # Use a direct call approach instead of the wrapper method
                    payload = {
                        "selections": {
                            "countryTo": receive_country.upper(),
                            "amountFrom": float(test_amount),
                            "amountTo": None,
                            "currencyFrom": send_currency,
                            "currencyTo": None,
                            "paymentMethod": payment_method,
                            "deliveryMethod": delivery_method,
                            "shouldCalcAmountFrom": False,
                            "shouldCalcVariableRates": True,
                            "state": None,
                            "agentToId": None,
                            "stateTo": None,
                            "agentToLocationId": None,
                            "promoCode": None,
                            "promoId": 0,
                            "transferReason": None,
                            "countryFrom": send_country.upper()
                        }
                    }
                    
                    # Direct call to calculate
                    correlation_id = str(uuid.uuid4())
                    response = self._session.post(
                        f"{self.BASE_URL}/MoneyTransferCalculator/Calculate",
                        json=payload,
                        headers={"CorrelationId": correlation_id},
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Check if there's valid calculation data
                        has_calculations = False
                        
                        if "model" in result and "transferDetails" in result["model"] and "calculations" in result["model"]["transferDetails"]:
                            calculations = result["model"]["transferDetails"]["calculations"]
                            
                            # If we have a valid exchange rate, this method works
                            if calculations.get("exchangeRate") is not None:
                                method_result["supported"] = True
                                method_result["working_payment_methods"].append(payment_method)
                                method_result["response"] = result
                                self.logger.info(f"Found working method: {delivery_method} with {payment_method}")
                                
                                # Check if we have at least one payment method
                                if len(method_result["working_payment_methods"]) == 1:
                                    # If this is the first working payment method, save the full response
                                    method_result["response"] = result
                        
                        # Even if exchange rate is null, consider it supported if no explicit error
                        elif "errorResponse" not in result and payment_method not in method_result["working_payment_methods"]:
                            # Add it as potentially working
                            method_result["working_payment_methods"].append(payment_method)
                            method_result["supported"] = True
                            if method_result["response"] is None:
                                method_result["response"] = result
                    
                except Exception as e:
                    self.logger.debug(f"Error testing {delivery_method} with {payment_method}: {str(e)}")
            
            results[delivery_method] = method_result
            
        return results

    def calculate_rate(self, send_amount: float, send_currency: str, receive_country: str,
                      payment_method: str = "DebitCard", delivery_method: str = "BankDeposit",
                      send_country: str = "US") -> dict:
        """
        Calculate rate via POST /MoneyTransferCalculator/Calculate.
        
        Args:
            send_amount: Amount to send
            send_currency: Currency code to send (e.g., USD)
            receive_country: Country code to receive money (e.g., MX)
            payment_method: Payment method (DebitCard, CreditCard, BankAccount)
            delivery_method: Delivery method (BankDeposit, CashPickup, etc.)
            send_country: Source country code (default: US)
            
        Returns:
            Dictionary with rate details or None if calculation failed
        """
        try:
            self._ensure_valid_token()
            
            payload = {
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
                    "state": None,
                    "agentToId": None,
                    "stateTo": None,
                    "agentToLocationId": None,
                    "promoCode": None,
                    "promoId": 0,
                    "transferReason": None,
                    "countryFrom": send_country.upper()
                }
            }

            # Get full response to inspect
            full_response = self._do_calculate(payload, return_full=True)
            
            if full_response is None:
                return None
                
            # For debugging - log the complete response structure
            if self.debug_mode:
                self.logger.debug(f"Full calculate response: {json.dumps(full_response, indent=2)}")
            
            # Check if there's an error
            if "errorResponse" in full_response and full_response["errorResponse"]:
                self.logger.warning(f"Error in calculate response: {full_response['errorResponse']}")
                return None
                
            # Extract fields from the correct model.calculations path
            model_calcs = full_response.get("model", {}).get("calculations", {})
            direct_calcs = full_response.get("calculations", {})
            
            # Try both possible locations for calculation data
            calculations = model_calcs if model_calcs.get("exchangeRate") is not None else direct_calcs
            
            # Return structured response
            result = {
                "provider": "RIA",
                "timestamp": datetime.now().isoformat(),
                "send_amount": send_amount,
                "send_currency": send_currency.upper(),
                "receive_country": receive_country.upper(),
                "exchange_rate": calculations.get("exchangeRate"),
                "transfer_fee": calculations.get("transferFee"),
                "receive_amount": calculations.get("amountTo"),
                "payment_method": payment_method,
                "delivery_method": delivery_method,
                "total_fee": calculations.get("totalFeesAndTaxes", 0),
                "promo_discount": calculations.get("promoAmount", 0),
                "currency_to": calculations.get("currencyTo"),
                "status_message": full_response.get("statusMessage"),
                "raw_response": full_response if self.debug_mode else None
            }
            
            return result

        except RIAAuthenticationError:
            raise
        except (requests.RequestException, ValueError, KeyError) as e:
            self.logger.error(f"Calculation failed: {str(e)}", exc_info=True)
            return None

    def _do_calculate(self, payload: dict, return_full: bool = True) -> dict:
        """
        Execute calculation request.
        
        Args:
            payload: Request payload
            return_full: If True, return full response instead of just calculations (Default: True)
            
        Returns:
            Full response JSON or just calculations based on return_full (or None if request fails)
        """
        correlation_id = str(uuid.uuid4())
        
        try:
            response = self._session.post(
                f"{self.BASE_URL}/MoneyTransferCalculator/Calculate",
                json=payload,
                headers={
                    'CorrelationId': correlation_id
                },
                timeout=self.timeout
            )
            
            self.logger.debug(f"HTTP Response Status: {response.status_code}")
            self.logger.debug(f"HTTP Response Headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            # Check for token updates here too
            if 'bearer' in response.headers:
                new_token = response.headers['bearer']
                if new_token != self.bearer_token:
                    self.bearer_token = new_token
                    self._session.headers['Authorization'] = f'Bearer {new_token}'
                    self.logger.debug("Updated bearer token from calculate response")
            
            # Inspect Session-Analytics and other headers
            if 'Session-Analytics' in response.headers:
                self.logger.debug(f"Session Analytics: {response.headers['Session-Analytics']}")
            
            # Parse and return response
            result = response.json()
            
            if return_full:
                return result
            else:
                # Check both possible locations for calculation data
                model_calcs = result.get("model", {}).get("calculations", {})
                direct_calcs = result.get("calculations", {})
                
                # Return whichever has actual data
                if model_calcs.get("exchangeRate") is not None:
                    return model_calcs
                else:
                    return direct_calcs
                    
        except requests.RequestException as e:
            self.logger.error(f"Calculate request failed: {str(e)}", exc_info=True)
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response status: {e.response.status_code}")
                self.logger.error(f"Response body: {e.response.text[:1000]}")
            return None

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.close()