import logging
import requests
from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid
import time
import json
import os
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from apps.providers.wirebarley.exceptions import (
    WireBarleyError,
    WireBarleyAuthError,
    WireBarleySessionError,
    WireBarleyAPIError,
    WireBarleyRateError,
    WireBarleyValidationError,
    WireBarleyQuoteError,
    WireBarleyCorridorError,
    WireBarleyThresholdError
)

"""
WireBarley API Integration Module

This module provides an aggregator-ready integration with WireBarley's API for remittance services.
It returns standardized responses in the aggregator format, with no fallback or mock data.

Key features:
- No fallback data - returns "success": false if API calls fail
- Standard aggregator response fields
- Session-based authentication with Selenium fallback
- Comprehensive error handling and reporting

AUTHENTICATION:
- Direct cookie injection (preferred) - provide cookies from an authenticated browser session
- Selenium automation (fallback) - automate browser login process

ENVIRONMENT VARIABLES:
- WIREBARLEY_COOKIES: JSON string of cookie name/value pairs (for direct cookie injection)
- WIREBARLEY_USER_AGENT: Browser User-Agent to use (optional)
- WIREBARLEY_EMAIL: Login email (for Selenium automation)
- WIREBARLEY_PASSWORD: Login password (for Selenium automation)
"""

logger = logging.getLogger(__name__)

