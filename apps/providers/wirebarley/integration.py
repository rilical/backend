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
from apps.providers.utils.country_currency_standards import validate_corridor

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
    
    # Add provider_id class attribute
    provider_id = "wirebarley"
    
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

        # Otherwise fill aggregator success shape with standard field names
        return {
            "provider_id": self.name,
            "success": True,
            "error_message": None,

            # Map to standard field names expected by the base provider
            "send_amount": result.get("source_amount", 0.0),
            "send_currency": str(result.get("source_currency", "")).upper(),
            "receive_amount": result.get("destination_amount", 0.0),
            "receive_currency": str(result.get("destination_currency", "")).upper(),
            "exchange_rate": result.get("exchange_rate", 0.0),
            "fee": result.get("fee", 0.0),

            # Payment/Delivery methods (generic for WireBarley)
            "payment_method": "BANK",
            "delivery_method": "BANK",
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
        """Initialize session with browser-like behavior that works with public API."""
        # Create a session with retry capability
        self.session = self._create_session_with_retry()
        
        # Set browser-like headers
        self.session.headers.update({
            "User-Agent": os.environ.get("WIREBARLEY_USER_AGENT", self.DEFAULT_USER_AGENT),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1"
        })
        
        # Step 1: Visit the homepage to get cookies
        try:
            homepage_url = self.BASE_URL
            self.logger.info(f"Visiting WireBarley homepage: {homepage_url}")
            homepage_response = self.session.get(homepage_url, timeout=10)
            
            if homepage_response.status_code != 200:
                self.logger.error(f"Failed to access homepage: {homepage_response.status_code}")
                return False
                
            # Step 2: Visit the homepage again with Referer header (critical step)
            self.session.headers.update({
                "Referer": homepage_url
            })
            
            second_response = self.session.get(homepage_url, timeout=10)
            if second_response.status_code != 200:
                self.logger.error(f"Failed on second homepage visit: {second_response.status_code}")
                return False
                
            self.session_timestamp = time.time()
            self.logger.info("WireBarley session initialized successfully")
            return True
                
        except requests.RequestException as e:
            self.logger.error(f"Error initializing session: {str(e)}")
            return False
    
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
        """Get exchange rate information for a specific currency pair using the most reliable method."""
        try:
            # First ensure we have a valid session
            self._ensure_valid_session()
            
            # Determine country code for the send currency
            source_country = self.CURRENCY_TO_COUNTRY.get(send_currency, send_currency[:2])
            country_code = self.CURRENCY_TO_COUNTRY.get(receive_currency, receive_currency[:2])
            
            if not country_code:
                self.logger.info(f"Unable to determine country code for currency {receive_currency}")
                return self.standardize_response({
                    "success": False,
                    "error_message": f"Unsupported currency: {receive_currency}"
                })
            
            # Use public endpoint to get rates for all corridors in a single request
            public_url = f"{self.BASE_URL}/my/remittance/api/v1/exrate/{source_country}/{send_currency}"
            
            # Set API-specific headers - this is the key to making it work
            api_headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": self.BASE_URL + "/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Device-Type": "WEB",
                "Device-Model": "Safari",
                "Device-Version": "605.1.15",
                "Lang": "en",
                "Request-ID": str(uuid.uuid4()),
                "Request-Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            }
            
            self.logger.info(f"Fetching exchange rates from {public_url}")
            
            # Use the existing session with the API-specific headers
            self.session.headers.update(api_headers)
            response = self.session.get(public_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data") is not None and "exRates" in data["data"]:
                    # Find the matching rate data for our corridor
                    self.logger.info(f"Found {len(data['data']['exRates'])} exchange rates")
                    for rate_data in data["data"]["exRates"]:
                        if rate_data.get("currency") == receive_currency:
                            # Found our corridor - extract rate information
                            wb_rate = rate_data.get("wbRate", 0)
                            
                            # Get threshold-based rate if available
                            if "wbRateData" in rate_data:
                                threshold_rate = self._pick_threshold_rate(rate_data, send_amount)
                                if threshold_rate:
                                    wb_rate = threshold_rate
                            
                            # Calculate fee
                            fee = self._calculate_fee(rate_data, send_amount)
                            
                            # Calculate destination amount
                            destination_amount = send_amount * Decimal(str(wb_rate))
                            
                            self.logger.info(f"Rate found for {send_currency} to {receive_currency}: {wb_rate}")
                            
                            # Format the response in the expected aggregator format
                            raw_response = {
                                "success": True,
                                "source_amount": float(send_amount),
                                "source_currency": send_currency,
                                "destination_amount": float(destination_amount),
                                "destination_currency": receive_currency,
                                "exchange_rate": float(wb_rate),
                                "fee": float(fee) if fee is not None else 0.0,
                                "payment_method": "BANK",
                                "delivery_method": "BANK",
                                "delivery_time_minutes": 1440,  # 24 hours in minutes
                                "timestamp": str(datetime.now(timezone.utc).isoformat()),
                                "raw_data": {
                                    "provider": "wirebarley",
                                    "rate_data": rate_data
                                }
                            }
                            
                            # Return standardized response
                            return self.standardize_response(raw_response)
                    
                    # If we get here, we didn't find the currency
                    return self.standardize_response({
                        "success": False,
                        "error_message": f"Unsupported corridor: No exchange rate found for {send_currency} to {receive_currency}"
                    })
                else:
                    self.logger.error("API returned data in unexpected format")
                    # Fallback to authenticated API if public API fails
                    return self._try_authenticated_api(send_amount, send_currency, receive_currency, country_code)
            else:
                self.logger.error(f"Public API returned status {response.status_code}")
                # Fallback to authenticated API if public API fails
                return self._try_authenticated_api(send_amount, send_currency, receive_currency, country_code)
                
        except Exception as e:
            self.logger.error(f"Error in get_exchange_rate: {str(e)}")
            return self.standardize_response({
                "success": False,
                "error_message": f"Error retrieving exchange rate: {str(e)}"
            })
    
    def _try_authenticated_api(self, send_amount, send_currency, receive_currency, country_code):
        """Fallback to the authenticated API if the public API fails."""
        try:
            # Ensure we have valid authenticated session
            self._ensure_valid_session()
            
            # Use the authenticated API endpoint
            result = self._fetch_api_data(send_currency, country_code, send_amount)
            
            # The fetch_api_data method returns in a different format
            # We need to reformat it for standardized response
            if result.get("success"):
                # Extract needed values and create raw_response
                raw_response = {
                    "success": True,
                    "source_amount": float(send_amount),
                    "source_currency": send_currency,
                    "destination_amount": result.get("receive_amount", 0),
                    "destination_currency": receive_currency,
                    "exchange_rate": result.get("exchange_rate", 0),
                    "fee": result.get("fee", 0),
                    "payment_method": "BANK",
                    "delivery_method": "BANK",
                    "delivery_time_minutes": 1440,
                    "timestamp": str(datetime.now(timezone.utc).isoformat()),
                    "raw_data": result
                }
                
                return self.standardize_response(raw_response)
            else:
                return self.standardize_response(result)
        except Exception as e:
            self.logger.error(f"Error in authenticated API fallback: {str(e)}")
            return self.standardize_response({
                "success": False,
                "error_message": f"Error in authenticated fallback: {str(e)}"
            })
    
    def get_quote(
        self,
        amount: Optional[Decimal] = None,
        send_currency: str = "USD",
        receive_currency: str = None,
        send_country: str = None,
        receive_country: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get a quote with enhanced corridor validation and browser session."""
        try:
            # Map parameter names for backward compatibility
            source_currency = send_currency
            destination_currency = receive_currency
            
            # First handle common unsupported corridors explicitly
            if destination_currency == 'MXN':
                self.logger.info(f"WireBarley does not support {source_currency} to {destination_currency} corridor")
                return self.standardize_response({
                    "success": False,
                    "error_message": f"Unsupported corridor: WireBarley does not support {source_currency} to {destination_currency}"
                })
                
            # Validate the corridor using shared utils
            source_country = self.CURRENCY_TO_COUNTRY.get(source_currency, "US")
            dest_country = self.CURRENCY_TO_COUNTRY.get(destination_currency, "")
            
            if not dest_country:
                self.logger.info(f"Unable to determine country code for currency {destination_currency}")
                return self.standardize_response({
                    "success": False,
                    "error_message": f"Unsupported destination currency: {destination_currency}"
                })
                
            is_valid, validation_msg = validate_corridor(
                source_country=source_country,
                source_currency=source_currency,
                dest_country=dest_country,
                dest_currency=destination_currency
            )
            
            if not is_valid:
                return self.standardize_response({
                    "success": False,
                    "error_message": f"Unsupported corridor: {validation_msg}"
                })

            # Initialize browser-like session with custom headers
            self._ensure_valid_session()
            self.session.headers.update({
                "Origin": self.BASE_URL,
                "Referer": f"{self.BASE_URL}/send",
                "Sec-Fetch-User": "?1",
                "TE": "trailers"
            })

            if not amount:
                return self.standardize_response({
                    "success": False,
                    "error_message": "Amount is required"
                })
            
            try:
                # Convert to Decimal if needed
                if not isinstance(amount, Decimal):
                    amount = Decimal(str(amount))
                
                # Validate amount
                if amount < 0:
                    return self.standardize_response({
                        "success": False,
                        "error_message": "Amount must be positive"
                    })
                
                # Check for min/max amount limits
                if amount < self.MIN_SUPPORTED_AMOUNT:
                    return self.standardize_response({
                        "success": False,
                        "error_message": f"Amount {amount} is below minimum supported amount {self.MIN_SUPPORTED_AMOUNT}"
                    })
                    
                if amount > self.MAX_SUPPORTED_AMOUNT:
                    return self.standardize_response({
                        "success": False,
                        "error_message": f"Amount {amount} is above maximum supported amount {self.MAX_SUPPORTED_AMOUNT}"
                    })
                
                # Call get_exchange_rate for the actual implementation
                # get_exchange_rate already returns a standardized response
                return self.get_exchange_rate(
                    send_amount=amount,
                    send_currency=source_currency,
                    receive_currency=destination_currency,
                    **kwargs
                )
                
            except Exception as e:
                self.logger.error(f"Error in get_quote: {str(e)}")
                return self.standardize_response({
                    "success": False,
                    "error_message": f"Error in quote generation: {str(e)}"
                })
            
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                return self.standardize_response({
                    "success": False,
                    "error_message": "Unsupported currency pair for WireBarley"
                })
            raise
    
    def get_corridors(self, source_currency: str = "USD") -> Dict[str, Any]:
        """Get available corridors for a source currency."""
        # Initialize failure structure
        failure_response = {
            "success": False,
            "error_message": None,
            "provider_id": self.name
        }
        
        # Validate currency
        if source_currency not in self.CURRENCY_TO_COUNTRY:
            failure_response["error_message"] = f"Unsupported source currency: {source_currency}"
            return failure_response
        
        # Ensure session is valid
        self._ensure_valid_session()
        if not self.session:
            failure_response["error_message"] = "No valid session. Check WireBarley cookies or Selenium login."
            return failure_response
        
        try:
            # Try using our new browser-like approach to get available corridors
            source_country = self.CURRENCY_TO_COUNTRY.get(source_currency, source_currency[:2])
            
            # Use public endpoint to get rates for all corridors in a single request
            public_url = f"{self.BASE_URL}/my/remittance/api/v1/exrate/{source_country}/{source_currency}"
            
            # Set API-specific headers - same approach as get_exchange_rate
            api_headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": self.BASE_URL + "/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Device-Type": "WEB",
                "Device-Model": "Safari",
                "Device-Version": "605.1.15",
                "Lang": "en",
                "Request-ID": str(uuid.uuid4()),
                "Request-Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            }
            
            self.logger.info(f"Fetching available corridors from {public_url}")
            
            # Try to use cached data first
            cache_key = f"corridors_{source_currency}"
            if (
                cache_key in self._corridors_cache and
                cache_key in self._cache_timestamp and
                (time.time() - self._cache_timestamp[cache_key]) < self._cache_duration
            ):
                self.logger.info(f"Using cached corridors for {source_currency}")
                return self._corridors_cache[cache_key]
            
            # Use the existing session with the API-specific headers
            self.session.headers.update(api_headers)
            response = self.session.get(public_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("data") is not None and "exRates" in data["data"]:
                    ex_rates = data["data"]["exRates"]
                    self.logger.info(f"Found {len(ex_rates)} potential corridors")
                    
                    # Extract corridors from exchange rates
                    corridors = []
                    for rate_data in ex_rates:
                        if "currency" in rate_data and "country" in rate_data:
                            target_currency = rate_data["currency"]
                            country_code = rate_data["country"]
                            
                            # Find min/max amounts from fee information
                            min_amount = self.MIN_SUPPORTED_AMOUNT
                            max_amount = self.MAX_SUPPORTED_AMOUNT
                            
                            if "transferFees" in rate_data and rate_data["transferFees"]:
                                # Take the most permissive min/max across all fee structures
                                for fee_struct in rate_data["transferFees"]:
                                    if "min" in fee_struct and fee_struct["min"] is not None:
                                        min_struct = Decimal(str(fee_struct["min"]))
                                        if min_struct < min_amount:
                                            min_amount = min_struct
                                            
                                    if "max" in fee_struct and fee_struct["max"] is not None:
                                        max_struct = Decimal(str(fee_struct["max"]))
                                        if max_struct > max_amount:
                                            max_amount = max_struct
                            
                            corridors.append({
                                "source_currency": source_currency,
                                "target_currency": target_currency,
                                "source_country": source_country,
                                "target_country": country_code,
                                "min_amount": float(min_amount),
                                "max_amount": float(max_amount)
                            })
                    
                    # Create success response
                    result = {
                        "success": True,
                        "provider_id": self.name,
                        "corridors": corridors
                    }
                    
                    # Cache the result
                    self._corridors_cache[cache_key] = result
                    self._cache_timestamp[cache_key] = time.time()
                    
                    return result
                else:
                    self.logger.error("API returned data in unexpected format for corridors")
                    # Fall back to old method
                    return self._try_authenticated_corridors_api(source_currency)
            else:
                self.logger.error(f"Public API returned status {response.status_code} for corridors")
                # Fall back to old method
                return self._try_authenticated_corridors_api(source_currency)
                
        except Exception as e:
            self.logger.error(f"Error in get_corridors: {str(e)}")
            failure_response["error_message"] = f"Error getting corridors: {str(e)}"
            return failure_response
    
    def _try_authenticated_corridors_api(self, source_currency):
        """Use the authenticated API to get corridors as a fallback."""
        failure_response = {
            "success": False,
            "error_message": None,
            "provider_id": self.name
        }
        
        try:
            # Get source country code
            source_country_code = self.CURRENCY_TO_COUNTRY[source_currency]
            
            # Build request
            headers = {
                "Request-Id": str(uuid.uuid4()),
                "Content-Type": "application/json"
            }
            
            # Get data from API
            url = f"{self.API_BASE_URL}/api/v1/remittance/getRemittanceList?sendCurrency={source_currency}&sendCountry={source_country_code}"
            response = self.session.get(url, headers=headers, timeout=15)
            
            # Parse response
            if response.status_code != 200:
                failure_response["error_message"] = f"API error: HTTP {response.status_code}"
                return failure_response
                
            data = response.json()
            
            # Handle API-level errors
            if data.get("status") != "success":
                error_msg = data.get("message", "Unknown API error")
                failure_response["error_message"] = f"API error: {error_msg}"
                return failure_response
            
            # Extract corridor information
            corridors = []
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
                            "source_country": source_country_code,
                            "target_country": country_code,
                            "min_amount": float(min_amount),
                            "max_amount": float(max_amount)
                        })
            
            # Create response
            result = {
                "success": True,
                "provider_id": self.name,
                "corridors": corridors
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in authenticated corridors API: {str(e)}")
            failure_response["error_message"] = f"Error getting corridors: {str(e)}"
            return failure_response
    
    def close(self):
        """Close and clean up resources."""
        if self.session:
            try:
                self.session.close()
            except:
                pass
            
        self.session = None
        self.session_timestamp = None 