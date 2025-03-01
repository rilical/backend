"""
Pangea Money Transfer Integration

This module implements the integration with Pangea Money Transfer API.
Pangea offers money transfer services to various countries with competitive
rates and multiple delivery methods.

The primary API endpoint used is the FeesAndFX endpoint which provides:
- Exchange rates
- Fee information
- Delivery method options
- Estimated delivery times

The API format for the exchange parameter is:
{sourceCurrency}-{targetCurrency}|{sourceCountry}-{targetCountry}
For example: USD-MXN|US-MX for US Dollar to Mexican Peso from US to Mexico
"""

import json
import logging
import os
import pprint
from datetime import datetime, UTC
from decimal import Decimal
from typing import Dict, Optional, Any, List, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    PangeaError,
    PangeaAuthenticationError,
    PangeaConnectionError,
    PangeaValidationError,
    PangeaRateLimitError
)

logger = logging.getLogger(__name__)


def log_request_details(logger, method: str, url: str, headers: Dict,
                      params: Dict = None, data: Dict = None):
    """Log details of outgoing API requests."""
    logger.debug("\n" + "="*80 + f"\nOUTGOING REQUEST DETAILS:\n{'='*80}")
    logger.debug(f"Method: {method}")
    logger.debug(f"URL: {url}")

    masked_headers = headers.copy()
    sensitive = ['Authorization', 'Cookie']
    for key in sensitive:
        if key in masked_headers:
            masked_headers[key] = '***MASKED***'

    logger.debug("\nHeaders:")
    logger.debug(pprint.pformat(masked_headers))

    if params:
        logger.debug("\nQuery Params:")
        logger.debug(pprint.pformat(params))
    if data:
        logger.debug("\nRequest Body:")
        logger.debug(pprint.pformat(data))


def log_response_details(logger, response):
    """Log details of API responses."""
    logger.debug("\n" + "="*80 + f"\nRESPONSE DETAILS:\n{'='*80}")
    logger.debug(f"Status Code: {response.status_code}")
    logger.debug(f"Reason: {response.reason}")
    logger.debug("\nResponse Headers:")
    logger.debug(pprint.pformat(dict(response.headers)))

    try:
        body = response.json()
        logger.debug("\nJSON Response Body:")
        logger.debug(pprint.pformat(body))
    except ValueError:
        body = response.text
        content_type = response.headers.get('content-type', '').lower()
        if 'html' in content_type:
            logger.debug("\nHTML Response (truncated):")
            logger.debug(body[:500] + '...' if len(body) > 500 else body)
        else:
            logger.debug("\nPlain Text Response:")
            logger.debug(body[:1000] + '...' if len(body) > 1000 else body)

    logger.debug("="*80)


