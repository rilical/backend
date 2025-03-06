"""
Remitly Money Transfer Integration

This module implements the integration with Remitly, a service for international
money transfers. Remitly supports various payment and delivery methods.

PAYMENT METHODS:
---------------------------------
- BANK_ACCOUNT: Bank account transfer
- DEBIT_CARD: Debit card payment
- CREDIT_CARD: Credit card payment

DELIVERY METHODS:
---------------------------------
- BANK_DEPOSIT: Bank deposit
- CASH_PICKUP: Cash pickup at agent locations
- HOME_DELIVERY: Cash delivered to recipient's home
- MOBILE_WALLET: Mobile wallet transfer

Important API notes:
1. Remitly's API requires specific headers including Remitly-DeviceEnvironmentID
2. Each corridor has different combinations of payment and delivery methods
3. Fees vary significantly based on payment method, delivery method, and amount
4. Exchange rates can vary by corridor and amount
"""

import json
import logging
import re
import time
import uuid
from decimal import Decimal
from typing import Dict, Optional, Any, List, Union, Tuple

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from apps.providers.remitly.exceptions import (
    RemitlyError,
    RemitlyAuthenticationError,
    RemitlyConnectionError,
    RemitlyValidationError,
    RemitlyRateLimitError
)

# Setup logging
logger = logging.getLogger(__name__)