class WireBarleyProvider(RemittanceProvider):
    """
    WireBarley Money Transfer Provider.
    
    This provider implements aggregator-standard responses with live data and no fallbacks.
    """
    
    # API URLS
    BASE_URL = "https://www.wirebarley.com"
    LOGIN_URL = "https://my.wirebarley.com/login"
    API_BASE_URL = "https://my.wirebarley.com"
    
    # For constructing API requests
    ORIGIN_COUNTRY = "US"  # Default origin country (United States)
    
    # Currency to country code mapping
    CURRENCY_TO_COUNTRY = {
        "USD": "US",  # US Dollar
        "NZD": "NZ",  # New Zealand Dollar
        "GBP": "GB",  # British Pound
        "AUD": "AU",  # Australian Dollar
        "EUR": "EU",  # Euro
        "CAD": "CA",  # Canadian Dollar
        "SGD": "SG",  # Singapore Dollar
        "HKD": "HK",  # Hong Kong Dollar
        "JPY": "JP",  # Japanese Yen
        "CNY": "CN",  # Chinese Yuan
        "LKR": "LK",  # Sri Lanka Rupee
        "ILS": "IL",  # Israeli New Shekel
        "PHP": "PH",  # Philippine Peso
        "MYR": "MY",  # Malaysian Ringgit
        "UZS": "UZ",  # Uzbekistan Sum
        "THB": "TH",  # Thai Baht
        "ZAR": "ZA",  # South African Rand
        "TRY": "TR",  # Turkish Lira
        "KRW": "KR",  # South Korean Won
        "IDR": "ID",  # Indonesian Rupiah
        "VND": "VN",  # Vietnamese Dong
        "RUB": "RU",  # Russian Ruble
        "NPR": "NP",  # Nepalese Rupee
        "INR": "IN",  # Indian Rupee
        "CHF": "CH",  # Swiss Franc
        "BDT": "BD",  # Bangladeshi Taka
        "TWD": "TW",  # Taiwan New Dollar
        "BHD": "BH",  # Bahraini Dinar
        "AED": "AE",  # United Arab Emirates Dirham
        "OMR": "OM",  # Omani Rial
        "SAR": "SA",  # Saudi Arabian Riyal
        "QAR": "QA",  # Qatari Riyal
        "PKR": "PK",  # Pakistani Rupee
    }
    
    # Default User-Agent
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    )
    
    # Session and amount constraints
    SESSION_VALID_DURATION = 3600  # 1 hour in seconds
    MIN_SUPPORTED_AMOUNT = Decimal("10.00")
    MAX_SUPPORTED_AMOUNT = Decimal("10000.00")
    
    # Request retry settings
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 0.5
    RETRY_STATUS_FORCELIST = [429, 500, 502, 503, 504]
    
    def __init__(self, name="wirebarley", **kwargs):
        """Initialize the WireBarley provider."""
        super().__init__(name=name, base_url=self.BASE_URL, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.session_timestamp = None
        
        # Cache for corridor data
        self._corridors_cache = {}
        self._cache_timestamp = {}
        self._cache_duration = 300  # 5 minutes cache duration
        
        # Initialize session
        self._initialize_session()
    
    def standardize_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Convert local result dictionary to aggregator-standard format."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # If success is false or missing, treat as failure
        success = result.get("success", False)
        error_message = result.get("error_message")

        # If not successful, return minimal aggregator failure shape
        if not success:
            return {
                "provider_id": self.name,
                "success": False,
                "error_message": error_message or "Unknown error from WireBarley"
            }

        # Otherwise fill aggregator success shape
        return {
            "provider_id": self.name,
            "success": True,
            "error_message": None,

            "send_amount": result.get("send_amount", 0.0),
            "source_currency": str(result.get("send_currency", "")).upper(),
            "destination_amount": result.get("receive_amount", 0.0),
            "destination_currency": str(result.get("receive_currency", "")),
            "exchange_rate": result.get("exchange_rate", 0.0),
            "fee": result.get("fee", 0.0),

            # Payment/Delivery methods (generic for WireBarley)
            "payment_method": "bankAccount",
            "delivery_method": "bankDeposit",
            "delivery_time_minutes": 1440,  # default 1 day in minutes
            "timestamp": result.get("timestamp", now_iso)
        }
    
    def _create_session_with_retry(self):
        """Create requests session with retry capability."""
        session = requests.Session()
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=self.RETRY_BACKOFF_FACTOR,
            status_forcelist=self.RETRY_STATUS_FORCELIST,
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session
    
    def _get_browser_cookies(self):
        """Get cookies from environment variable."""
        cookies_str = os.environ.get("WIREBARLEY_COOKIES")
        if not cookies_str:
            return None
        
        try:
            self.logger.info("Using WireBarley cookies from environment variable")
            return json.loads(cookies_str)
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON in WIREBARLEY_COOKIES")
            return None
    
    def _get_selenium_cookies(self):
        """Get cookies by automating login with Selenium."""
        email = os.environ.get("WIREBARLEY_EMAIL")
        password = os.environ.get("WIREBARLEY_PASSWORD")
        
        if not email or not password:
            self.logger.error("WIREBARLEY_EMAIL and WIREBARLEY_PASSWORD must be set for Selenium automation")
            return None
            
        try:
            # Initialize Chrome in headless mode
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            driver = webdriver.Chrome(options=options)
            
            # Go to login page
            driver.get(self.LOGIN_URL)
            
            # Wait for the login form and fill it
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            
            # Fill the login form
            driver.find_element(By.ID, "email").send_keys(email)
            driver.find_element(By.ID, "password").send_keys(password)
            
            # Submit the form and wait for redirection
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            # Wait for login to complete
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
            )
            
            # Get cookies
            cookies = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}
            
            driver.quit()
            return cookies
            
        except Exception as e:
            self.logger.error(f"Selenium automation error: {str(e)}")
            try:
                driver.quit()
            except:
                pass
            return None
    
    def _initialize_session(self):
        """Initialize session with cookies."""
        # First try getting cookies from environment
        cookies = self._get_browser_cookies()
        
        # Fall back to Selenium automation if needed
        if not cookies:
            self.logger.info("No cookies found in environment, falling back to Selenium")
            cookies = self._get_selenium_cookies()
            
            if not cookies:
                self.logger.error("Failed to get browser session data")
                return False
        
        # Create session with retry capability
        self.session = self._create_session_with_retry()
        
        # Set cookies
        for name, value in cookies.items():
            self.session.cookies.set(name, value)
        
        # Set user agent
        self.session.headers.update({
            "User-Agent": os.environ.get("WIREBARLEY_USER_AGENT", self.DEFAULT_USER_AGENT)
        })
        
        self.session_timestamp = time.time()
        self.logger.info("WireBarley session initialized successfully")
        return True
    
    def _validate_session(self):
        """Validate session by making a test request."""
        if not self.session:
            return False
            
        try:
            test_url = "https://my.wirebarley.com/remittance"  # an auth-protected page
            resp = self.session.get(test_url, timeout=10)
            return resp.status_code < 400  # Success if status code is 2xx or 3xx
        except requests.RequestException:
            return False
    
    def _ensure_valid_session(self):
        """Ensure we have a valid session."""
        now = time.time()
        if (self.session_timestamp is None) or ((now - self.session_timestamp) > self.SESSION_VALID_DURATION):
            self.logger.info("WireBarley session expired or missing, re-initializing")
            self._initialize_session()
    
    def _fetch_api_data(
        self,
        send_currency: str,
        receive_country_code: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Fetch data from WireBarley API."""
        try:
            # Build URL
            url = f"{self.API_BASE_URL}/api/v1/remittance/calculateAmount"
            
            # Build payload
            payload = {
                "sendCountry": self.ORIGIN_COUNTRY,
                "sendCurrency": send_currency,
                "receiveCountry": receive_country_code,
                "amount": float(amount),
                "receiveMethod": "BANK_ACCOUNT",
                "paymentMethod": "REGULAR",
            }
            
            # Make request
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            response = self.session.post(url, json=payload, headers=headers, timeout=15)
            
            # Parse response
            if response.status_code != 200:
                return {
                    "success": False,
                    "error_message": f"API error: HTTP {response.status_code}"
                }
            
            data = response.json()
            
            # Handle API-level errors
            if data.get("status") != "success":
                error_msg = data.get("message", "Unknown API error")
                return {
                    "success": False,
                    "error_message": f"API error: {error_msg}"
                }
            
            # Extract data we need
            corridor_obj = data.get("data", {})
            
            # Get exchange rate
            wb_rate = self._pick_threshold_rate(corridor_obj, amount)
            if not wb_rate:
                return {
                    "success": False,
                    "error_message": "Could not determine exchange rate"
                }
            
            # Calculate fee
            fee_val = self._calculate_fee(corridor_obj, amount)
            
            # Calculate receive amount
            receive_amount = float(amount) * wb_rate
            
            # Return standardized data
            return {
                "success": True,
                "send_amount": float(amount),
                "send_currency": send_currency,
                "receive_amount": receive_amount,
                "receive_currency": data.get("data", {}).get("receiveCurrency"),
                "exchange_rate": wb_rate,
                "fee": fee_val,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_data": data  # Include raw API response for debugging
            }
            
        except requests.RequestException as e:
            return {
                "success": False,
                "error_message": f"Request error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error_message": f"Unexpected error: {str(e)}"
            }
    
    def _pick_threshold_rate(self, corridor_obj: Dict[str, Any], amount: Decimal) -> Optional[float]:
        """Select the appropriate exchange rate based on amount thresholds in wbRateData."""
        try:
            # Get the wb rate data which contains threshold information
            wbRateData = corridor_obj.get("wbRateData", {})
            if wbRateData:
                # Handle threshold-based rates
                thresholds = []
                def parse_key(i):
                    thr_k = "threshold" if i == 0 else f"threshold{i}"
                    rate_k = "wbRate" if i == 0 else f"wbRate{i}"
                    return (wbRateData.get(thr_k), wbRateData.get(rate_k))

                # Parse up to 6 thresholds (0..5)
                for i in range(6):
                    thr, rt = parse_key(i)
                    if thr is not None or rt is not None:
                        thr_f = float(thr) if thr is not None else float('inf')
                        rt_f = float(rt) if rt is not None else 0.0
                        thresholds.append((thr_f, rt_f))

                # Sort thresholds by ascending amount
                thresholds.sort(key=lambda x: x[0])
                
                # Find first threshold that is >= amount
                for (thr_val, rate_val) in thresholds:
                    if amount <= Decimal(str(thr_val)):
                        return rate_val
                        
                # If amount is above all thresholds, use the last threshold rate
                if thresholds:
                    return thresholds[-1][1]

            # Fallback to standard rates
            return corridor_obj.get("exchangeRate") or corridor_obj.get("wbRate")
            
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error picking threshold rate: {e}")
            # Fallback to standard rate
            return corridor_obj.get("exchangeRate") or corridor_obj.get("wbRate")
    
    def _calculate_fee(self, corridor_obj: Dict[str, Any], amount: Decimal) -> float:
        """Calculate the fee for a transaction based on corridor data."""
        default_fee = 4.99
        try:
            # First check payment fees
            payment_fees = corridor_obj.get("paymentFees", [])
            fee_val = self._find_fee_in_array(payment_fees, amount)
            if fee_val is not None:
                return fee_val

            # If no payment fee found, check transfer fees
            transfer_fees = corridor_obj.get("transferFees", [])
            fee_val2 = self._find_fee_in_array(transfer_fees, amount)
            if fee_val2 is not None:
                return fee_val2

            # Default fee if nothing found
            return default_fee
        except Exception as e:
            self.logger.error(f"Fee calculation error: {e}")
            return default_fee
    
    def _find_fee_in_array(self, fees_array: List[Dict[str, Any]], amount: Decimal) -> Optional[float]:
        """Find the applicable fee in a fee array based on amount thresholds."""
        if not fees_array:
            return None
            
        for fee_obj in fees_array:
            min_amount = Decimal(str(fee_obj.get("min", 0)))
            max_amount = Decimal(str(fee_obj.get("max", float('inf'))))
            
            # Check if this fee structure applies to our amount
            if min_amount <= amount <= max_amount:
                # Find applicable fee within this structure based on thresholds
                thresholds = []
                
                # Collect all threshold/fee pairs
                for i in range(1, 11):  # fee1 through fee10
                    threshold_key = f"threshold{i}"
                    fee_key = f"fee{i}"
                    
                    if threshold_key in fee_obj and fee_key in fee_obj:
                        threshold = fee_obj[threshold_key]
                        fee = fee_obj[fee_key]
                        
                        if threshold is not None and fee is not None:
                            thresholds.append((Decimal(str(threshold)), float(fee)))
                
                # Add base fee (fee1) with zero threshold
                if "fee1" in fee_obj:
                    base_fee = float(fee_obj["fee1"])
                    thresholds.append((Decimal("0"), base_fee))
                    
                # Sort by threshold ascending
                thresholds.sort(key=lambda x: x[0])
                
                # Find applicable fee based on threshold
                applicable_fee = None
                for threshold, fee in thresholds:
                    if amount >= threshold:
                        applicable_fee = fee
                
                return applicable_fee
        
        return None
    
    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_currency: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Get exchange rate information for a specific currency pair."""
        try:
            # First try using the public API endpoint which doesn't require authentication
            country_code = self.CURRENCY_TO_COUNTRY.get(receive_currency, receive_currency[:2])
            
            # Use public endpoint to get rates for all corridors in a single request
            public_url = f"{self.BASE_URL}/my/remittance/api/v1/exrate/{self.ORIGIN_COUNTRY}/{send_currency}"
            
            try:
                session = self._create_session_with_retry()
                response = session.get(
                    public_url,
                    headers={
                        "Content-Type": "application/json",
                        "Pragma": "no-cache",
                        "Accept": "*/*",
                        "Sec-Fetch-Site": "same-origin",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Cache-Control": "no-cache",
                        "Sec-Fetch-Mode": "cors",
                        "User-Agent": self.DEFAULT_USER_AGENT,
                        "Referer": f"{self.BASE_URL}/",
                        "Device-Type": "WEB",
                        "Lang": "en",
                        "Request-ID": str(uuid.uuid4()),
                        "Request-Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    },
                    cookies={"lang": "en"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == 0 and "data" in data and data["data"] is not None:
                        # Find the matching rate data for our corridor
                        for rate_data in data["data"]["exRates"]:
                            if rate_data.get("currency") == receive_currency:
                                # Found our corridor - extract rate information
                                wb_rate = rate_data.get("wbRate", 0)
                                
                                # Get threshold-based rate if available
                                if "wbRateData" in rate_data:
                                    threshold_rate = self._pick_threshold_rate(rate_data, send_amount)
                                    if threshold_rate:
                                        wb_rate = threshold_rate
                                
                                # Find the fee structure
                                fee = 0
                                if "paymentFees" in rate_data:
                                    for fee_data in rate_data["paymentFees"]:
                                        # Default to first available fee structure
                                        fee = self._calculate_fee({"paymentFees": [fee_data]}, send_amount)
                                        break
                                
                                # Calculate destination amount
                                destination_amount = float(send_amount) * wb_rate
                                
                                return {
                                    "success": True,
                                    "send_amount": float(send_amount),
                                    "send_currency": send_currency,
                                    "receive_amount": destination_amount,
                                    "receive_currency": receive_currency,
                                    "exchange_rate": wb_rate,
                                    "fee": fee,
                                    "payment_method": "bankAccount",
                                    "delivery_method": "bankDeposit",
                                    "delivery_time_minutes": 1440  # 24 hours
                                }
            except Exception as e:
                self.logger.debug(f"Public API error: {str(e)}")
            
            # Continue with original authenticated flow if public API didn't work
            self._ensure_valid_session()
            
            # Base result for failures
            aggregator_fail = {
                "success": False,
                "provider_id": self.name,
                "error_message": None
            }
            
            # Validate input
            if send_currency not in self.CURRENCY_TO_COUNTRY:
                aggregator_fail["error_message"] = f"Unsupported send currency: {send_currency}"
                return self.standardize_response(aggregator_fail)
            
            if receive_currency not in self.CURRENCY_TO_COUNTRY:
                aggregator_fail["error_message"] = f"Unsupported receive currency: {receive_currency}"
                return self.standardize_response(aggregator_fail)
            
            if not (self.MIN_SUPPORTED_AMOUNT <= send_amount <= self.MAX_SUPPORTED_AMOUNT):
                aggregator_fail["error_message"] = f"Amount {send_amount} not in allowed range {self.MIN_SUPPORTED_AMOUNT}-{self.MAX_SUPPORTED_AMOUNT}"
                return self.standardize_response(aggregator_fail)

            # Get the receive country code
            receive_country_code = self.CURRENCY_TO_COUNTRY.get(receive_currency)
            if not receive_country_code:
                aggregator_fail["error_message"] = f"Could not find country code for currency: {receive_currency}"
                return self.standardize_response(aggregator_fail)

            # Ensure session is valid
            self._ensure_valid_session()
            if not self.session:
                aggregator_fail["error_message"] = "No valid session. Check WireBarley cookies or Selenium login."
                return self.standardize_response(aggregator_fail)

            # Fetch data from API
            raw_data = self._fetch_api_data(send_currency, receive_country_code, send_amount)
            if raw_data.get("success") is False:
                # pass along the error
                aggregator_fail["error_message"] = raw_data.get("error_message", "Unknown WireBarley error")
                return self.standardize_response(aggregator_fail)

            # Success! Create standardized response
            aggregator_ok = {
                "success": True,
                "provider_id": self.name,
                "send_amount": float(send_amount),
                "send_currency": send_currency,
                "receive_amount": raw_data.get("receive_amount"),
                "receive_currency": receive_currency,
                "exchange_rate": raw_data.get("exchange_rate"),
                "fee": raw_data.get("fee", 0.0),
                "timestamp": raw_data.get("timestamp"),
                "raw_response": raw_data.get("raw_data")  # Include raw API response for debugging
            }
            return self.standardize_response(aggregator_ok)
        except Exception as e:
            self.logger.error(f"Error in get_exchange_rate: {e}", exc_info=True)
            return self.standardize_response({
                "success": False,
                "error_message": f"Exchange rate error: {str(e)}"
            })
    
    def get_quote(
        self,
        amount: Optional[Decimal] = None,
        source_currency: str = "USD",
        destination_currency: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get a quote for a money transfer."""
        if not amount:
            return self.standardize_response({
                "success": False,
                "error_message": "Amount is required"
            })
        
        try:
            # Convert to Decimal if needed
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
            
            # Call get_exchange_rate for the actual implementation
            if amount < 0:
                return self.standardize_response({
                    "success": False,
                    "error_message": "Amount must be positive"
                })
                
            return self.get_exchange_rate(
                send_amount=amount,
                send_currency=source_currency,
                receive_currency=destination_currency,
                **kwargs
            )
            
        except Exception as e:
            self.logger.error(f"Error in get_quote: {e}", exc_info=True)
            return self.standardize_response({
                "success": False,
                "error_message": f"Quote error: {str(e)}"
            })
    
    def get_corridors(self, source_currency: str = "USD") -> Dict[str, Any]:
        """Get available corridors for a source currency."""
        aggregator_fail = {
            "success": False,
            "provider_id": self.name,
            "error_message": None
        }
        
        # Validate currency
        if source_currency not in self.CURRENCY_TO_COUNTRY:
            aggregator_fail["error_message"] = f"Unsupported source currency: {source_currency}"
            return self.standardize_response(aggregator_fail)
        
        # Ensure session is valid
        self._ensure_valid_session()
        if not self.session:
            aggregator_fail["error_message"] = "No valid session"
            return self.standardize_response(aggregator_fail)
        
        try:
            # Get source country code
            source_country_code = self.CURRENCY_TO_COUNTRY[source_currency]
            
            # Build request
            headers = {
                "Request-Id": str(uuid.uuid4()),
                "Content-Type": "application/json"
            }
            
            # Try to use cached data first
            cache_key = f"corridors_{source_currency}"
            if (
                cache_key in self._corridors_cache and
                cache_key in self._cache_timestamp and
                (time.time() - self._cache_timestamp[cache_key]) < self._cache_duration
            ):
                return self._corridors_cache[cache_key]
            
            # Get data from API
            url = f"{self.API_BASE_URL}/api/v1/remittance/getRemittanceList?sendCurrency={source_currency}&sendCountry={source_country_code}"
            response = self.session.get(url, headers=headers, timeout=15)
            
            # Parse response
            if response.status_code != 200:
                aggregator_fail["error_message"] = f"API error: HTTP {response.status_code}"
                return self.standardize_response(aggregator_fail)
                
            data = response.json()
            
            # Handle API-level errors
            if data.get("status") != "success":
                error_msg = data.get("message", "Unknown API error")
                aggregator_fail["error_message"] = f"API error: {error_msg}"
                return self.standardize_response(aggregator_fail)
            
            # Extract corridor information
            corridors = []
            send_info = data.get("data", {}).get("sendInfo", {})
            receive_list = data.get("data", {}).get("receiveList", [])
            
            for receive_info in receive_list:
                country_code = receive_info.get("receiveCountry")
                currency_code = receive_info.get("receiveCurrency")
                
                # Find matching currency in our mapping
                for currency, country in self.CURRENCY_TO_COUNTRY.items():
                    if country == country_code and currency == currency_code:
                        min_amount = receive_info.get("min") or 10
                        max_amount = receive_info.get("max") or 10000
                        
                        corridors.append({
                            "source_currency": source_currency,
                            "target_currency": currency,
                            "country_code": country_code,
                            "min_amount": str(min_amount),
                            "max_amount": str(max_amount)
                        })
            
            # Create response
            result = {
                "success": True,
                "provider_id": self.name,
                "corridors": corridors
            }
            
            # Cache the result
            self._corridors_cache[cache_key] = result
            self._cache_timestamp[cache_key] = time.time()
            
            return self.standardize_response(result)
            
        except Exception as e:
            aggregator_fail["error_message"] = f"Error getting corridors: {str(e)}"
            return self.standardize_response(aggregator_fail)
    
    def close(self):
        """Close and clean up resources."""
        if self.session:
            try:
                self.session.close()
            except:
                pass
            
        self.session = None
        self.session_timestamp = None 