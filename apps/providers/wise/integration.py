"""
Wise Money Transfer Integration (formerly TransferWise)

This module implements the integration with Wise (TransferWise) money transfer API.
Wise has various payment and payout methods:

PAYMENT METHODS (pay_in types):
------------------------------
- PISP: Open Banking / Instant Bank Transfer
- BANK_TRANSFER: Regular bank transfer
- DEBIT: Debit card
- CREDIT: Credit card
- INTERNATIONAL_DEBIT: International debit card
- INTERNATIONAL_CREDIT: International credit card
- SWIFT: SWIFT transfer
- BALANCE: Wise account balance

DELIVERY METHODS (pay_out types):
--------------------------------
- BANK_TRANSFER: Bank account deposit
- SWIFT: SWIFT transfer to bank account
- CASH_PICKUP: Cash pickup (where available)

Key API notes:
1. The quotes endpoint returns all available payment options
2. Each payment option has specific fees, exchange rates, and delivery times
3. Some options may be unavailable in specific corridors (country pairs)
4. The API is rate-limited and requires proper authentication
5. Exchange rates are updated frequently throughout the day

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
from typing import Dict, Optional, Any, List, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    WiseError,
    WiseAuthenticationError,
    WiseConnectionError,
    WiseValidationError,
    WiseRateLimitError
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


class WiseProvider(RemittanceProvider):
    """Integration with Wise (formerly TransferWise) money transfer service."""
    
    BASE_URL = "https://api.transferwise.com"
    QUOTES_ENDPOINT = "/v3/quotes/"
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30, user_agent: Optional[str] = None):
        """Initialize the Wise provider.
        
        Args:
            api_key: API key for authenticating with Wise
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        super().__init__(name="Wise", base_url=self.BASE_URL)
        self.logger = logger
        self.timeout = timeout
        
        self.user_agent = user_agent or os.environ.get(
            "WISE_DEFAULT_UA",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
        )
        
        self.api_key = api_key or os.environ.get("WISE_API_KEY")
        self._session = requests.Session()
        self.request_id = str(uuid.uuid4())
        self._initialize_session()
        
        self.logger.debug(f"Initialized WiseProvider with UA: {self.user_agent}")
        
    def _initialize_session(self) -> None:
        """Set up the HTTP session with default headers."""
        self.logger.debug("Initializing Wise session...")
        
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
            "X-Request-ID": self.request_id
        })
        
        if self.api_key:
            self._session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
            
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
        """Get the exchange rate information from Wise.
        
        Args:
            send_amount: Amount to send in source currency
            send_currency: Source currency code (e.g., 'USD')
            receive_country: Destination country code (e.g., 'MX')
            receive_currency: Optional destination currency code
            send_country: Source country code, defaults to 'US'
            
        Returns:
            Dictionary with exchange rate details or None if not available
        """
        # Map country codes to currency codes if receive_currency not specified
        country_to_currency = {
            "US": "USD",
            "GB": "GBP",
            "IN": "INR",
            "EG": "EGP",
            "MX": "MXN",
            "CA": "CAD",
            "AU": "AUD",
            "NZ": "NZD",
            "JP": "JPY",
            "CN": "CNY",
            "PH": "PHP",
            "SG": "SGD",
            "AE": "AED",
            "ZA": "ZAR",
            "BR": "BRL",
            "NG": "NGN",
            "KE": "KES"
        }
        
        if not receive_currency:
            receive_currency = country_to_currency.get(receive_country)
            if not receive_currency:
                self.logger.warning(f"No default currency for country {receive_country}")
                return None
                
        try:
            quote_data = self.get_quote(
                source_currency=send_currency,
                target_currency=receive_currency,
                source_amount=float(send_amount)
            )
            
            if not quote_data:
                self.logger.warning("Failed to get quote data from Wise API")
                return None
                
            best_option = self._find_best_payment_option(quote_data)
            
            if not best_option:
                self.logger.warning("No valid payment options found in quote")
                return None
                
            return {
                "provider": self.name,
                "timestamp": datetime.now(UTC).isoformat(),
                "send_amount": float(send_amount),
                "send_currency": send_currency,
                "receive_country": receive_country,
                "receive_currency": receive_currency,
                "exchange_rate": float(quote_data.get("rate", 0)),
                "transfer_fee": float(best_option.get("fee", {}).get("total", 0)),
                "service_name": f"{best_option.get('payIn', 'Unknown')} to {best_option.get('payOut', 'Unknown')}",
                "delivery_time": best_option.get("formattedEstimatedDelivery", "Unknown"),
                "receive_amount": float(best_option.get("targetAmount", 0))
            }
                
        except (WiseError, WiseConnectionError, WiseValidationError) as e:
            self.logger.error(f"Error getting Wise exchange rate: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in Wise exchange rate: {e}")
            return None
    
    def get_quote(self,
                 source_currency: str,
                 target_currency: str,
                 source_amount: Optional[float] = None,
                 target_amount: Optional[float] = None) -> Dict:
        """Get quote data from Wise API.
        
        Args:
            source_currency: Source currency code (e.g. 'USD')
            target_currency: Target currency code (e.g. 'EUR')
            source_amount: Amount to send in source currency
            target_amount: Amount to receive in target currency
            
        Returns:
            Dictionary with quote information
            
        Raises:
            WiseConnectionError: If connection to API fails
            WiseValidationError: If API rejects our request parameters
            WiseRateLimitError: If rate limits are exceeded
            WiseAuthenticationError: If authentication fails
        """
        if not source_amount and not target_amount:
            raise WiseValidationError(
                "Either source_amount or target_amount must be provided",
                error_code="MISSING_AMOUNT"
            )
            
        payload = {
            "sourceCurrency": source_currency,
            "targetCurrency": target_currency,
            "sourceAmount": source_amount,
            "targetAmount": target_amount
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        try:
            url = urljoin(self.BASE_URL, self.QUOTES_ENDPOINT)
            headers = dict(self._session.headers)
            
            # For quote endpoint, authentication is optional
            # For display purposes only, Authorization header can be omitted
            
            log_request_details(self.logger, "POST", url, headers, data=payload)
            
            response = self._session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            log_response_details(self.logger, response)
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get("paymentOptions") and not data.get("rate"):
                raise WiseValidationError(
                    "Invalid quote response format",
                    error_code="INVALID_RESPONSE",
                    details={"response": data}
                )
                
            return data
            
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            response_text = e.response.text if e.response else ""
            
            if status_code == 401:
                raise WiseAuthenticationError(
                    "Authentication failed with Wise API",
                    error_code="AUTH_FAILED",
                    details={"original_error": str(e), "response": response_text}
                )
            elif status_code == 400:
                raise WiseValidationError(
                    "Invalid request parameters",
                    error_code="INVALID_PARAMETERS",
                    details={"original_error": str(e), "response": response_text}
                )
            elif status_code == 429:
                raise WiseRateLimitError(
                    "Rate limit exceeded for Wise API",
                    error_code="RATE_LIMIT",
                    details={"original_error": str(e), "response": response_text, 
                            "retry_after": e.response.headers.get("Retry-After", "60")}
                )
            else:
                raise WiseConnectionError(
                    f"HTTP error from Wise API: {status_code}",
                    error_code="HTTP_ERROR",
                    details={"original_error": str(e), "response": response_text}
                )
                
        except requests.RequestException as e:
            raise WiseConnectionError(
                "Failed to connect to Wise API",
                error_code="CONNECTION_FAILED",
                details={"original_error": str(e)}
            )
    
    def get_supported_corridors(self) -> List[Dict]:
        """Get list of supported country corridors.
        
        This method fetches supported corridors from the Wise API.
        In a production implementation, this would call Wise's API
        to get the up-to-date list of supported corridors.
        
        Returns:
            List of dictionaries with source and target country information
        """
        # In a real implementation, this would call the Wise API
        # to get the list of supported corridors
        return [
            {"source_country": "US", "target_country": "MX"},
            {"source_country": "US", "target_country": "IN"},
            {"source_country": "US", "target_country": "PH"},
            {"source_country": "GB", "target_country": "IN"},
            {"source_country": "GB", "target_country": "US"},
            {"source_country": "CA", "target_country": "IN"}
        ]
    
    def get_payment_methods(self, source_country: str, target_country: str) -> List[str]:
        """Get available payment methods for a specific corridor.
        
        For production use, this should query the Wise API to get
        the available payment methods for the specified corridor.
        
        Args:
            source_country: Source country code (e.g., 'US')
            target_country: Target country code (e.g., 'MX')
            
        Returns:
            List of available payment method codes
        """
        # This would typically call the Wise API to get available payment methods
        # For now, return a static list based on common options
        common_methods = ["BANK_TRANSFER", "DEBIT", "CREDIT"]
        
        # Add country-specific methods
        if source_country == "GB":
            common_methods.append("PISP")  # Open Banking available in UK
        
        if source_country in ["US", "CA", "GB", "AU"]:
            common_methods.extend(["INTERNATIONAL_DEBIT", "INTERNATIONAL_CREDIT"])
            
        return common_methods
    
    def get_delivery_methods(self, source_country: str, target_country: str) -> List[str]:
        """Get available delivery methods for a specific corridor.
        
        For production use, this should query the Wise API to get
        the available delivery methods for the specified corridor.
        
        Args:
            source_country: Source country code (e.g., 'US')
            target_country: Target country code (e.g., 'MX')
            
        Returns:
            List of available delivery method codes
        """
        # This would typically call the Wise API to get available delivery methods
        # For now, return a static list based on common options
        methods = ["BANK_TRANSFER"]
        
        # Add cash pickup for countries where it's commonly available
        if target_country in ["MX", "PH", "IN", "CO", "VN"]:
            methods.append("CASH_PICKUP")
            
        # Add SWIFT for international transfers to certain countries
        if target_country not in ["US", "GB", "EU"]:
            methods.append("SWIFT")
            
        return methods
    
    def _find_best_payment_option(self, quote_data: Dict) -> Optional[Dict]:
        """Find the best payment option from quote data.
        
        The "best" option is currently defined as the one with lowest total fee.
        
        Args:
            quote_data: Quote data from Wise API
            
        Returns:
            Dictionary with best payment option or None if no valid options
        """
        payment_options = quote_data.get("paymentOptions", [])
        
        # If the API response uses different field structure
        if not payment_options:
            payment_options = quote_data.get("options", [])
            
        if not payment_options:
            return None
            
        # Filter out disabled options
        valid_options = [opt for opt in payment_options if not opt.get("disabled", False)]
        
        if not valid_options:
            return None
            
        # Sort by total fee (lowest first)
        sorted_options = sorted(
            valid_options,
            key=lambda x: float(x.get("fee", {}).get("total", float("inf")))
        )
        
        return sorted_options[0] if sorted_options else None
    
    def __enter__(self):
        """Context manager entry.
        
        Returns:
            Self for use in with statement
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit.
        
        Closes the session and cleans up resources.
        """
        if self._session:
            self._session.close() 