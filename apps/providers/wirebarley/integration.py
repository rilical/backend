import logging
import requests
from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import traceback

from apps.providers.base.provider import RemittanceProvider

"""
WireBarley API Integration Module

This module provides a complete integration with the WireBarley API for remittance services.
It supports multiple currency corridors and handles API failures gracefully.

IMPORTANT:
- This implementation simulates browser requests to the WireBarley API
- API calls require specific browser-like headers and cookies from an active session
- Without valid session cookies, API calls will fail with a 400 status code
- For testing with real data, you'll need to extract cookies from a browser session with WireBarley

HEADERS REQUIRED:
- All standard browser headers (User-Agent, Accept, etc.)
- Device-Type, Device-Model, Device-Version
- Request-ID (UUID for each request)
- Request-Time (formatted timestamp)
- Lang (language preference)

COOKIES REQUIRED:
- Session cookies from an authenticated browser session (_fbp, _ga, etc.)
- These cookies establish your identity with the WireBarley service

Last Updated: March 3, 2025
"""

logger = logging.getLogger(__name__)

class WireBarleyProvider(RemittanceProvider):
    """
    WireBarley integration for retrieving fees, exchange rates, and quotes.
    
    Authentication can be done in two ways:
    1. Direct cookie injection (preferred) - provide cookies from an authenticated browser session
    2. Selenium automation (fallback) - automate browser login process
    
    For direct cookie injection, set the following environment variables:
    - WIREBARLEY_COOKIES: JSON string of cookie name/value pairs
    - WIREBARLEY_USER_AGENT: Browser User-Agent to use (optional)
    
    For Selenium automation, set:
    - WIREBARLEY_EMAIL: Login email
    - WIREBARLEY_PASSWORD: Login password
    
    Example WIREBARLEY_COOKIES format:
    {
        "_ga": "GA1.2.123456789.1234567890",
        "_fbp": "fb.1.1234567890.123456789",
        ...
    }
    """
    
    BASE_URL = "https://www.wirebarley.com"
    
    # Currency to country code mapping
    CURRENCY_TO_COUNTRY = {
        "USD": "US",  # United States Dollar
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
    
    def __init__(self, config=None):
        """Initialize the WireBarley provider."""
        super().__init__(name="wirebarley", base_url=self.BASE_URL)
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.browser_data = None
        self.session_timestamp = None
        self.session_valid_duration = 3600  # 1 hour in seconds
        
        # Cache for corridor data
        self._corridors_cache = {}
        self._cache_timestamp = {}
        self._cache_duration = 3600
        self._current_source_currency = "USD"
        
        # Initialize session
        self._initialize_session()
    
    def _get_browser_cookies(self):
        """Get cookies either from environment variable or via Selenium."""
        # First try to get cookies from environment variable
        cookies_str = os.getenv('WIREBARLEY_COOKIES')
        if cookies_str:
            try:
                cookies_dict = json.loads(cookies_str)
                self.logger.info("Using cookies from environment variable")
                return cookies_dict
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse WIREBARLEY_COOKIES: {e}")
        
        # Fallback to Selenium automation
        self.logger.info("No cookies found in environment, falling back to Selenium")
        return self._get_selenium_cookies()
    
    def _get_selenium_cookies(self):
        """Create a browser session and get authentication cookies using Selenium."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-agent={os.getenv("WIREBARLEY_USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")}')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            wait = WebDriverWait(driver, 20)
            
            # Go directly to the login page
            driver.get('https://my.wirebarley.com/login')
            time.sleep(5)  # Wait for page to load
            
            try:
                # Try different selectors for login form elements
                email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]')))
                password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]')))
                
                # Fill in credentials from environment variables
                email = os.getenv('WIREBARLEY_EMAIL')
                password = os.getenv('WIREBARLEY_PASSWORD')
                
                if not email or not password:
                    raise ValueError("WIREBARLEY_EMAIL and WIREBARLEY_PASSWORD environment variables are required for Selenium automation")
                
                email_field.send_keys(email)
                password_field.send_keys(password)
                
                # Try to find and click the login button
                login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]')))
                login_button.click()
                
                # Wait for login to complete
                time.sleep(5)
                
                # Navigate to remittance page to get additional cookies
                driver.get('https://my.wirebarley.com/remittance')
                time.sleep(5)
                
                # Get all cookies
                cookies = driver.get_cookies()
                
                # Convert cookies to dictionary format
                cookie_dict = {}
                for cookie in cookies:
                    cookie_dict[cookie['name']] = cookie['value']
                
                return cookie_dict
                
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.warning(f"Login attempt failed: {str(e)}\nStacktrace:\n{traceback.format_exc()}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Browser automation failed: {str(e)}\nStacktrace:\n{traceback.format_exc()}")
            return {}
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _initialize_session(self):
        """Initialize a new session with proper headers and cookies."""
        try:
            # Get browser session data
            browser_data = self._get_browser_cookies()
            if not browser_data:
                raise Exception("Failed to get browser session data")

            # Set up session with headers
            self.session = requests.Session()
            
            # Use custom User-Agent if provided
            user_agent = os.getenv('WIREBARLEY_USER_AGENT', 
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')
            
            self.session.headers.update({
                'User-Agent': user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://my.wirebarley.com',
                'Referer': 'https://my.wirebarley.com/'
            })

            # Set cookies from browser session
            for name, value in browser_data.items():
                self.session.cookies.set(name, value, domain='.wirebarley.com')
            
            # Update session timestamp
            self.session_timestamp = time.time()
            
            # Validate session
            self._validate_session()
            
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize session: {str(e)}")
            return False
    
    def _init_api_session(self):
        """Initialize the API session with proper authentication."""
        try:
            # Step 1: Visit main page to get CSRF token
            response = self.session.get(
                f"{self.BASE_URL}/en",
                timeout=15
            )
            response.raise_for_status()
            
            # Extract CSRF token from response if available
            csrf_token = None
            for cookie in response.cookies:
                if cookie.name == "XSRF-TOKEN":
                    csrf_token = cookie.value
                    break
            
            if csrf_token:
                self.session.headers["X-XSRF-TOKEN"] = csrf_token
            
            # Step 2: Initialize remittance session
            init_data = {
                "deviceType": "WEB",
                "lang": "en",
                "region": "US",
                "deviceId": self.device_id,
                "sessionId": self.session_id,
                "timestamp": str(int(time.time() * 1000))
            }
            
            init_response = self.session.post(
                f"{self.BASE_URL}/my/remittance/api/v1/init",
                json=init_data,
                timeout=15
            )
            init_response.raise_for_status()
            
            # Step 3: Get user info if available
            if os.getenv("WIREBARLEY_TOKEN"):
                user_response = self.session.get(
                    f"{self.BASE_URL}/my/remittance/api/v1/user/info",
                    timeout=15
                )
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    if user_data.get("status") == 0:
                        logger.debug("Successfully retrieved user info")
            
            # Validate session with test API call
            self._validate_session()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API session initialization failed: {e}")
            raise
    
    def _validate_session(self):
        """Validate the current session with a test API call."""
        try:
            headers = {
                "Request-Id": str(uuid.uuid4()),
                "Request-Time": str(int(time.time() * 1000))
            }
            
            response = self.session.get(
                f"{self.BASE_URL}/my/remittance/api/v1/exrate/US/USD",
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") == 400:
                raise Exception(f"Session validation failed: {data.get('messageKey')}")
                
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            raise
    
    def _ensure_valid_session(self):
        """Ensure we have a valid session, reinitialize if necessary."""
        current_time = time.time()
        
        # Check if session needs renewal
        if (self.session is None or 
            self.session_timestamp is None or
            (current_time - self.session_timestamp) > self.session_valid_duration):
            logger.debug("Session expired or invalid, reinitializing...")
            self._initialize_session()
    
    def fetch_raw_data(self, source_currency: str, target_currency: str, amount: Decimal) -> Dict[str, Any]:
        """Fetch exchange rate and fee data with proper error handling and retries."""
        max_retries = 3
        base_delay = 1
        
        country_code = self.CURRENCY_TO_COUNTRY.get(source_currency)
        if not country_code:
            logger.warning(f"Unsupported source currency: {source_currency}")
            return None
        
        api_endpoint = f"{self.BASE_URL}/my/remittance/api/v1/exrate/{country_code}/{source_currency}"
        
        for attempt in range(max_retries):
            try:
                self._ensure_valid_session()
                
                headers = {
                    "Request-Id": str(uuid.uuid4()),
                    "Request-Time": str(int(time.time() * 1000))
                }
                
                response = self.session.get(
                    api_endpoint,
                    headers=headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == 0 and data.get("data"):
                        return data
                    elif data.get("status") == 400:
                        if "SESSION_EXPIRED" in str(data.get("messageKey", "")):
                            logger.warning("Session expired, reinitializing...")
                            self._initialize_session()
                            continue
                        else:
                            logger.error(f"API error: {data.get('messageKey')}")
                    
                elif response.status_code in (401, 403):
                    logger.warning("Authentication error, reinitializing session...")
                    self._initialize_session()
                    continue
                    
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", base_delay * (2 ** attempt)))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                    
                else:
                    logger.error(f"Unexpected status code: {response.status_code}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.debug(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            
        logger.error(f"Failed to fetch data after {max_retries} attempts")
        return None
    
    def parse_exrates(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse the "exRates" array from the raw JSON to unify corridor info:
        - baseRate / wbRate
        - Payment fees / Transfer fees
        - thresholds, etc.
        
        Return a list of dictionaries; each item represents a corridor.
        """
        results = []
        
        # Check if we got a proper response
        if data.get("status") != 0 or data.get("data") is None:
            logger.warning(f"WireBarley API returned non-success status: {data.get('status')}")
            return results
            
        exrates = data.get("data", {}).get("exRates", [])
        for ex in exrates:
            # Basic fields
            country = ex.get("country")
            currency = ex.get("currency")
            wb_rate = ex.get("wbRate")       # The "WireBarley" rate
            base_rate = ex.get("baseRate")   # Possibly the standard/base rate
            status = ex.get("status")
            
            # Parse the fee arrays, if needed
            payment_fees = ex.get("paymentFees", [])
            transfer_fees = ex.get("transferFees", [])
            # If you want to unify them into one list, or store them separately, do so:
            unified_payment_fees = self._parse_fee_array(payment_fees)
            unified_transfer_fees = self._parse_fee_array(transfer_fees)
            
            # Optional advanced usage: parse the tiered rate data
            wb_rate_data = ex.get("wbRateData", {})
            # This can hold multiple threshold-based rates, e.g.:
            # {
            #   "threshold": 200, "wbRate": 57.1040667,
            #   "threshold1": 300, "wbRate1": 57.1330388,
            #   ...
            # }
            # You can parse each threshold pair if your system needs it:
            threshold_rates = self._parse_threshold_rates(wb_rate_data)
            
            corridor_info = {
                "country_code": country,   # e.g. "PH", "AU", ...
                "currency": currency,      # e.g. "PHP", "AUD", ...
                "wirebarley_rate": float(wb_rate) if wb_rate else None,
                "base_rate": float(base_rate) if base_rate else None,
                "status": status,          # "ACTIVE", etc.
                "payment_fees": unified_payment_fees,   # array/list of fee tiers
                "transfer_fees": unified_transfer_fees, # array/list of fee tiers
                "rate_thresholds": threshold_rates,      # list of threshold-based rates
            }
            
            results.append(corridor_info)
        
        return results
    
    def _parse_fee_array(self, fee_array: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Example helper method: parse each fee object from "paymentFees" or "transferFees"
        into a structured list. Each item might define multiple thresholds or feeX fields.
        
        Input example item from wirebarley:
        {
          "useDiscountFee": false,
          "min": 10,
          "fee1": 4.99,
          "discountFee1": null,
          "threshold1": 500.01,
          "fee2": 5.99,
          ...
          "max": 2999,
          "option": "CREDIT_DEBIT_CARD",
          "country": "AU",
          "dest": "AUD"
        }
        
        We'll unify it into your own structure:
        [
            {
                "option": "CREDIT_DEBIT_CARD",
                "min_send": 10,
                "max_send": 2999,
                "tiers": [
                    {
                      "threshold": 500.01,
                      "fee": 4.99
                    },
                    {
                      "threshold": 600.01,
                      "fee": 5.99
                    },
                    ...
                ]
            },
            ...
        ]
        """
        results = []
        for fee_item in fee_array:
            option = fee_item.get("option")  # e.g. "CREDIT_DEBIT_CARD" or "ACH_EXPRESS"
            country = fee_item.get("country")
            dest_currency = fee_item.get("dest")
            min_send = fee_item.get("min")
            max_send = fee_item.get("max")
            use_discount = fee_item.get("useDiscountFee")  # bool
            
            # Build tier list from fee1..fee10 if present
            # Typically, you see fields: fee1..fee10, threshold1..threshold10
            # We'll loop up to 10 to see if they're present:
            fee_tiers = []
            for i in range(1, 11):
                fee_key = f"fee{i}"
                thr_key = f"threshold{i}"
                fee_val = fee_item.get(fee_key)
                thr_val = fee_item.get(thr_key)
                if fee_val is not None:
                    # We have a tier
                    fee_tiers.append({
                        "threshold": float(thr_val) if thr_val is not None else None,
                        "fee": float(fee_val),
                    })
            
            results.append({
                "option": option,
                "country": country,
                "dest_currency": dest_currency,
                "min_send": min_send,
                "max_send": max_send,
                "use_discount_fee": use_discount,
                "fee_tiers": fee_tiers,
            })
        return results
    
    def _parse_threshold_rates(self, wb_rate_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse the threshold-based rates from wbRateData.
        
        Example input:
        {
            "threshold": 500,
            "wbRate": 32.0332162,
            "threshold1": 1000,
            "wbRate1": 32.0494109,
            ...
        }
        
        Returns:
        [
            {"threshold": 500.0, "rate": 32.0332162},
            {"threshold": 1000.0, "rate": 32.0494109},
            ...
        ]
        """
        thresholds = []
        
        # First handle the base threshold/rate pair
        base_threshold = wb_rate_data.get("threshold")
        base_rate = wb_rate_data.get("wbRate")
        if base_threshold is not None or base_rate is not None:
            thresholds.append({
                "threshold": float(base_threshold) if base_threshold is not None else None,
                "rate": float(base_rate) if base_rate is not None else None
            })
        
        # Then handle threshold1..threshold9 pairs
        for i in range(1, 10):
            thr_key = f"threshold{i}"
            rate_key = f"wbRate{i}"
            
            threshold = wb_rate_data.get(thr_key)
            rate = wb_rate_data.get(rate_key)
            
            if threshold is not None or rate is not None:
                thresholds.append({
                    "threshold": float(threshold) if threshold is not None else None,
                    "rate": float(rate) if rate is not None else None
                })
        
        # Filter out entries where both threshold and rate are None
        thresholds = [t for t in thresholds if not (t["threshold"] is None and t["rate"] is None)]
        
        # Sort by threshold value (None values go last)
        thresholds.sort(key=lambda x: float('inf') if x["threshold"] is None else x["threshold"])
        
        return thresholds
    
    def get_min_amount(self, ex_rate: Dict[str, Any]) -> float:
        """
        Get the minimum supported amount for a corridor.
        
        Args:
            ex_rate: The exchange rate data for a corridor
            
        Returns:
            The minimum amount supported for this corridor, defaulting to 10.0
        """
        # Look through payment fees for minimum amounts
        payment_fees = ex_rate.get("payment_fees", [])
        if payment_fees:
            min_amounts = [fee.get("min_send", 10.0) for fee in payment_fees if fee.get("min_send") is not None]
            if min_amounts:
                return min(min_amounts)
        
        # Default minimum if not found
        return 10.0
    
    def get_max_amount(self, ex_rate: Dict[str, Any]) -> float:
        """
        Get the maximum supported amount for a corridor.
        
        Args:
            ex_rate: The exchange rate data for a corridor
            
        Returns:
            The maximum amount supported for this corridor, defaulting to 3000.0
        """
        # Look through payment fees for maximum amounts
        payment_fees = ex_rate.get("payment_fees", [])
        if payment_fees:
            max_amounts = [fee.get("max_send", 3000.0) for fee in payment_fees if fee.get("max_send") is not None]
            if max_amounts:
                return max(max_amounts)
        
        # Default maximum if not found
        return 3000.0
    
    def get_corridors(self, source_currency: str = "USD") -> Dict[str, Any]:
        """
        Get available corridors for the given source currency.
        Returns a dictionary with success status and corridor details.
        """
        logger.debug(f"Fetching corridors for {source_currency}")
        
        # Use a default amount for corridor lookup
        default_amount = Decimal("100")
        
        # Fetch raw data with default target currency (doesn't affect corridor list)
        data = self.fetch_raw_data(source_currency, "USD", default_amount)
        if not data or "data" not in data or "exRates" not in data["data"]:
            logger.error(f"Failed to fetch corridors for {source_currency}")
            return {
                "success": False,
                "error": "Failed to fetch corridor data"
            }
        
        # Extract corridor information from exchange rates
        corridors = []
        for rate in data["data"]["exRates"]:
            corridor = {
                "source_currency": source_currency,
                "target_currency": rate.get("currency"),
                "country_code": rate.get("countryCode"),
                "min_amount": Decimal(str(rate.get("minAmount", "10"))),
                "max_amount": Decimal(str(rate.get("maxAmount", "10000"))),
                "exchange_rate": Decimal(str(rate.get("exchangeRate", "0"))),
                "fee": Decimal(str(rate.get("fee", "0")))
            }
            corridors.append(corridor)
        
        return {
            "success": True,
            "corridors": corridors
        }
    
    def get_exchange_rate(self, send_amount: Decimal, send_currency: str, receive_country: str) -> Dict[str, Any]:
        """
        Get exchange rate and fees for a specific corridor and amount.
        
        Args:
            send_amount: Amount to send
            send_currency: Source currency code (USD, EUR, etc.)
            receive_country: ISO country code for destination (PH, IN, etc.)
            
        Returns:
            dict with success status, rate, fee, and other details
        """
        try:
            # Ensure valid session
            self._ensure_valid_session()
            
            # Check if source currency is supported
            if send_currency not in self.CURRENCY_TO_COUNTRY:
                logger.warning(f"Unsupported source currency: {send_currency}")
                return {
                    "success": False, 
                    "error": f"Source currency {send_currency} not supported"
                }
                
            # Validate amount
            if send_amount < Decimal("10") or send_amount > Decimal("10000"):
                logger.warning(f"Amount {send_amount} outside of supported range (10-10000)")
                return {
                    "success": False,
                    "error": f"Amount {send_amount} outside of supported range (10-10000)"
                }
            
            # Fetch raw data from API
            raw_data = self.fetch_raw_data(send_currency, receive_country, send_amount)
            if not raw_data or "data" not in raw_data:
                logger.error("Failed to fetch exchange rate data")
                return {
                    "success": False,
                    "error": "Failed to fetch exchange rate data"
                }
            
            # Find matching exchange rate for the receive country
            ex_rates = raw_data.get("data", {}).get("exRates", [])
            matching_rate = None
            for rate in ex_rates:
                if rate.get("country") == receive_country:
                    matching_rate = rate
                    break
            
            if not matching_rate:
                logger.error(f"No exchange rate found for {receive_country}")
                return {
                    "success": False,
                    "error": f"No exchange rate found for {receive_country}"
                }
            
            # Get the appropriate rate based on amount thresholds
            rate_value = self._get_threshold_rate(matching_rate, send_amount)
            if rate_value is None:
                logger.error("Failed to determine exchange rate")
                return {
                    "success": False,
                    "error": "Failed to determine exchange rate"
                }
            
            # Calculate fee
            fee = self._calculate_fee(send_amount, send_currency, matching_rate)
            
            # Calculate target amount
            target_amount = float(send_amount) * float(rate_value)
            
            return {
                "success": True,
                "source_amount": float(send_amount),
                "source_currency": send_currency,
                "target_amount": target_amount,
                "target_currency": matching_rate.get("currency"),
                "fee": fee,
                "rate": float(rate_value),
                "fee_currency": send_currency,
                "rate_source": "wirebarley",
                "rate_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting exchange rate: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_threshold_rate(self, rate_data: Dict[str, Any], amount: Decimal) -> Optional[float]:
        """
        Get the appropriate exchange rate based on amount thresholds.
        
        Args:
            rate_data: Exchange rate data from API
            amount: Send amount
            
        Returns:
            The appropriate exchange rate or None if not found
        """
        try:
            # First check if there are threshold-based rates
            wb_rate_data = rate_data.get("wbRateData", {})
            if wb_rate_data:
                # Sort thresholds in ascending order
                thresholds = []
                for i in range(1, 6):  # Usually up to 5 thresholds
                    thr_key = f"threshold{i}" if i > 1 else "threshold"
                    rate_key = f"wbRate{i}" if i > 1 else "wbRate"
                    
                    if thr_key in wb_rate_data and rate_key in wb_rate_data:
                        thresholds.append({
                            "threshold": float(wb_rate_data[thr_key]),
                            "rate": float(wb_rate_data[rate_key])
                        })
                
                thresholds.sort(key=lambda x: x["threshold"])
                
                # Find the appropriate rate based on amount
                for t in thresholds:
                    if float(amount) <= t["threshold"]:
                        return t["rate"]
                
                # If amount is above all thresholds, use the last rate
                if thresholds:
                    return thresholds[-1]["rate"]
            
            # If no threshold rates found, use the basic rate
            return float(rate_data.get("wbRate", rate_data.get("baseRate")))
            
        except Exception as e:
            logger.error(f"Error determining threshold rate: {e}")
            return None
    
    def _calculate_fee(self, amount: Decimal, currency: str, rate_data: Dict[str, Any]) -> float:
        """
        Calculate the transfer fee based on amount and rate data.
        
        The fee structure can be complex with multiple tiers and options:
        1. Each payment method (e.g. CREDIT_CARD, BANK_TRANSFER) has its own fee structure
        2. Within each payment method, fees are tiered based on amount thresholds
        3. Some tiers may have discount fees available
        
        Args:
            amount: Send amount
            currency: Source currency
            rate_data: Exchange rate data containing fee information
            
        Returns:
            The calculated fee amount (defaults to 4.99 if no matching fee found)
        """
        try:
            # Default fee if none found
            default_fee = 4.99
            
            # Get both payment and transfer fees
            payment_fees = rate_data.get("paymentFees", [])
            transfer_fees = rate_data.get("transferFees", [])
            
            if not payment_fees and not transfer_fees:
                logger.debug(f"No fee structures found for {currency}, using default")
                return default_fee
            
            # Try payment fees first
            for fee_info in payment_fees:
                min_amount = float(fee_info.get("min", 0))
                max_amount = float(fee_info.get("max", float("inf")))
                
                if min_amount <= float(amount) <= max_amount:
                    # Check if discount fees are available
                    use_discount = fee_info.get("useDiscountFee", False)
                    
                    # Get fee tiers
                    tiers = []
                    for i in range(1, 11):
                        threshold_key = f"threshold{i}"
                        fee_key = f"fee{i}"
                        discount_key = f"discountFee{i}"
                        
                        threshold = fee_info.get(threshold_key)
                        fee = fee_info.get(fee_key)
                        discount_fee = fee_info.get(discount_key) if use_discount else None
                        
                        if fee is not None:
                            tiers.append({
                                "threshold": float(threshold) if threshold is not None else float("inf"),
                                "fee": float(discount_fee if use_discount and discount_fee is not None else fee)
                            })
                    
                    # Sort tiers by threshold
                    tiers.sort(key=lambda x: x["threshold"])
                    
                    # Find appropriate fee based on amount
                    for tier in tiers:
                        if float(amount) <= tier["threshold"]:
                            return tier["fee"]
                    
                    # If amount is above all thresholds, use the last fee
                    if tiers:
                        return tiers[-1]["fee"]
                    
                    # If no tiers found, use the base fee
                    base_fee = fee_info.get("fee")
                    if base_fee is not None:
                        return float(base_fee)
            
            # If no matching payment fee found, try transfer fees
            for fee_info in transfer_fees:
                min_amount = float(fee_info.get("min", 0))
                max_amount = float(fee_info.get("max", float("inf")))
                
                if min_amount <= float(amount) <= max_amount:
                    fee = fee_info.get("fee")
                    if fee is not None:
                        return float(fee)
            
            # No matching fee tier found in either structure
            logger.debug(f"No matching fee tier found for {amount} {currency}, using default")
            return default_fee
            
        except Exception as e:
            logger.error(f"Error calculating fee: {e}")
            return default_fee
    
    def get_quote(self, send_amount, send_currency, receive_currency):
        """
        Get a quote for a money transfer.
        
        Args:
            send_amount (float): The amount to send
            send_currency (str): The currency code of the sending amount (e.g., "USD")
            receive_currency (str): The currency code for the receiving amount (e.g., "PHP")
            
        Returns:
            dict: A dictionary containing the quote details or error information
        """
        # Get the country code from the target currency
        country_code = self._get_country_from_currency(receive_currency)
        if not country_code:
            return {
                "success": False,
                "error": f"Unsupported target currency: {receive_currency}",
                "send_amount": send_amount,
                "send_currency": send_currency,
                "target_currency": receive_currency,
                "provider": "wirebarley"
            }
        
        # Get the exchange rate
        exchange_rate_response = self.get_exchange_rate(send_amount, send_currency, country_code)
        
        # Check if the exchange rate call was successful
        if exchange_rate_response.get("success", False):
            # Format the response
            return {
                "success": True,
                "send_amount": exchange_rate_response["source_amount"],
                "send_currency": exchange_rate_response["source_currency"],
                "receive_amount": exchange_rate_response["target_amount"],
                "receive_currency": exchange_rate_response["target_currency"],
                "fee": exchange_rate_response["fee"],
                "rate": exchange_rate_response["rate"],
                "provider": "wirebarley",
                "rate_source": exchange_rate_response.get("rate_source", "wirebarley"),
                "rate_timestamp": exchange_rate_response.get("rate_timestamp", datetime.now().isoformat())
            }
        else:
            # Return the error from the exchange rate call
            error_message = exchange_rate_response.get("error", "Unknown error")
            
            # Check if it's an authentication error
            if "API authentication required" in error_message:
                error_message = "API authentication required. Please provide valid API credentials."
            
            return {
                "success": False,
                "error": error_message,
                "send_amount": send_amount,
                "send_currency": send_currency,
                "target_currency": receive_currency,
                "provider": "wirebarley"
            }
    
    def _get_country_from_currency(self, currency: str) -> Optional[str]:
        """
        Map a currency code to its corresponding country code.
        
        Args:
            currency: Currency code (e.g., 'PHP')
            
        Returns:
            Country code (e.g., 'PH') or None if not found
        """
        # Use the class-level mapping instead of defining a duplicate mapping here
        return self.CURRENCY_TO_COUNTRY.get(currency)
    
    def get_corridor_details(self, source_currency: str, country_code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific corridor.
        
        Args:
            source_currency: Source currency code (e.g., 'USD')
            country_code: Destination country code (e.g., 'PH')
            
        Returns:
            Dictionary with corridor details or None if not found
        """
        corridors_response = self.get_corridors(source_currency)
        if not corridors_response:
            logger.error(f"Failed to fetch corridors for {source_currency}")
            return None
            
        # Fetch raw data to get full exRates information
        raw_data = self.fetch_raw_data(source_currency, "USD", Decimal("100"))
        if raw_data.get("status") != 0 or "data" not in raw_data or "exRates" not in raw_data["data"]:
            logger.error(f"Invalid API response for {source_currency}")
            return None
            
        # Find the matching corridor
        for ex_rate in raw_data["data"]["exRates"]:
            if ex_rate.get("countryCode") == country_code:
                return ex_rate
                
        logger.warning(f"No corridor found for {source_currency} to {country_code}")
        return None

    def _update_exchange_rate_cache(self):
        """Regular updates to exchange rate cache."""
        # Implementation of _update_exchange_rate_cache method
        pass 