class PangeaProvider(RemittanceProvider):
    """Integration with Pangea Money Transfer service."""
    
    BASE_URL = "https://api.gopangea.com"
    FEES_AND_FX_ENDPOINT = "/api/v5/FeesAndFX"
    
    # Mapping of country codes to currency codes
    COUNTRY_TO_CURRENCY = {
        "US": "USD",  # United States - US Dollar
        "MX": "MXN",  # Mexico - Mexican Peso
        "CO": "COP",  # Colombia - Colombian Peso
        "GT": "GTQ",  # Guatemala - Guatemalan Quetzal
        "DO": "DOP",  # Dominican Republic - Dominican Peso
        "SV": "USD",  # El Salvador - US Dollar
        "PE": "PEN",  # Peru - Peruvian Sol
        "EC": "USD",  # Ecuador - US Dollar
        "BR": "BRL",  # Brazil - Brazilian Real
        "BO": "BOB",  # Bolivia - Boliviano
        "PY": "PYG",  # Paraguay - Paraguayan Guaraní
        "NI": "NIO",  # Nicaragua - Nicaraguan Córdoba
        "HN": "HNL",  # Honduras - Honduran Lempira
        "PH": "PHP",  # Philippines - Philippine Peso
        "IN": "INR",  # India - Indian Rupee
        "VN": "VND",  # Vietnam - Vietnamese Dong
        "CN": "CNY",  # China - Chinese Yuan
        "ID": "IDR",  # Indonesia - Indonesian Rupiah
        "KR": "KRW",  # South Korea - South Korean Won
        "ES": "EUR",  # Spain - Euro
        "FR": "EUR",  # France - Euro
        "DE": "EUR",  # Germany - Euro
        "IT": "EUR",  # Italy - Euro
        "GB": "GBP",  # United Kingdom - British Pound
        "CA": "CAD",  # Canada - Canadian Dollar
        "AU": "AUD",  # Australia - Australian Dollar
        "JP": "JPY",  # Japan - Japanese Yen
    }
    
    # Supported corridors
    SUPPORTED_CORRIDORS = [
        ("US", "MX"),  # USA to Mexico
        ("US", "CO"),  # USA to Colombia
        ("US", "GT"),  # USA to Guatemala
        ("US", "DO"),  # USA to Dominican Republic
        ("US", "SV"),  # USA to El Salvador
        ("US", "PE"),  # USA to Peru
        ("US", "EC"),  # USA to Ecuador
        ("US", "BR"),  # USA to Brazil
        ("US", "BO"),  # USA to Bolivia
        ("US", "PY"),  # USA to Paraguay
        ("US", "NI"),  # USA to Nicaragua
        ("US", "HN"),  # USA to Honduras
        ("US", "PH"),  # USA to Philippines
        ("US", "IN"),  # USA to India
        ("CA", "MX"),  # Canada to Mexico
        ("CA", "CO"),  # Canada to Colombia
        ("CA", "IN"),  # Canada to India
        ("CA", "PH"),  # Canada to Philippines
    ]
    
    def __init__(self, timeout: int = 30, user_agent: Optional[str] = None):
        """Initialize the Pangea provider.
        
        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        super().__init__(name="Pangea", base_url=self.BASE_URL)
        self.logger = logger
        self.timeout = timeout
        
        self.user_agent = user_agent or os.environ.get(
            "PANGEA_DEFAULT_UA",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
        )
        
        self._session = requests.Session()
        self._initialize_session()
        
        self.logger.debug(f"Initialized PangeaProvider with UA: {self.user_agent}")
        
    def _initialize_session(self) -> None:
        """Set up the HTTP session with default headers."""
        self.logger.debug("Initializing Pangea session...")
        
        self._session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": self.user_agent,
            "Origin": "https://pangeamoneytransfer.com",
            "Referer": "https://pangeamoneytransfer.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive"
        })
        
        # Print the headers for debug
        self.logger.debug(f"Session headers: {self._session.headers}")
            
        # Add retry mechanism for better reliability
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
    
    def get_exchange_rate(self,
                         send_amount: Decimal,
                         send_currency: str,
                         receive_country: str,
                         receive_currency: Optional[str] = None,
                         send_country: str = "US") -> Optional[Dict]:
        """Get the exchange rate information from Pangea.
        
        Args:
            send_amount: Amount to send in source currency
            send_currency: Source currency code (e.g., 'USD')
            receive_country: Destination country code (e.g., 'MX')
            receive_currency: Optional destination currency code
            send_country: Source country code, defaults to 'US'
            
        Returns:
            Dictionary with exchange rate details or None if not available
        """
        # If receive_currency not specified, use country mapping
        if not receive_currency:
            receive_currency = self.COUNTRY_TO_CURRENCY.get(receive_country)
            if not receive_currency:
                self.logger.warning(f"No default currency for country {receive_country}")
                return None
        
        # Check for valid amount
        if not send_amount or float(send_amount) <= 0:
            self.logger.warning(f"Invalid send amount: {send_amount}")
            return None
                
        try:
            # Get fees and exchange rate data
            fees_data = self.get_fees_and_fx(
                source_country=send_country,
                target_country=receive_country,
                source_currency=send_currency,
                target_currency=receive_currency
            )
            
            if not fees_data:
                self.logger.warning("Failed to get fees and FX data from Pangea API")
                return None
            
            # Extract from API response based on frontend code
            exchange_rates = fees_data.get("ExchangeRates", [])
            if not exchange_rates:
                self.logger.warning("No exchange rates found in response")
                return None
                
            # Find the regular exchange rate (similar to frontend logic)
            regular_rate = next((rate for rate in exchange_rates if rate.get("ExchangeRateType") == "Regular"), None)
            if not regular_rate:
                self.logger.warning("No Regular exchange rate type found")
                return None
                
            # Get fee information
            fees = fees_data.get("Fees", {})
            card_fees = fees.get("Card", [])
            if not card_fees:
                self.logger.warning("No fee information found")
                return None
                
            # Get the first fee (default)
            fee = card_fees[0].get("Fee", 0) if card_fees else 0
                
            # Calculate receive amount based on exchange rate
            exchange_rate = float(regular_rate.get("Rate", 0))
            
            if exchange_rate <= 0:
                self.logger.warning("Invalid exchange rate (zero or negative)")
                return None
                
            # Calculate the amount after fees
            send_amount_after_fees = float(send_amount) - float(fee)
            receive_amount = send_amount_after_fees * exchange_rate
            
            # Get delivery information from first payout method
            delivery_time = "Unknown"
            
            return {
                "provider": self.name,
                "timestamp": datetime.now(UTC).isoformat(),
                "send_amount": float(send_amount),
                "send_currency": send_currency,
                "receive_country": receive_country,
                "receive_currency": receive_currency,
                "exchange_rate": exchange_rate,
                "transfer_fee": float(fee),
                "service_name": "Pangea Money Transfer",
                "delivery_time": delivery_time,
                "receive_amount": receive_amount
            }
                
        except (PangeaError, PangeaConnectionError, PangeaValidationError) as e:
            self.logger.error(f"Error getting Pangea exchange rate: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in Pangea exchange rate: {e}")
            return None
    
    def get_fees_and_fx(self,
                       source_country: str,
                       target_country: str,
                       source_currency: str,
                       target_currency: str) -> Dict:
        """Get fees and exchange rate data from Pangea API.
        
        Args:
            source_country: Source country code (e.g., 'US')
            target_country: Target country code (e.g., 'MX')
            source_currency: Source currency code (e.g., 'USD')
            target_currency: Target currency code (e.g., 'MXN')
            
        Returns:
            Dictionary with fees and exchange rate information
            
        Raises:
            PangeaConnectionError: If connection to API fails
            PangeaValidationError: If API rejects our request parameters
            PangeaRateLimitError: If rate limits are exceeded
        """            
        try:
            # Construct the exchange parameter: {sourceCurrency}-{targetCurrency}|{sourceCountry}-{targetCountry}
            exchange_param = f"{source_currency}-{target_currency}|{source_country}-{target_country}"
            
            url = urljoin(self.BASE_URL, self.FEES_AND_FX_ENDPOINT)
            params = {
                "exchange": exchange_param,
                "senderId": ""  # Empty sender ID as shown in the curl examples
            }
            
            self.logger.info(f"Making request to Pangea API: GET {url}")
            self.logger.info(f"Query parameters: {params}")
            
            log_request_details(self.logger, "GET", url, dict(self._session.headers), params=params)
            
            response = self._session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            self.logger.info(f"Received response from Pangea API: Status {response.status_code}")
            
            log_response_details(self.logger, response)
            
            # Let's log the raw response text to debug
            self.logger.debug(f"Raw response text: {response.text[:1000]}")
            
            # Handle non-successful status codes without raising immediately
            if response.status_code != 200:
                self.logger.warning(f"Non-200 status code from Pangea API: {response.status_code}")
                
                # Try to parse error message from response
                try:
                    error_json = response.json()
                    self.logger.warning(f"Error response JSON: {error_json}")
                except Exception:
                    self.logger.warning(f"Could not parse error JSON, raw text: {response.text[:500]}")
                
                response.raise_for_status()  # Now raise the exception
            
            # Try to parse the response as JSON
            try:
                data = response.json()
                self.logger.debug(f"Parsed JSON response: {data}")
            except ValueError as e:
                self.logger.error(f"Failed to parse response as JSON: {e}")
                self.logger.error(f"Raw response text: {response.text[:500]}")
                raise PangeaValidationError(
                    "Invalid JSON response from Pangea API",
                    error_code="INVALID_JSON",
                    details={"response_text": response.text[:500]}
                )
            
            # Check for required fields in the response
            if not data:
                self.logger.warning("Empty response data from Pangea API")
                raise PangeaValidationError(
                    "Empty response from Pangea API",
                    error_code="EMPTY_RESPONSE",
                    details={"response": data}
                )
            
            # Check for ExchangeRates field instead of exchangeRate
            if "ExchangeRates" not in data or not data["ExchangeRates"]:
                self.logger.warning(f"Response missing ExchangeRates field: {data}")
                raise PangeaValidationError(
                    "Invalid response format or no exchange rate data",
                    error_code="INVALID_RESPONSE",
                    details={"response": data}
                )
                
            return data
            
        except requests.HTTPError as e:
            status_code = getattr(e.response, 'status_code', 0)
            response_text = getattr(e.response, 'text', "")
            
            self.logger.error(f"HTTP error from Pangea API: {status_code}")
            self.logger.error(f"Response text: {response_text[:500]}")
            
            if status_code == 401:
                raise PangeaAuthenticationError(
                    "Authentication failed with Pangea API",
                    error_code="AUTH_FAILED",
                    details={"original_error": str(e), "response": response_text}
                )
            elif status_code == 400:
                raise PangeaValidationError(
                    "Invalid request parameters",
                    error_code="INVALID_PARAMETERS",
                    details={"original_error": str(e), "response": response_text}
                )
            elif status_code == 429:
                raise PangeaRateLimitError(
                    "Rate limit exceeded for Pangea API",
                    error_code="RATE_LIMIT",
                    details={"original_error": str(e), "response": response_text}
                )
            else:
                raise PangeaConnectionError(
                    f"HTTP error from Pangea API: {status_code}",
                    error_code="HTTP_ERROR",
                    details={"original_error": str(e), "response": response_text}
                )
                
        except requests.RequestException as e:
            self.logger.error(f"Request exception when connecting to Pangea API: {e}")
            raise PangeaConnectionError(
                "Failed to connect to Pangea API",
                error_code="CONNECTION_FAILED",
                details={"original_error": str(e)}
            )
        except Exception as e:
            self.logger.error(f"Unexpected error in Pangea API request: {e}")
            raise PangeaError(
                f"Unexpected error: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                details={"original_error": str(e)}
            )
    
    def get_supported_corridors(self) -> List[Dict]:
        """Get list of supported country corridors.
        
        Returns:
            List of dictionaries with source and target country information
        """
        return [
            {"source_country": src, "target_country": tgt}
            for src, tgt in self.SUPPORTED_CORRIDORS
        ]
    
    def get_payment_methods(self, source_country: str, target_country: str) -> List[str]:
        """Get available payment methods for a specific corridor.
        
        Args:
            source_country: Source country code (e.g., 'US')
            target_country: Target country code (e.g., 'MX')
            
        Returns:
            List of available payment method codes
        """
        # Pangea typically supports these payment methods
        common_methods = ["BANK_TRANSFER", "DEBIT_CARD", "CREDIT_CARD"]
        
        # For specific corridors, certain methods may be available/unavailable
        # This would require calling their API with specific corridor info
        # For now, we return the common methods
        return common_methods
    
    def get_delivery_methods(self, source_country: str, target_country: str) -> List[str]:
        """Get available delivery methods for a specific corridor.
        
        Args:
            source_country: Source country code (e.g., 'US')
            target_country: Target country code (e.g., 'MX')
            
        Returns:
            List of available delivery method codes
        """
        # Basic static implementation, in production should fetch from API
        # Different corridors support different delivery methods
        methods = ["BANK_DEPOSIT"]
        
        # Add cash pickup for countries where it's commonly available
        if target_country in ["MX", "CO", "GT", "DO", "PE", "EC", "BR", "PH"]:
            methods.append("CASH_PICKUP")
            
        # Add mobile money for countries where it's available
        if target_country in ["PH", "IN"]:
            methods.append("MOBILE_MONEY")
            
        return methods
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._session:
            self._session.close() 