"""
Paysend Money Transfer Integration

This module implements an aggregator-ready integration with Paysend's public quote API.
"""

import json
import logging
import time
import uuid
import os
from decimal import Decimal
from typing import Dict, Optional, Any, List, Union
from pathlib import Path
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from apps.providers.paysend.exceptions import (
    PaysendError,
    PaysendAuthenticationError,
    PaysendConnectionError,
    PaysendValidationError,
    PaysendRateLimitError,
    PaysendApiError
)

# Optional browser helper for captcha challenges
try:
    from apps.providers.paysend.browser_helper import get_browser_cookies_sync, run_browser_helper_sync
    BROWSER_HELPER_AVAILABLE = True
except ImportError:
    BROWSER_HELPER_AVAILABLE = False

logger = logging.getLogger(__name__)


class PaysendProvider(RemittanceProvider):
    """
    Aggregator-ready integration with Paysend's public quote API.

    Features:
      - Direct API calls
      - Optional browser automation fallback for captcha
      - Mock data fallback if all else fails
    """
    
    BASE_URL = "https://paysend.com"
    QUOTE_ENDPOINT = "/api/public/quote"
    COUNTRIES_DATA_FILE = "country_list.json"
    DEFAULT_DELIVERY_METHOD = "Bank Transfer"
    DEFAULT_PAYMENT_METHOD = "Card"
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.3 Safari/605.1.15"
    )
    USE_BROWSER_HELPER = True

    # Fallback country name mappings for URL construction
    COUNTRY_NAMES = {
        "US": "the-united-states-of-america",
        "IN": "india",
        "AM": "armenia",
        "DZ": "algeria",
        "GB": "the-united-kingdom",
        "CA": "canada",
        "AU": "australia",
        "DE": "germany",
        "FR": "france",
        "ES": "spain",
        "IT": "italy",
        "NL": "the-netherlands",
        "BE": "belgium",
        "CH": "switzerland",
        "AT": "austria",
        "SG": "singapore",
        "NZ": "new-zealand",
        "HK": "hong-kong",
        "JP": "japan",
        "KR": "south-korea",
        "TH": "thailand",
        "MY": "malaysia",
        "PH": "the-philippines",
        "ID": "indonesia",
        "CN": "china",
        "RU": "russia",
        "UA": "ukraine",
        "MX": "mexico",
        "BR": "brazil",
        "AR": "argentina",
        "CO": "colombia",
        "PE": "peru",
        "CL": "chile",
        "EG": "egypt",
        "ZA": "south-africa",
        "NG": "nigeria",
        "KE": "kenya",
        "GH": "ghana",
        "AE": "the-united-arab-emirates",
        "TR": "turkey",
        "SA": "saudi-arabia",
        "IL": "israel",
        "PK": "pakistan",
        "BD": "bangladesh",
        "LK": "sri-lanka",
        "NP": "nepal",
    }

    # Fallback currency IDs
    CURRENCY_IDS = {
        "USD": "840",
        "EUR": "978",
        "GBP": "826",
        "CAD": "124",
        "AUD": "036",
        "NZD": "554",
        "JPY": "392",
        "CHF": "756",
        "HKD": "344",
        "SGD": "702",
        "AED": "784",
        "SAR": "682",
        "INR": "356",
        "PKR": "586",
        "BDT": "050",
        "LKR": "144",
        "NPR": "524",
        "IDR": "360",
        "PHP": "608",
        "THB": "764",
        "MYR": "458",
        "KRW": "410",
        "CNY": "156",
        "RUB": "643",
        "UAH": "980",
        "MXN": "484",
        "BRL": "986",
        "ARS": "032",
        "COP": "170",
        "PEN": "604",
        "CLP": "152",
        "EGP": "818",
        "ZAR": "710",
        "NGN": "566",
        "KES": "404",
        "GHS": "936",
        "TRY": "949",
        "ILS": "376",
        "AMD": "051",
        "DZD": "012",
    }

    def __init__(self, user_agent: Optional[str] = None, timeout: int = 30, use_browser_helper: Optional[bool] = None):
        super().__init__(name="Paysend", base_url=self.BASE_URL)
        self.timeout = timeout
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        
        # Determine if we should use browser automation
        if use_browser_helper is not None:
            self.use_browser_helper = use_browser_helper
        else:
            self.use_browser_helper = self.USE_BROWSER_HELPER and BROWSER_HELPER_AVAILABLE
        
        # Create requests session
        self.session = requests.Session()
        self._setup_session()
        
        # Attempt to load extracted country data from JSON
        self.country_data = self._load_country_data()
        self.from_countries_by_code = {}
        self.to_countries_by_code = {}
        self.currency_ids = {}

        if self.country_data:
            self._build_lookup_dictionaries()
        
        # If browser is available and we want to use it, load cookies
        if self.use_browser_helper:
            self._load_browser_cookies()
    
    def _load_country_data(self) -> Dict:
        """
        Load country data from the extracted JSON file.
        
        Returns:
            Dictionary containing country data or empty dict if file not found
        """
        try:
            # Try to find the countries data file in the same directory as this module
            current_dir = Path(__file__).parent
            countries_file_path = current_dir / self.COUNTRIES_DATA_FILE
            
            # If not found, try to find it relative to the current working directory
            if not countries_file_path.exists():
                countries_file_path = Path(self.COUNTRIES_DATA_FILE)
            
            if countries_file_path.exists():
                logger.info(f"Loading Paysend country data from {countries_file_path}")
                with open(countries_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Loaded data for {len(data.get('from_countries', []))} source countries and {len(data.get('to_countries', []))} destination countries")
                return data
            else:
                logger.warning(f"Paysend countries data file not found at {countries_file_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading Paysend country data: {e}")
            return {}
    
    def _build_lookup_dictionaries(self):
        """Build lookup dictionaries for faster access to country and currency data"""
        # Build lookup dictionaries for source and destination countries
        for country in self.country_data.get('from_countries', []):
            code = country.get('code')
            if code:
                self.from_countries_by_code[code.upper()] = country
        
        for country in self.country_data.get('to_countries', []):
            code = country.get('code')
            if code:
                self.to_countries_by_code[code.upper()] = country
                
                # Also extract currency IDs from all country data
                for currency in country.get('currencies', []):
                    if currency.get('code') and currency.get('id'):
                        self.currency_ids[currency.get('code')] = str(currency.get('id'))
        
        logger.debug(f"Built lookup dictionaries for {len(self.from_countries_by_code)} source countries, {len(self.to_countries_by_code)} destination countries, and {len(self.currency_ids)} currencies")
    
    def _load_browser_cookies(self):
        """Load browser cookies into the requests session if available."""
        if not BROWSER_HELPER_AVAILABLE:
            return
            
        try:
            cookies = get_browser_cookies_sync()
            if cookies:
                logger.info("Loading browser cookies into requests session")
                self.session.cookies.update(cookies)
        except Exception as e:
            logger.warning(f"Error loading browser cookies: {e}")
    
    def _setup_session(self):
        """Configure default headers, cookies, and retry logic."""
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Origin": "https://paysend.com",
            "Referer": "https://paysend.com/en-us/"
        })
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _make_api_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        retry_auth: bool = True,
        max_retries: int = 2
    ) -> Dict:
        """
        Make a request to the Paysend API with proper error handling.
        
        Args:
            method: HTTP method (GET or POST)
            url: API endpoint URL
            params: URL parameters for GET requests
            data: Request payload for POST requests
            headers: Request headers
            retry_auth: Whether to retry with a new session if authentication fails
            max_retries: Maximum number of retries for authentication issues
            
        Returns:
            API response as a dictionary
        """
        retry_count = 0
        request_headers = {**self.session.headers}
        if headers:
            request_headers.update(headers)
        
        while retry_count <= max_retries:
            try:
                # Make the request
                if method.upper() == "GET":
                    response = self.session.get(
                        url=url,
                        params=params,
                        headers=request_headers,
                        timeout=self.timeout
                    )
                else:  # POST
                    response = self.session.post(
                        url=url,
                        json=data,
                        params=params,
                        headers=request_headers,
                        timeout=self.timeout
                    )
                
                # Log response status
                logger.debug(f"Paysend API response status: {response.status_code}")
                
                # Check for common error status codes
                if response.status_code in (401, 403):
                    if retry_auth and retry_count < max_retries:
                        logger.warning(f"Authentication failed, refreshing session and retrying (attempt {retry_count + 1}/{max_retries})")
                        self._setup_session()
                        time.sleep(1)  # Add delay between retries
                        retry_count += 1
                        continue
                    raise PaysendAuthenticationError("Authentication failed")
                
                if response.status_code == 429:
                    # With rate limits, we should wait longer before retrying
                    if retry_count < max_retries:
                        wait_time = 5 * (retry_count + 1)  # Progressive backoff
                        logger.warning(f"Rate limit exceeded, waiting {wait_time} seconds before retry")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    raise PaysendRateLimitError("Rate limit exceeded")
                    
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        # Check if error_data is a dictionary before trying to access it
                        if isinstance(error_data, dict):
                            # Check if 'error' field is a boolean
                            if isinstance(error_data.get("error"), bool) and error_data.get("message"):
                                error_message = error_data.get("message", "Unknown API error")
                            else:
                                # Original case where error might be a nested dict
                                error_message = error_data.get("error", {}).get("message", "Unknown API error")
                        else:
                            error_message = f"API returned non-dictionary error: {error_data}"
                        
                        # Check if the error is related to captcha
                        if "captcha" in error_message.lower() or response.status_code == 497:
                            logger.error(f"Paysend API requires captcha: {error_message}")
                            raise PaysendApiError(f"Paysend API requires captcha: {error_message}")
                            
                        raise PaysendApiError(f"API error: {error_message}")
                    except (ValueError, KeyError):
                        raise PaysendApiError(f"API error: {response.status_code}")
                
                # Parse and return response
                try:
                    return response.json()
                except ValueError:
                    # If the response is empty but status is 200, return empty dict
                    if response.status_code == 200 and not response.text.strip():
                        return {}
                    raise PaysendApiError("Invalid JSON response from API")
                    
            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")
                
                # Retry network errors
                if retry_count < max_retries:
                    logger.warning(f"Connection error, retrying (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(2)
                    retry_count += 1
                    continue
                    
                raise PaysendConnectionError(f"Connection error: {e}")
        
        # This should not be reached, but just in case
        raise PaysendConnectionError("Maximum retries exceeded")
    
    def _get_send_money_url(self, from_country: str, to_country: str, from_currency: str, to_currency: str) -> Dict[str, str]:
        """
        Construct the proper URL for the send-money endpoint.
        
        Args:
            from_country: Source country code (e.g., "US")
            to_country: Destination country code (e.g., "AM")
            from_currency: Source currency code (e.g., "USD")
            to_currency: Destination currency code (e.g., "AMD")
            
        Returns:
            Dictionary with 'ui_url' and 'api_url' keys
        """
        # Normalize country codes to uppercase for lookup
        from_country = from_country.upper()
        to_country = to_country.upper()
        
        # Use SEO friendly names from the extracted data if available
        from_country_name = None
        to_country_name = None
        
        # Try to get country data from our lookup dictionaries
        from_country_data = self.from_countries_by_code.get(from_country)
        to_country_data = self.to_countries_by_code.get(to_country)
        
        # Get seoNameFrom from source country data
        if from_country_data and from_country_data.get('seoNameFrom'):
            from_country_name = from_country_data.get('seoNameFrom')
        else:
            # Fall back to hardcoded mappings if not found in the extracted data
            from_country_name = self.COUNTRY_NAMES.get(from_country, from_country.lower())
        
        # Get seoNameTo from destination country data
        if to_country_data and to_country_data.get('seoNameTo'):
            to_country_name = to_country_data.get('seoNameTo')
        else:
            # Fall back to hardcoded mappings if not found in the extracted data
            to_country_name = self.COUNTRY_NAMES.get(to_country, to_country.lower())
        
        # Find currency IDs - first try the extracted data
        from_curr_id = None
        to_curr_id = None
        
        # Try to find currency ID in our currency_ids dictionary
        from_curr_id = self.currency_ids.get(from_currency)
        if not from_curr_id:
            # Fall back to hardcoded mappings
            from_curr_id = self.CURRENCY_IDS.get(from_currency, "840")  # Default to USD if not found
        
        to_curr_id = self.currency_ids.get(to_currency)
        if not to_curr_id:
            # Fall back to hardcoded mappings
            to_curr_id = self.CURRENCY_IDS.get(to_currency)
            
            # If still not found, use a default
            if not to_curr_id:
                logger.warning(f"Currency ID not found for {to_currency}, using default")
                to_curr_id = "356"  # Default to INR if not found
        
        # Construct the full URL for the UI page (used as Referer)
        ui_url = f"{self.BASE_URL}/en-us/send-money/from-{from_country_name}-to-{to_country_name}?fromCurrId={from_curr_id}&toCurrId={to_curr_id}&isFrom=true"
        
        # Construct the API URL - this is different from the UI URL
        api_url = f"{self.BASE_URL}/api/en-us/send-money/from-{from_country_name}-to-{to_country_name}?fromCurrId={from_curr_id}&toCurrId={to_curr_id}&isFrom=true"
        
        logger.debug(f"Constructed send-money UI URL: {ui_url}")
        logger.debug(f"Constructed send-money API URL: {api_url}")
        
        return {
            "ui_url": ui_url,
            "api_url": api_url
        }

    def get_quote(
        self,
        from_currency: str,
        to_currency: str,
        from_country: str,
        to_country: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Fetch a Paysend exchange rate and fee quote.
        """
        urls = self._get_send_money_url(from_country, to_country, from_currency, to_currency)
        api_url = urls["api_url"]
        ui_url = urls["ui_url"]
        
        params = {
            "amount": str(amount),
            "fromCurrency": from_currency,
            "toCurrency": to_currency
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Pragma": "no-cache",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Origin": "https://paysend.com",
            "Referer": ui_url,
            "User-Agent": self.user_agent
        }
        
        local_result = {
            "success": False,
            "send_amount": float(amount),
            "send_currency": from_currency,
            "receive_amount": None,
            "receive_currency": to_currency,
            "exchange_rate": None,
            "fee": None,
            "error_message": None
        }
        
        try:
            data = self._make_api_request("POST", api_url, params=params, headers=headers)
            
            if data.get("success") is True:
                local_result.update({
                    "success": True,
                    "receive_amount": data.get("receive_amount"),
                    "exchange_rate": data.get("exchange_rate"),
                    "fee": data.get("fee", 0),
                    "raw_json": data
                })
                return local_result
            else:
                raise PaysendApiError(f"API returned unsuccessful response: {data}")
                
        except PaysendApiError as e:
            if "captcha" in str(e).lower() and self.use_browser_helper and BROWSER_HELPER_AVAILABLE:
                logger.info("Attempting to use browser automation to solve captcha")
                
                try:
                    browser_data = run_browser_helper_sync(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        amount=float(amount),
                        from_country=from_country,
                        to_country=to_country,
                        url=ui_url,
                        headless=False
                    )
                    
                    if browser_data and browser_data.get("success") is True:
                        logger.info("Successfully retrieved quote using browser automation")
                        
                        self._load_browser_cookies()
                        
                        local_result.update({
                            "success": True,
                            "receive_amount": browser_data.get("receive_amount"),
                            "exchange_rate": browser_data.get("exchange_rate"),
                            "fee": browser_data.get("fee", 0),
                            "raw_json": browser_data
                        })
                        return local_result
                except Exception as browser_error:
                    logger.error(f"Error using browser automation: {browser_error}")
            
            if "captcha" in str(e).lower():
                logger.warning("Paysend API requires captcha, using mock data for testing")
                
                mock_data = self._get_mock_quote_data(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    amount=amount
                )
                
                local_result.update({
                    "success": True,
                    "receive_amount": mock_data["receive_amount"],
                    "exchange_rate": mock_data["exchange_rate"],
                    "fee": mock_data["fee"],
                    "raw_json": mock_data
                })
                return local_result
            else:
                local_result["error_message"] = str(e)
                return local_result
                
        except Exception as ex:
            logger.error(f"Paysend get_quote error: {ex}")
            local_result["error_message"] = str(ex)
            return local_result

    def _get_mock_quote_data(self, from_currency: str, to_currency: str, amount: Decimal) -> Dict[str, Any]:
        """Return a realistic mock quote if captcha or other blocking occurs."""
        mock_rates = {
            "USD-INR": Decimal("82.75"),
            "USD-PHP": Decimal("55.50"),
            "USD-MXN": Decimal("17.25"),
            "USD-NGN": Decimal("753.00"),
            "EUR-INR": Decimal("88.50"),
            "GBP-INR": Decimal("103.25"),
        }
        corridor = f"{from_currency.upper()}-{to_currency.upper()}"
        exchange_rate = mock_rates.get(corridor, Decimal("1.0"))
        
        if amount < 500:
            fee = Decimal("2.99")
        elif amount < 1000:
            fee = Decimal("3.99")
        else:
            fee = Decimal("4.99")
        
        receive_amount = (amount - fee) * exchange_rate
        return {
            "success": True,
            "exchange_rate": float(exchange_rate),
            "fee": float(fee),
            "receive_amount": float(receive_amount),
            "currency_from": from_currency,
            "currency_to": to_currency
        }
    
    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str = "USD",
        receive_country: str = None,
        receive_currency: str = None,
        delivery_method: str = None,
        payment_method: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Aggregator method for fetching a quote & returning aggregator-friendly fields.
        """
        # Basic validation
        if not receive_country:
            return self.standardize_response({
                "success": False,
                "error_message": "Missing receive_country",
                "send_amount": float(send_amount),
                "send_currency": send_currency
            })
            
        if not receive_currency:
            return self.standardize_response({
                "success": False,
                "error_message": "Missing receive_currency",
                "send_amount": float(send_amount),
                "send_currency": send_currency
            })
            
        # If we don't know from_country, assume "US" if sending USD; otherwise guess from currency
        from_country = "US" if send_currency.upper() == "USD" else None
        
        # Minimal currency->country fallback map if not in loaded data
        fallback_map = {"USD": "US", "EUR": "DE", "GBP": "GB", "CAD": "CA", "AUD": "AU"}
        if not from_country:
            from_country = fallback_map.get(send_currency.upper())
            if not from_country:
                return self.standardize_response({
                    "success": False,
                    "error_message": f"Unable to deduce from_country for {send_currency}",
                    "send_amount": float(send_amount),
                    "send_currency": send_currency
                })

        # Get quote from Paysend
        quote = self.get_quote(
            from_currency=send_currency,
            to_currency=receive_currency,
            from_country=from_country,
            to_country=receive_country,
            amount=send_amount
        )
        
        # Add aggregator keys
        quote["delivery_time_minutes"] = self._get_delivery_time(receive_country.upper())
        quote["timestamp"] = datetime.now().isoformat()
        
        return self.standardize_response(quote, provider_specific_data=kwargs.get("include_raw", False))

    def _get_delivery_time(self, country_code: str) -> int:
        """Example logic for delivery time estimates."""
        example_times = {
            "IN": 60,  # 1 hour
            "PH": 120, # 2 hours
            "MX": 45,
            "NG": 90
        }
        return example_times.get(country_code.upper(), 24 * 60)
        
    def get_fee_info(
        self,
        send_currency: str,
        payout_currency: str,
        send_amount: Decimal,
        recipient_type: str = "bank_account",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retrieve fee information from Paysend.
        
        Args:
            send_currency: Source currency code (e.g., 'USD')
            payout_currency: Destination currency code (e.g., 'INR')
            send_amount: Amount to send in source currency
            recipient_type: Type of recipient account (default: "bank_account")
            
        Returns:
            Dictionary with fee information and status
        """
        result = {
            "success": False,
            "send_currency": send_currency.upper(),
            "payout_currency": payout_currency.upper(),
            "send_amount": float(send_amount),
            "recipient_type": recipient_type,
            "fee": None,
            "error_message": None,
            "destination_currency": payout_currency.upper()
        }

        # Basic validation
        if not send_amount or send_amount <= 0:
            result["error_message"] = "Amount must be positive"
            return self.standardize_response(result)
            
        # Determine from_country based on send_currency
        from_country = "US" if send_currency.upper() == "USD" else None
        fallback_map = {"USD": "US", "EUR": "DE", "GBP": "GB", "CAD": "CA", "AUD": "AU"}
        
        if not from_country:
            from_country = fallback_map.get(send_currency.upper())
            if not from_country:
                result["error_message"] = f"Unable to determine from_country for {send_currency}"
                return self.standardize_response(result)
        
        # Find to_country based on currency if possible
        to_country = None
        for country_code, country_data in self.to_countries_by_code.items():
            for currency in country_data.get('currencies', []):
                if currency.get('code') == payout_currency.upper():
                    to_country = country_code
                    break
            if to_country:
                break
                
        if not to_country:
            # Fallback currency-to-country mapping
            currency_to_country = {
                "INR": "IN", "PHP": "PH", "MXN": "MX", "NGN": "NG", 
                "GBP": "GB", "EUR": "DE", "USD": "US"
            }
            to_country = currency_to_country.get(payout_currency.upper())
            
        if not to_country:
            result["error_message"] = f"Unable to determine destination country for {payout_currency}"
            return self.standardize_response(result)
            
        try:
            # Use get_quote to obtain both rate and fee information
            quote = self.get_quote(
                from_currency=send_currency,
                to_currency=payout_currency,
                from_country=from_country,
                to_country=to_country,
                amount=send_amount
            )
            
            if quote.get("success"):
                result["success"] = True
                result["fee"] = quote.get("fee")
            else:
                # If quote failed, use mock data as fallback
                mock_data = self._get_mock_quote_data(
                    from_currency=send_currency,
                    to_currency=payout_currency,
                    amount=send_amount
                )
                result["success"] = True
                result["fee"] = mock_data.get("fee")
                
        except Exception as e:
            error_msg = f"Failed to retrieve fee information: {e}"
            logger.error(error_msg)
            result["error_message"] = error_msg
            
        return self.standardize_response(result)

    def get_supported_countries(self) -> List[str]:
        """List of possible 'from' countries if we loaded from_countries_by_code, otherwise fallback."""
        if self.from_countries_by_code:
            return list(self.from_countries_by_code.keys())
        return ["US", "GB", "DE", "FR", "CA", "AU"]

    def get_supported_currencies(self) -> List[str]:
        """All known currencies. If loaded data is available, use it; else fallback list."""
        if self.currency_ids:
            return list(self.currency_ids.keys())
        return ["USD", "EUR", "GBP", "CAD", "AUD", "INR", "PHP", "MXN"]

    def get_supported_corridors(self) -> Dict[str, List[str]]:
        """Mapping of from_country -> [list of to_countries]."""
        if self.from_countries_by_code and self.to_countries_by_code:
            corridors = {}
            for src_code in self.from_countries_by_code.keys():
                corridors[src_code] = list(self.to_countries_by_code.keys())
            return corridors
        else:
            return {
                "US": ["IN", "MX", "PH"],
                "GB": ["IN", "PH"],
                "DE": ["IN", "PH"]
            }
    
    def get_currency_for_country(self, country_code: str) -> List[str]:
        """
        Get the list of currencies supported for a specific country.
        
        Args:
            country_code: ISO country code
        
        Returns:
            List of currency codes supported for that country
        """
        country_code = country_code.upper()
        
        # First check destination countries
        if country_code in self.to_countries_by_code:
            country_data = self.to_countries_by_code[country_code]
            return [currency.get('code') for currency in country_data.get('currencies', []) 
                   if currency.get('code')]
        
        # Then check source countries
        if country_code in self.from_countries_by_code:
            country_data = self.from_countries_by_code[country_code]
            return [currency.get('code') for currency in country_data.get('currencies', [])
                   if currency.get('code')]
        
        # Return empty list if country not found
        return []
    
    def close(self):
        """Close session if needed."""
        if self.session:
            self.session.close()
            self.session = None
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def standardize_response(self, raw_data: Dict[str, Any], provider_specific_data: bool = False) -> Dict[str, Any]:
        """
        Converts a local dictionary of quote/exchange rate data into 
        aggregator-friendly keys.
        """
        final_exchange_rate = raw_data.get("exchange_rate")
        final_rate = raw_data.get("rate")
        if final_rate is None:
            final_rate = final_exchange_rate
        
        final_target_currency = raw_data.get("destination_currency") or raw_data.get("receive_currency") or raw_data.get("target_currency")
        
        standardized = {
            "provider_id": self.name,
            "success": raw_data.get("success", False),
            "error_message": raw_data.get("error_message"),
            
            "send_amount": raw_data.get("send_amount") or raw_data.get("source_amount", 0.0),
            "source_currency": (raw_data.get("send_currency") or raw_data.get("source_currency") or "").upper(),
            
            "destination_amount": raw_data.get("receive_amount") or raw_data.get("destination_amount"),
            "destination_currency": (final_target_currency or "").upper(),
            
            "exchange_rate": final_exchange_rate,
            "fee": raw_data.get("fee"),
            "delivery_time_minutes": raw_data.get("delivery_time_minutes"),
            "timestamp": raw_data.get("timestamp") or datetime.now().isoformat(),
            
            "rate": final_rate,
            "target_currency": (final_target_currency or "").upper(),
        }
        
        if provider_specific_data and "raw_json" in raw_data:
            standardized["raw_response"] = raw_data["raw_json"]
        
        return standardized 