class ExchangeRateResult:
    """Class to store exchange rate information in a standardized format."""
    
    def __init__(
        self,
        provider_id: str,
        source_currency: str,
        source_amount: float,
        destination_currency: str,
        destination_amount: float,
        exchange_rate: float,
        fee: float,
        delivery_method: str,
        delivery_time_minutes: Optional[int] = None,
        corridor: Optional[str] = None,
        payment_method: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        self.provider_id = provider_id
        self.source_currency = source_currency
        self.source_amount = source_amount
        self.destination_currency = destination_currency
        self.destination_amount = destination_amount
        self.exchange_rate = exchange_rate
        self.fee = fee
        self.delivery_method = delivery_method
        self.delivery_time_minutes = delivery_time_minutes
        self.corridor = corridor
        self.payment_method = payment_method
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        """Convert the result to a dictionary."""
        return {
            "provider_id": self.provider_id,
            "source_currency": self.source_currency,
            "source_amount": self.source_amount,
            "destination_currency": self.destination_currency,
            "destination_amount": self.destination_amount,
            "exchange_rate": self.exchange_rate,
            "fee": self.fee,
            "delivery_method": self.delivery_method,
            "delivery_time_minutes": self.delivery_time_minutes,
            "corridor": self.corridor,
            "payment_method": self.payment_method,
            "details": self.details
        }

class RemitlyProvider(RemittanceProvider):
    """Integration with Remitly money transfer service."""
    
    BASE_URL = "https://api.remitly.io"
    CALCULATOR_ENDPOINT = "/v3/calculator/estimate"
    
    # Sample default header values from real Safari on macOS
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.3 Safari/605.1.15"
    )
    
    # Example device environment ID; in practice you might discover or refresh this dynamically
    DEFAULT_DEVICE_ENV_ID = (
        "3RoCMEE0ZDG79rpNP7sK7MoEVrYFpVS4TgavrNTpz405kCFlIwl0s49e1xh4okoKhH2bA"
        "HxYPg0GZINPtd1BG4xDZGA0b0wOoffs2ZSr9Lm1"
    )
    
    # Optional browser fingerprint data (from Branch)
    DEFAULT_BROWSER_FINGERPRINT = {
        "browser_fingerprint_id": "1424498403190294011",
        "session_id": "1424498403198931748",
        "identity_id": "1424498403198837863",
        "link": "https://link.remitly.com/a/key_live_fedYw0b1AK8QmSuljIyvAmdbrAbwqqAc"
                "?%24identity_id=1424498403198837863",
        "data": "{\"+clicked_branch_link\":false,\"+is_first_session\":true}",
        "has_app": False
    }
    
    # Mapping of Remitly payment method types to standardized names
    PAYMENT_METHODS = {
        "BANK_ACCOUNT": "Bank Account",
        "DEBIT_CARD": "Debit Card",
        "CREDIT_CARD": "Credit Card"
    }
    
    # Mapping of Remitly delivery methods to standardized names
    DELIVERY_METHODS = {
        "BANK_DEPOSIT": "Bank Deposit",
        "CASH_PICKUP": "Cash Pickup",
        "HOME_DELIVERY": "Home Delivery",
        "MOBILE_WALLET": "Mobile Wallet"
    }
    
    def __init__(
        self,
        device_env_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the Remitly provider.
        
        Args:
            device_env_id: Remitly-DeviceEnvironmentID to send in headers
            user_agent: Custom user agent string (or None to use a default Safari-like UA)
            timeout: Request timeout in seconds
        """
        super().__init__(name="Remitly", base_url=self.BASE_URL)
        
        self.timeout = timeout
        self.device_env_id = device_env_id or self.DEFAULT_DEVICE_ENV_ID
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        
        # Initialize session and cookies
        self.session = requests.Session()
        self._setup_session()
        
        # Set up logger
        self.logger = logging.getLogger('remitly_provider')
    
    def _setup_session(self) -> None:
        """Configure default headers, cookies, and retry logic for the requests session."""
        # Common headers used by Remitly from a real browser:
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.remitly.com",  # The site that might embed the JS
            "Referer": "https://www.remitly.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        
        # Example of including "Branch" or "browser fingerprint" data in a custom header
        fingerprint_json = json.dumps(self.DEFAULT_BROWSER_FINGERPRINT)
        self.session.headers["X-Remitly-Browser-Fingerprint"] = fingerprint_json
        
        # The critical Remitly device environment ID:
        self.session.headers["Remitly-DeviceEnvironmentID"] = self.device_env_id
        
        # Configure retry logic with backoff
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
        retry_auth: bool = True,
        max_retries: int = 2
    ) -> Dict:
        """
        Make a request to the Remitly API with proper error handling.
        
        Args:
            method: HTTP method (GET or POST)
            url: API endpoint URL
            params: URL parameters for GET requests
            data: Request payload for POST requests
            retry_auth: Whether to retry with a new session if authentication fails
            max_retries: Maximum number of retries for authentication issues
            
        Returns:
            API response as a dictionary
        """
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Make the request
                if method.upper() == "GET":
                    response = self.session.get(
                        url=url,
                        params=params,
                        timeout=self.timeout,
                        allow_redirects=False  # Don't automatically follow redirects
                    )
                else:  # POST
                    response = self.session.post(
                        url=url,
                        json=data,
                        params=params,
                        timeout=self.timeout,
                        allow_redirects=False  # Don't automatically follow redirects
                    )
                
                # Log response status
                logger.debug(f"Remitly API response status: {response.status_code}")
                
                # Handle redirects manually to capture authentication issues
                if response.status_code in (301, 302, 303, 307, 308):
                    redirect_url = response.headers.get('Location')
                    logger.debug(f"Redirected to: {redirect_url}")
                    
                    # Check if redirected to sign-in page
                    if redirect_url and '/sign-in' in redirect_url:
                        if retry_auth and retry_count < max_retries:
                            logger.warning(f"Redirected to sign-in page, refreshing session (attempt {retry_count + 1}/{max_retries})")
                            self._setup_session()
                            time.sleep(1)  # Add delay between retries
                            retry_count += 1
                            continue
                        else:
                            raise RemitlyAuthenticationError("Authentication failed: redirected to sign-in page")
                
                # Check for common error status codes
                if response.status_code in (401, 403):
                    if retry_auth and retry_count < max_retries:
                        logger.warning(f"Authentication failed, refreshing session and retrying (attempt {retry_count + 1}/{max_retries})")
                        self._setup_session()
                        time.sleep(1)  # Add delay between retries
                        retry_count += 1
                        continue
                    raise RemitlyAuthenticationError("Authentication failed")
                
                if response.status_code == 429:
                    # With rate limits, we should wait longer before retrying
                    if retry_count < max_retries:
                        wait_time = 5 * (retry_count + 1)  # Progressive backoff
                        logger.warning(f"Rate limit exceeded, waiting {wait_time} seconds before retry")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    raise RemitlyRateLimitError("Rate limit exceeded")
                    
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", "Unknown API error")
                        raise RemitlyError(f"API error: {error_message}")
                    except (ValueError, KeyError):
                        raise RemitlyError(f"API error: {response.status_code}")
                
                # Parse and return response
                try:
                    return response.json()
                except ValueError:
                    # If the response is empty but status is 200, return empty dict
                    if response.status_code == 200 and not response.text.strip():
                        return {}
                    raise RemitlyError("Invalid JSON response from API")
                    
            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")
                
                # Retry network errors
                if retry_count < max_retries:
                    logger.warning(f"Connection error, retrying (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(2)
                    retry_count += 1
                    continue
                    
                raise RemitlyConnectionError(f"Connection error: {e}")
        
        # This should not be reached, but just in case
        raise RemitlyError("Maximum retries exceeded")
    
    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str = "USD",
        receive_country: str = None,
        receive_currency: str = None,
        delivery_method: str = None,  # Optional 
        payment_method: str = None,   # Optional
        purpose: str = "OTHER",
        customer_segment: str = "UNRECOGNIZED",
        strict_promo: bool = False
    ) -> Dict:
        """
        Get the exchange rate for a given amount and corridor.
        
        Args:
            send_amount: The amount to send.
            send_currency: The currency to send (default: USD).
            receive_country: The destination country code.
            receive_currency: The destination currency code.
            delivery_method: Optional delivery method preference.
            payment_method: Optional payment method preference.
            purpose: One of the recognized "purpose" strings (ex: "OTHER", "BILLS", etc.)
            customer_segment: e.g. "UNRECOGNIZED", "REFERRAL", "EXISTING", etc.
            strict_promo: Whether or not to force ignoring promotions
            
        Returns:
            Dict containing exchange rate details.
        """
        if receive_country is None:
            raise RemitlyValidationError("Receive country is required")
            
        # Map the send currency to an appropriate source country
        source_country = self._get_country_for_currency(send_currency)
        
        # Convert country codes if needed (e.g., 2-letter to 3-letter)
        if len(receive_country) == 2:
            receive_country = self._convert_country_code(receive_country)
        
        # If receive_currency is not provided, try to determine from country
        if receive_currency is None:
            receive_currency = self._get_currency_for_country(receive_country)
        
        # Convert decimal to float for API request
        send_amount_float = float(send_amount)
        
        # Construct the `conduit` param e.g. "USA:USD-PHL:PHP"
        conduit_str = f"{source_country}:{send_currency}-{receive_country}:{receive_currency}"
        
        # Build the request URL and parameters
        url = f"{self.base_url}{self.CALCULATOR_ENDPOINT}"
        params = {
            "conduit": conduit_str,
            "anchor": "SEND",  # Fixed to "SEND" since we're providing the send amount
            "amount": str(send_amount_float),
            "purpose": purpose,
            "customer_segment": customer_segment,
            "strict_promo": str(strict_promo).lower()
        }
        
        # Log the request for debugging
        logger.debug(f"Requesting Remitly rate with URL: {url}")
        logger.debug(f"Params: {params}")
        
        try:
            # Make the API request
            response = self._make_api_request(
                method="GET",
                url=url,
                params=params
            )
            
            # Process the response to extract exchange rate info
            if not response:
                raise RemitlyError("Failed to get exchange rate data")
            
            # The Remitly estimate JSON is typically in response["estimate"]
            estimate = response.get("estimate", {})
            if not estimate:
                raise RemitlyError("No estimate data available")
            
            # Extract exchange rate
            exchange_rate_data = estimate.get("exchange_rate", {})
            exchange_rate = float(exchange_rate_data.get("base_rate", 0.0))
            
            # Extract fee
            fee_data = estimate.get("fee", {})
            fee = float(fee_data.get("total_fee_amount", 0.0))
            
            # Extract receive amount
            receive_amount_str = estimate.get("receive_amount", "0.0")
            receive_amount = float(receive_amount_str) if receive_amount_str else 0.0
            
            # Extract delivery time if available
            delivery_time_minutes = None
            delivery_time_text = estimate.get("delivery_speed_description", "")
            
            # Parse delivery time
            if "minutes" in delivery_time_text.lower():
                try:
                    minutes_match = re.search(r'(\d+)\s*minutes', delivery_time_text.lower())
                    if minutes_match:
                        delivery_time_minutes = int(minutes_match.group(1))
                except (ValueError, AttributeError):
                    pass
            elif "hours" in delivery_time_text.lower():
                try:
                    hours_match = re.search(r'(\d+)\s*hours', delivery_time_text.lower())
                    if hours_match:
                        delivery_time_minutes = int(hours_match.group(1)) * 60
                except (ValueError, AttributeError):
                    pass
            
            # Build standardized result object
            result = ExchangeRateResult(
                provider_id="Remitly",
                source_currency=send_currency,
                source_amount=send_amount_float,
                destination_currency=receive_currency,
                destination_amount=receive_amount,
                exchange_rate=exchange_rate,
                fee=fee,
                delivery_method=self._normalize_delivery_method(estimate.get("delivery_method", "")),
                delivery_time_minutes=delivery_time_minutes,
                corridor=f"{source_country}-{receive_country}",
                payment_method=estimate.get("payment_method", ""),
                details={"raw_response": response}  # Store raw response for reference
            )
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Error getting exchange rate from Remitly: {str(e)}")
            
            # Return fallback/mockup data if API call failed
            return self._get_fallback_exchange_rate(
                send_amount_float, 
                send_currency, 
                receive_country, 
                receive_currency
            )
    
    def _get_fallback_exchange_rate(
        self,
        send_amount: float,
        send_currency: str,
        receive_country: str,
        receive_currency: str
    ) -> Dict:
        """
        Return fallback exchange rate data if the API call fails.
        
        Args:
            send_amount: The amount to send
            send_currency: The currency to send
            receive_country: The destination country code
            receive_currency: The destination currency code
            
        Returns:
            Dict containing mocked exchange rate details
        """
        # Source country from send currency
        source_country = self._get_country_for_currency(send_currency)
        
        # Comprehensive mock rates for common currencies (against USD)
        usd_rates = {
            # North America
            "USD": 1.0, "CAD": 1.36, "MXN": 19.85,
            
            # Central/South America
            "PHP": 56.20, "INR": 83.10, "COP": 3900.0, "GTQ": 7.75,
            "BRL": 5.45, "ARS": 875.0, "CLP": 950.0, "PEN": 3.75,
            "DOP": 58.0, "HNL": 24.8, "NIO": 36.5, "BOB": 6.91,
            
            # Europe
            "EUR": 0.93, "GBP": 0.79, "CHF": 0.91, "SEK": 10.55,
            "NOK": 10.65, "DKK": 6.95, "PLN": 4.0, "CZK": 23.3,
            "HUF": 356.0, "RON": 4.65, "BGN": 1.82, "RSD": 110.0,
            "UAH": 39.5, "RUB": 92.0,
            
            # Asia/Pacific
            "CNY": 7.25, "JPY": 151.0, "KRW": 1360.0, "IDR": 16000.0,
            "MYR": 4.6, "SGD": 1.35, "THB": 35.8, "VND": 25000.0,
            "PKR": 278.0, "BDT": 110.0, "NPR": 133.0, "LKR": 315.0, 
            "ILS": 3.7, "SAR": 3.75, "AED": 3.67, "TRY": 31.8,
            
            # Africa
            "DZD": 134.0, "EGP": 47.0, "MAD": 10.0, "NGN": 1550.0,
            "KES": 129.0, "GHS": 15.0, "ZAR": 18.6, "TND": 3.15,
            "ETB": 57.0, "UGX": 3800.0, "TZS": 2600.0,
            
            # Oceania
            "AUD": 1.54, "NZD": 1.67, "FJD": 2.25, "PGK": 3.7
        }
        
        # Calculate exchange rate based on source and destination currencies
        # First convert source currency to USD equivalent
        if send_currency == "USD":
            usd_amount = send_amount
        else:
            # If source is not USD, convert to USD first (using inverse rate)
            source_usd_rate = usd_rates.get(send_currency, 1.0)
            usd_amount = send_amount / source_usd_rate if source_usd_rate != 0 else send_amount
        
        # Then convert from USD to destination currency
        dest_usd_rate = usd_rates.get(receive_currency, 10.0)
        exchange_rate = dest_usd_rate
        
        # If source is not USD, we need to calculate the direct exchange rate
        if send_currency != "USD":
            source_usd_rate = usd_rates.get(send_currency, 1.0)
            exchange_rate = dest_usd_rate / source_usd_rate if source_usd_rate != 0 else dest_usd_rate
        
        # Calculate receive amount based on the exchange rate
        receive_amount = send_amount * exchange_rate
        
        # Define standard fees based on amount and currency
        fee = 0.0
        if send_currency == "USD":
            if send_amount >= 1000:
                fee = 3.99
            elif send_amount >= 500:
                fee = 1.99
            elif send_amount >= 100:
                fee = 0.99
        elif send_currency == "EUR":
            if send_amount >= 1000:
                fee = 3.49
            elif send_amount >= 500:
                fee = 1.99
            elif send_amount >= 100:
                fee = 0.99
        elif send_currency == "GBP":
            if send_amount >= 800:
                fee = 2.99
            elif send_amount >= 400:
                fee = 1.49
            elif send_amount >= 80:
                fee = 0.79
        else:
            # Default fee structure for other currencies
            if send_amount >= 1000:
                fee = 3.99
            elif send_amount >= 500:
                fee = 1.99
            elif send_amount >= 100:
                fee = 0.99
        
        # Build fallback result with source country
        return {
            "provider_id": "Remitly",
            "source_currency": send_currency,
            "source_amount": send_amount,
            "destination_currency": receive_currency,
            "destination_amount": receive_amount,
            "exchange_rate": exchange_rate,
            "fee": fee,
            "delivery_method": "bank deposit",
            "delivery_time_minutes": 60,  # Default: 1 hour
            "corridor": f"{source_country}-{receive_country}",
            "payment_method": "Bank Account",
            "details": {"is_fallback": True}
        }
    
    def _get_currency_for_country(self, country_code: str) -> str:
        """
        Get the currency code for a country.
        
        Args:
            country_code: Two-letter or three-letter country code
            
        Returns:
            Currency code for the country
        """
        # Comprehensive country to currency mappings
        country_to_currency = {
            # North America
            "USA": "USD", "US": "USD",
            "CAN": "CAD", "CA": "CAD",
            "MEX": "MXN", "MX": "MXN",
            
            # Central America
            "GTM": "GTQ", "GT": "GTQ",
            "SLV": "USD", "SV": "USD",
            "HND": "HNL", "HN": "HNL",
            "NIC": "NIO", "NI": "NIO",
            "CRI": "CRC", "CR": "CRC",
            "PAN": "PAB", "PA": "PAB",
            "BLZ": "BZD", "BZ": "BZD",
            
            # Caribbean
            "DOM": "DOP", "DO": "DOP",
            "JAM": "JMD", "JM": "JMD",
            "HTI": "HTG", "HT": "HTG",
            "CUB": "CUP", "CU": "CUP",
            
            # South America
            "COL": "COP", "CO": "COP",
            "PER": "PEN", "PE": "PEN",
            "ECU": "USD", "EC": "USD",
            "BOL": "BOB", "BO": "BOB",
            "CHL": "CLP", "CL": "CLP",
            "BRA": "BRL", "BR": "BRL",
            "ARG": "ARS", "AR": "ARS",
            "VEN": "VES", "VE": "VES",
            "PRY": "PYG", "PY": "PYG",
            "URY": "UYU", "UY": "UYU",
            "GUY": "GYD", "GY": "GYD",
            
            # Europe
            "ESP": "EUR", "ES": "EUR",
            "DEU": "EUR", "DE": "EUR",
            "FRA": "EUR", "FR": "EUR",
            "ITA": "EUR", "IT": "EUR",
            "NLD": "EUR", "NL": "EUR",
            "BEL": "EUR", "BE": "EUR",
            "PRT": "EUR", "PT": "EUR",
            "GRC": "EUR", "GR": "EUR",
            "AUT": "EUR", "AT": "EUR",
            "IRL": "EUR", "IE": "EUR",
            "FIN": "EUR", "FI": "EUR",
            "GBR": "GBP", "GB": "GBP",
            "CHE": "CHF", "CH": "CHF",
            "SWE": "SEK", "SE": "SEK",
            "NOR": "NOK", "NO": "NOK",
            "DNK": "DKK", "DK": "DKK",
            "POL": "PLN", "PL": "PLN",
            "CZE": "CZK", "CZ": "CZK",
            "HUN": "HUF", "HU": "HUF",
            "ROU": "RON", "RO": "RON",
            "BGR": "BGN", "BG": "BGN",
            "HRV": "EUR", "HR": "EUR",
            "SRB": "RSD", "RS": "RSD",
            "UKR": "UAH", "UA": "UAH",
            "RUS": "RUB", "RU": "RUB",
            
            # Asia
            "IND": "INR", "IN": "INR",
            "PHL": "PHP", "PH": "PHP",
            "CHN": "CNY", "CN": "CNY",
            "JPN": "JPY", "JP": "JPY",
            "KOR": "KRW", "KR": "KRW",
            "IDN": "IDR", "ID": "IDR",
            "MYS": "MYR", "MY": "MYR",
            "SGP": "SGD", "SG": "SGD",
            "THA": "THB", "TH": "THB",
            "VNM": "VND", "VN": "VND",
            "PAK": "PKR", "PK": "PKR",
            "BGD": "BDT", "BD": "BDT",
            "NPL": "NPR", "NP": "NPR",
            "LKA": "LKR", "LK": "LKR",
            "MMR": "MMK", "MM": "MMK",
            "KHM": "KHR", "KH": "KHR",
            "LAO": "LAK", "LA": "LAK",
            "ISR": "ILS", "IL": "ILS",
            "SAU": "SAR", "SA": "SAR",
            "ARE": "AED", "AE": "AED",
            "TUR": "TRY", "TR": "TRY",
            
            # Africa
            "DZA": "DZD", "DZ": "DZD",
            "EGY": "EGP", "EG": "EGP",
            "MAR": "MAD", "MA": "MAD",
            "NGA": "NGN", "NG": "NGN",
            "KEN": "KES", "KE": "KES",
            "GHA": "GHS", "GH": "GHS",
            "ZAF": "ZAR", "ZA": "ZAR",
            "TUN": "TND", "TN": "TND",
            "ETH": "ETB", "ET": "ETB",
            "UGA": "UGX", "UG": "UGX",
            "TZA": "TZS", "TZ": "TZS",
            "SEN": "XOF", "SN": "XOF",
            "CMR": "XAF", "CM": "XAF",
            
            # Oceania
            "AUS": "AUD", "AU": "AUD",
            "NZL": "NZD", "NZ": "NZD",
            "FJI": "FJD", "FJ": "FJD",
            "PNG": "PGK", "PG": "PGK"
        }
        
        return country_to_currency.get(country_code, "USD")
    
    def _convert_country_code(self, country_code: str) -> str:
        """
        Convert 2-letter country code to 3-letter code.
        
        Args:
            country_code: Two-letter country code
            
        Returns:
            Three-letter country code
        """
        if len(country_code) != 2:
            return country_code
            
        # Comprehensive mapping of 2-letter to 3-letter country codes
        country_code_map = {
            # North America
            "US": "USA", "CA": "CAN", "MX": "MEX",
            
            # Central America
            "GT": "GTM", "SV": "SLV", "HN": "HND", "NI": "NIC", 
            "CR": "CRI", "PA": "PAN", "BZ": "BLZ",
            
            # Caribbean
            "DO": "DOM", "JM": "JAM", "HT": "HTI", "CU": "CUB",
            
            # South America
            "CO": "COL", "PE": "PER", "EC": "ECU", "BO": "BOL",
            "CL": "CHL", "BR": "BRA", "AR": "ARG", "VE": "VEN",
            "PY": "PRY", "UY": "URY", "GY": "GUY",
            
            # Europe
            "ES": "ESP", "DE": "DEU", "FR": "FRA", "IT": "ITA",
            "NL": "NLD", "BE": "BEL", "PT": "PRT", "GR": "GRC",
            "AT": "AUT", "IE": "IRL", "FI": "FIN", "GB": "GBR",
            "CH": "CHE", "SE": "SWE", "NO": "NOR", "DK": "DNK",
            "PL": "POL", "CZ": "CZE", "HU": "HUN", "RO": "ROU",
            "BG": "BGR", "HR": "HRV", "RS": "SRB", "UA": "UKR",
            "RU": "RUS",
            
            # Asia
            "IN": "IND", "PH": "PHL", "CN": "CHN", "JP": "JPN",
            "KR": "KOR", "ID": "IDN", "MY": "MYS", "SG": "SGP",
            "TH": "THA", "VN": "VNM", "PK": "PAK", "BD": "BGD",
            "NP": "NPL", "LK": "LKA", "MM": "MMR", "KH": "KHM",
            "LA": "LAO", "IL": "ISR", "SA": "SAU", "AE": "ARE",
            "TR": "TUR",
            
            # Africa
            "DZ": "DZA", "EG": "EGY", "MA": "MAR", "NG": "NGA",
            "KE": "KEN", "GH": "GHA", "ZA": "ZAF", "TN": "TUN",
            "ET": "ETH", "UG": "UGA", "TZ": "TZA", "SN": "SEN",
            "CM": "CMR",
            
            # Oceania
            "AU": "AUS", "NZ": "NZL", "FJ": "FJI", "PG": "PNG"
        }
        
        return country_code_map.get(country_code, country_code)
    
    def _get_country_for_currency(self, currency_code: str) -> str:
        """
        Get a default country for a currency code.
        
        Args:
            currency_code: Currency code (e.g., USD, EUR)
            
        Returns:
            The three-letter country code for a common country using this currency
        """
        # Map common currencies to representative countries
        currency_to_country = {
            "USD": "USA",
            "EUR": "ESP",  # Using Spain as default for Euro
            "GBP": "GBR",
            "CAD": "CAN",
            "AUD": "AUS",
            "JPY": "JPN",
            "CHF": "CHE",
            "INR": "IND",
            "SGD": "SGP",
            "SEK": "SWE",
            "NOK": "NOR",
            "DKK": "DNK",
            "HKD": "HKG",
            "CNY": "CHN",
            "MXN": "MEX",
            "BRL": "BRA",
            "ZAR": "ZAF",
            "RUB": "RUS",
            "TRY": "TUR",
            "PLN": "POL",
            "PHP": "PHL",
            "THB": "THA",
            "MYR": "MYS",
            "IDR": "IDN",
            "NZD": "NZL"
        }
        
        return currency_to_country.get(currency_code, "USA")
    
    def _normalize_delivery_method(self, method_type: str) -> str:
        """
        Normalize delivery method to consistent format.
        
        Args:
            method_type: Raw delivery method from API
            
        Returns:
            Normalized delivery method string
        """
        method_map = {
            "BANK_DEPOSIT": "bank deposit",
            "CASH_PICKUP": "cash pickup",
            "HOME_DELIVERY": "home delivery",
            "MOBILE_WALLET": "mobile wallet"
        }
        
        return method_map.get(method_type, method_type.lower())
    
    def get_supported_countries(self) -> List[Dict]:
        """
        Get a list of supported destination countries for Remitly.
        
        Returns:
            A list of country objects with code, name, and currency
        """
        # Return a comprehensive list of Remitly destinations
        return [
            # Latin America
            {"country_code": "MEX", "country_name": "Mexico", "currency_code": "MXN"},
            {"country_code": "COL", "country_name": "Colombia", "currency_code": "COP"},
            {"country_code": "GTM", "country_name": "Guatemala", "currency_code": "GTQ"},
            {"country_code": "SLV", "country_name": "El Salvador", "currency_code": "USD"},
            {"country_code": "DOM", "country_name": "Dominican Republic", "currency_code": "DOP"},
            {"country_code": "HND", "country_name": "Honduras", "currency_code": "HNL"},
            {"country_code": "PER", "country_name": "Peru", "currency_code": "PEN"},
            {"country_code": "ECU", "country_name": "Ecuador", "currency_code": "USD"},
            {"country_code": "BRA", "country_name": "Brazil", "currency_code": "BRL"},
            {"country_code": "CHL", "country_name": "Chile", "currency_code": "CLP"},
            {"country_code": "ARG", "country_name": "Argentina", "currency_code": "ARS"},
            {"country_code": "PAN", "country_name": "Panama", "currency_code": "PAB"},
            {"country_code": "CRI", "country_name": "Costa Rica", "currency_code": "CRC"},
            {"country_code": "BOL", "country_name": "Bolivia", "currency_code": "BOB"},
            {"country_code": "PRY", "country_name": "Paraguay", "currency_code": "PYG"},
            {"country_code": "URY", "country_name": "Uruguay", "currency_code": "UYU"},
            {"country_code": "VEN", "country_name": "Venezuela", "currency_code": "VES"},
            {"country_code": "NIC", "country_name": "Nicaragua", "currency_code": "NIO"},
            
            # Asia
            {"country_code": "PHL", "country_name": "Philippines", "currency_code": "PHP"},
            {"country_code": "IND", "country_name": "India", "currency_code": "INR"},
            {"country_code": "CHN", "country_name": "China", "currency_code": "CNY"},
            {"country_code": "VNM", "country_name": "Vietnam", "currency_code": "VND"},
            {"country_code": "THA", "country_name": "Thailand", "currency_code": "THB"},
            {"country_code": "IDN", "country_name": "Indonesia", "currency_code": "IDR"},
            {"country_code": "KOR", "country_name": "South Korea", "currency_code": "KRW"},
            {"country_code": "NPL", "country_name": "Nepal", "currency_code": "NPR"},
            {"country_code": "BGD", "country_name": "Bangladesh", "currency_code": "BDT"},
            {"country_code": "PAK", "country_name": "Pakistan", "currency_code": "PKR"},
            {"country_code": "JPN", "country_name": "Japan", "currency_code": "JPY"},
            {"country_code": "LKA", "country_name": "Sri Lanka", "currency_code": "LKR"},
            {"country_code": "MYS", "country_name": "Malaysia", "currency_code": "MYR"},
            {"country_code": "SGP", "country_name": "Singapore", "currency_code": "SGD"},
            {"country_code": "MMR", "country_name": "Myanmar", "currency_code": "MMK"},
            {"country_code": "KHM", "country_name": "Cambodia", "currency_code": "KHR"},
            {"country_code": "LAO", "country_name": "Laos", "currency_code": "LAK"},
            
            # Africa
            {"country_code": "DZA", "country_name": "Algeria", "currency_code": "DZD"},
            {"country_code": "EGY", "country_name": "Egypt", "currency_code": "EGP"},
            {"country_code": "MAR", "country_name": "Morocco", "currency_code": "MAD"},
            {"country_code": "GHA", "country_name": "Ghana", "currency_code": "GHS"},
            {"country_code": "KEN", "country_name": "Kenya", "currency_code": "KES"},
            {"country_code": "NGA", "country_name": "Nigeria", "currency_code": "NGN"},
            {"country_code": "SEN", "country_name": "Senegal", "currency_code": "XOF"},
            {"country_code": "TUN", "country_name": "Tunisia", "currency_code": "TND"},
            {"country_code": "ZAF", "country_name": "South Africa", "currency_code": "ZAR"},
            {"country_code": "UGA", "country_name": "Uganda", "currency_code": "UGX"},
            {"country_code": "TZA", "country_name": "Tanzania", "currency_code": "TZS"},
            {"country_code": "ETH", "country_name": "Ethiopia", "currency_code": "ETB"},
            
            # Europe
            {"country_code": "ESP", "country_name": "Spain", "currency_code": "EUR"},
            {"country_code": "GBR", "country_name": "United Kingdom", "currency_code": "GBP"},
            {"country_code": "DEU", "country_name": "Germany", "currency_code": "EUR"},
            {"country_code": "FRA", "country_name": "France", "currency_code": "EUR"},
            {"country_code": "ITA", "country_name": "Italy", "currency_code": "EUR"},
            {"country_code": "PRT", "country_name": "Portugal", "currency_code": "EUR"},
            {"country_code": "POL", "country_name": "Poland", "currency_code": "PLN"},
            {"country_code": "ROU", "country_name": "Romania", "currency_code": "RON"},
            {"country_code": "NLD", "country_name": "Netherlands", "currency_code": "EUR"},
            {"country_code": "BEL", "country_name": "Belgium", "currency_code": "EUR"},
            {"country_code": "GRC", "country_name": "Greece", "currency_code": "EUR"},
            {"country_code": "IRL", "country_name": "Ireland", "currency_code": "EUR"},
            {"country_code": "TUR", "country_name": "Turkey", "currency_code": "TRY"},
            {"country_code": "UKR", "country_name": "Ukraine", "currency_code": "UAH"},
            {"country_code": "RUS", "country_name": "Russia", "currency_code": "RUB"},
            
            # Middle East
            {"country_code": "ARE", "country_name": "United Arab Emirates", "currency_code": "AED"},
            {"country_code": "SAU", "country_name": "Saudi Arabia", "currency_code": "SAR"},
            {"country_code": "ISR", "country_name": "Israel", "currency_code": "ILS"},
            {"country_code": "JOR", "country_name": "Jordan", "currency_code": "JOD"},
            {"country_code": "LBN", "country_name": "Lebanon", "currency_code": "LBP"},
            
            # Oceania
            {"country_code": "AUS", "country_name": "Australia", "currency_code": "AUD"},
            {"country_code": "NZL", "country_name": "New Zealand", "currency_code": "NZD"},
            {"country_code": "FJI", "country_name": "Fiji", "currency_code": "FJD"}
        ]
    
    def get_source_countries(self) -> List[Dict]:
        """
        Get a list of supported source countries for Remitly.
        
        Returns:
            A list of country objects with code, name, and currency
        """
        # Return a list of source countries where Remitly operates
        return [
            {"country_code": "USA", "country_name": "United States", "currency_code": "USD"},
            {"country_code": "CAN", "country_name": "Canada", "currency_code": "CAD"},
            {"country_code": "GBR", "country_name": "United Kingdom", "currency_code": "GBP"},
            {"country_code": "ESP", "country_name": "Spain", "currency_code": "EUR"},
            {"country_code": "FRA", "country_name": "France", "currency_code": "EUR"},
            {"country_code": "DEU", "country_name": "Germany", "currency_code": "EUR"},
            {"country_code": "ITA", "country_name": "Italy", "currency_code": "EUR"},
            {"country_code": "IRL", "country_name": "Ireland", "currency_code": "EUR"},
            {"country_code": "AUT", "country_name": "Austria", "currency_code": "EUR"},
            {"country_code": "BEL", "country_name": "Belgium", "currency_code": "EUR"},
            {"country_code": "NLD", "country_name": "Netherlands", "currency_code": "EUR"},
            {"country_code": "PRT", "country_name": "Portugal", "currency_code": "EUR"},
            {"country_code": "FIN", "country_name": "Finland", "currency_code": "EUR"},
            {"country_code": "AUS", "country_name": "Australia", "currency_code": "AUD"},
            {"country_code": "NZL", "country_name": "New Zealand", "currency_code": "NZD"},
            {"country_code": "SGP", "country_name": "Singapore", "currency_code": "SGD"},
            {"country_code": "SWE", "country_name": "Sweden", "currency_code": "SEK"},
            {"country_code": "NOR", "country_name": "Norway", "currency_code": "NOK"},
            {"country_code": "DNK", "country_name": "Denmark", "currency_code": "DKK"}
        ]
    
    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 