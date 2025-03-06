"""
TransferGo Money Transfer Integration

This module implements the integration with TransferGo, a service for international
money transfers. TransferGo offers competitive exchange rates with various
payment and delivery options.

PAYMENT METHODS:
---------------------------------
- BANK_ACCOUNT: Bank account transfer (SEPA, etc.)
- CARD: Debit/Credit card payment
- WALLET: Digital wallet payment

DELIVERY METHODS:
---------------------------------
- BANK_DEPOSIT: Direct bank deposit
- CASH_PICKUP: Cash pickup at select locations
- MOBILE_WALLET: Mobile wallet transfer (in select countries)

Important API notes:
1. TransferGo's API uses a booking token system for quotes
2. Exchange rates and fees vary by corridor and payment/delivery method
3. The API returns multiple options with different speed/fee combinations
4. The default option is marked with isDefault=true in the response
"""

import json
import logging
import time
import uuid
from decimal import Decimal
from typing import Dict, Optional, Any, List, Union, Tuple

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from apps.providers.transferGo.exceptions import (
    TransferGoError,
    TransferGoAuthenticationError,
    TransferGoConnectionError,
    TransferGoValidationError,
    TransferGoRateLimitError
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

class TransferGoProvider(RemittanceProvider):
    """
    Integration with TransferGo's booking quotes (live rates) endpoint.
    
    Example usage:
        provider = TransferGoProvider()
        result = provider.get_exchange_rate(
            send_amount=Decimal("500.00"),
            send_currency="EUR",
            receive_country="UA",
            receive_currency="UAH"
        )
    """

    BASE_URL = "https://my.transfergo.com"
    
    # Delivery method mapping
    DELIVERY_METHODS = {
        "BANK_TRANSFER": "Bank Deposit",
        "CASH_PICKUP": "Cash Pickup",
        "MOBILE_WALLET": "Mobile Wallet",
    }
    
    # Payment method mapping
    PAYMENT_METHODS = {
        "BANK_TRANSFER": "Bank Transfer",
        "CARD": "Card Payment",
        "WALLET": "Digital Wallet"
    }
    
    # Country to currency mapping (partial, common currencies)
    COUNTRY_CURRENCIES = {
        # Europe
        "GB": "GBP", "DE": "EUR", "FR": "EUR", "ES": "EUR", "IT": "EUR", 
        "NL": "EUR", "BE": "EUR", "AT": "EUR", "IE": "EUR", "FI": "EUR",
        "LV": "EUR", "LT": "EUR", "EE": "EUR", "PT": "EUR", "GR": "EUR", 
        "SK": "EUR", "SI": "EUR", "LU": "EUR", "MT": "EUR", "CY": "EUR",
        "PL": "PLN", "RO": "RON", "CZ": "CZK", "HU": "HUF", "SE": "SEK", 
        "DK": "DKK", "NO": "NOK", "CH": "CHF", "BG": "BGN", "HR": "HRK",
        
        # Americas
        "US": "USD", "CA": "CAD", "MX": "MXN", "BR": "BRL", "CO": "COP", 
        "AR": "ARS", "CL": "CLP", "PE": "PEN", "UY": "UYU", "DO": "DOP",
        "JM": "JMD", "BS": "BSD", "BB": "BBD", "TT": "TTD",
        
        # Asia Pacific
        "AU": "AUD", "NZ": "NZD", "JP": "JPY", "SG": "SGD", "CN": "CNY", 
        "HK": "HKD", "KR": "KRW", "TW": "TWD", "MY": "MYR", "TH": "THB", 
        "VN": "VND", "ID": "IDR", "PH": "PHP", "IN": "INR", "PK": "PKR", 
        "BD": "BDT", "LK": "LKR", "NP": "NPR",
        
        # Middle East
        "AE": "AED", "SA": "SAR", "QA": "QAR", "BH": "BHD", "KW": "KWD", 
        "OM": "OMR", "IL": "ILS", "JO": "JOD", "LB": "LBP", "TR": "TRY",
        
        # Africa
        "ZA": "ZAR", "NG": "NGN", "KE": "KES", "EG": "EGP", "MA": "MAD", 
        "TN": "TND", "GH": "GHS", "TZ": "TZS", "UG": "UGX", "ET": "ETB",
        
        # Eastern Europe & Central Asia
        "UA": "UAH", "RU": "RUB", "KZ": "KZT", "GE": "GEL", "BY": "BYN", 
        "AZ": "AZN", "MD": "MDL", "AL": "ALL", "BA": "BAM", "RS": "RSD",
        "ME": "EUR", "MK": "MKD", "AM": "AMD", "UZ": "UZS", "TJ": "TJS"
    }
    
    # Multi-currency countries (those that can use both local currency and USD/EUR)
    MULTI_CURRENCY_COUNTRIES = {
        "UA": ["UAH", "USD", "EUR"],
        "IN": ["INR", "USD", "EUR"], 
        "PH": ["PHP", "USD"],
        "NG": ["NGN", "USD", "EUR"],
        "KE": ["KES", "USD", "EUR"],
        "GH": ["GHS", "USD", "EUR"],
        "TZ": ["TZS", "USD", "EUR"],
        "UG": ["UGX", "USD", "EUR"],
        "LK": ["LKR", "USD"],
        "NP": ["NPR", "USD", "EUR"]
    }

    # Example default User-Agent (Safari on macOS)
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.3 Safari/605.1.15"
    )

    def __init__(self, user_agent: Optional[str] = None, timeout: int = 30):
        super().__init__(name="TransferGo", base_url=self.BASE_URL)
        self.timeout = timeout
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT

        # Initialize the requests session
        self.session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Configure default headers, cookies, and retry logic."""
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "*/*",  # TransferGo's endpoint returns JSON by default
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Origin": "https://www.transfergo.com",
            "Referer": "https://www.transfergo.com/"
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
        retry_auth: bool = True,
        max_retries: int = 2
    ) -> Dict:
        """
        Make a request to the TransferGo API with proper error handling.
        
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
                        timeout=self.timeout
                    )
                else:  # POST
                    response = self.session.post(
                        url=url,
                        json=data,
                        params=params,
                        timeout=self.timeout
                    )
                
                # Log response status
                logger.debug(f"TransferGo API response status: {response.status_code}")
                
                # Check for common error status codes
                if response.status_code in (401, 403):
                    if retry_auth and retry_count < max_retries:
                        logger.warning(f"Authentication failed, refreshing session and retrying (attempt {retry_count + 1}/{max_retries})")
                        self._setup_session()
                        time.sleep(1)  # Add delay between retries
                        retry_count += 1
                        continue
                    raise TransferGoAuthenticationError("Authentication failed")
                
                if response.status_code == 429:
                    # With rate limits, we should wait longer before retrying
                    if retry_count < max_retries:
                        wait_time = 5 * (retry_count + 1)  # Progressive backoff
                        logger.warning(f"Rate limit exceeded, waiting {wait_time} seconds before retry")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    raise TransferGoRateLimitError("Rate limit exceeded")
                    
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", "Unknown API error")
                        raise TransferGoError(f"API error: {error_message}")
                    except (ValueError, KeyError):
                        raise TransferGoError(f"API error: {response.status_code}")
                
                # Parse and return response
                try:
                    return response.json()
                except ValueError:
                    # If the response is empty but status is 200, return empty dict
                    if response.status_code == 200 and not response.text.strip():
                        return {}
                    raise TransferGoError("Invalid JSON response from API")
                    
            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")
                
                # Retry network errors
                if retry_count < max_retries:
                    logger.warning(f"Connection error, retrying (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(2)
                    retry_count += 1
                    continue
                    
                raise TransferGoConnectionError(f"Connection error: {e}")
        
        # This should not be reached, but just in case
        raise TransferGoError("Maximum retries exceeded")

    def get_quote(
        self,
        from_country: str,
        to_country: str,
        from_currency: str,
        to_currency: str,
        amount: Decimal,
        calc_base: str = "sendAmount",  # or "receiveAmount"
        business: int = 0
    ) -> Dict[str, Any]:
        """
        Fetch a TransferGo quote for the given corridor and amount.

        Args:
            from_country: e.g., "DE" (Germany)
            to_country: e.g., "UA" (Ukraine)
            from_currency: e.g., "EUR"
            to_currency: e.g., "UAH"
            amount: The numeric amount (Decimal)
            calc_base: "sendAmount" or "receiveAmount"
            business: 0 = personal / 1 = business

        Returns:
            A dictionary with parsed rate data from TransferGo.
        """
        url = f"{self.base_url}/api/booking/quotes"
        params = {
            "fromCurrencyCode": from_currency,
            "toCurrencyCode": to_currency,
            "fromCountryCode": from_country,
            "toCountryCode": to_country,
            "amount": str(amount),
            "calculationBase": calc_base,
            "business": str(business),
        }

        logger.debug(f"[TransferGo] Requesting quotes: {url} with {params}")
        
        try:
            # Make the API request
            data = self._make_api_request(
                method="GET",
                url=url,
                params=params
            )
            
            logger.debug(f"[TransferGo] Raw JSON response:\n{json.dumps(data, indent=2)}")

            # Extract all options and identify the default option
            options_list = data.get("options", [])
            
            # Identify the default option if any
            default_option = None
            for opt in options_list:
                if opt.get("isDefault", False):
                    default_option = opt
                    break
            
            # Build result structure
            result = {
                "provider": "TransferGo",
                "options": options_list,
                "raw_json": data
            }
            
            # Add default option information if available
            if default_option:
                result["default_fee"] = float(default_option["fee"]["value"])
                result["default_exchange_rate"] = float(default_option["rate"]["value"])
                result["default_send_amount"] = float(default_option["sendingAmount"]["value"])
                result["default_receive_amount"] = float(default_option["receivingAmount"]["value"])
                result["booking_token"] = default_option["bookingToken"]
                
                # Try to extract payment and delivery methods if available
                payment_method = default_option.get("payInMethod", {}).get("type", "")
                delivery_method = default_option.get("payOutMethod", {}).get("type", "")
                
                result["payment_method"] = self.PAYMENT_METHODS.get(payment_method, payment_method)
                result["delivery_method"] = self.DELIVERY_METHODS.get(delivery_method, delivery_method)
                
                # Try to extract delivery time if available
                delivery_time = default_option.get("delivery", {}).get("time", "")
                result["delivery_time"] = delivery_time
                
                # Try to extract delivery time in minutes if possible
                delivery_time_minutes = self._parse_delivery_time(delivery_time)
                if delivery_time_minutes:
                    result["delivery_time_minutes"] = delivery_time_minutes
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting quote from TransferGo: {str(e)}")
            raise

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str = "USD",
        receive_country: str = None,
        receive_currency: str = None,
        delivery_method: str = None,
        payment_method: str = None,
        preferred_receive_currency: str = None  # New parameter to specify preferred currency if multiple are available
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
            preferred_receive_currency: Optional preferred currency for countries with multiple supported currencies.
            
        Returns:
            Dict containing exchange rate details.
        """
        if not receive_country and not receive_currency:
            raise TransferGoValidationError("Either receive_country or receive_currency is required")
        
        # Map source currency to typical sending country
        from_country = self._get_country_for_currency(send_currency)
        
        # If receive_currency is not provided but country is, try to determine currency
        # If the country supports multiple currencies, use the preferred one if specified
        if not receive_currency and receive_country:
            if preferred_receive_currency and receive_country in self.MULTI_CURRENCY_COUNTRIES:
                if preferred_receive_currency in self.MULTI_CURRENCY_COUNTRIES[receive_country]:
                    receive_currency = preferred_receive_currency
                else:
                    # If preferred currency is not supported, fall back to default
                    receive_currency = self._get_currency_for_country(receive_country)
            else:
                receive_currency = self._get_currency_for_country(receive_country)
        
        # If receive_country is not provided but currency is, try to determine country
        if not receive_country and receive_currency:
            receive_country = self._get_country_for_currency(receive_currency)
        
        try:
            # Get quote from TransferGo
            quote_result = self.get_quote(
                from_country=from_country,
                to_country=receive_country,
                from_currency=send_currency,
                to_currency=receive_currency,
                amount=send_amount,
                calc_base="sendAmount"
            )
            
            # If we have a default option, use that for standardized output
            if "default_exchange_rate" in quote_result:
                # Build standardized result
                result = ExchangeRateResult(
                    provider_id="TransferGo",
                    source_currency=send_currency,
                    source_amount=float(send_amount),
                    destination_currency=receive_currency,
                    destination_amount=quote_result["default_receive_amount"],
                    exchange_rate=quote_result["default_exchange_rate"],
                    fee=quote_result["default_fee"],
                    delivery_method=quote_result.get("delivery_method", "bank deposit"),
                    delivery_time_minutes=quote_result.get("delivery_time_minutes"),
                    corridor=f"{from_country}-{receive_country}",
                    payment_method=quote_result.get("payment_method", "Bank Transfer"),
                    details={
                        "booking_token": quote_result.get("booking_token"),
                        "all_options": quote_result.get("options", []),
                        "raw_response": quote_result.get("raw_json", {})
                    }
                )
                
                return result.to_dict()
            else:
                # If no default option, return an error or fallback
                raise TransferGoError("No default rate option found in response")
                
        except Exception as e:
            logger.error(f"Error getting exchange rate from TransferGo: {str(e)}")
            
            # Return fallback data if API call failed
            return self._get_fallback_exchange_rate(
                float(send_amount),
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
        
        # Comprehensive mock rates for common currencies (against EUR as base)
        eur_rates = {
            # Base currency
            "EUR": 1.0,
            
            # Major currencies
            "USD": 1.08, "GBP": 0.85, "CHF": 0.96, "JPY": 161.5, "CAD": 1.46,
            "AUD": 1.64, "NZD": 1.75, "SGD": 1.45, "HKD": 8.43, "CNY": 7.79,
            
            # European currencies
            "PLN": 4.32, "CZK": 25.23, "SEK": 11.31, "NOK": 11.29, "DKK": 7.46,
            "HUF": 386.55, "RON": 4.97, "BGN": 1.96, "HRK": 7.51, "RSD": 117.16,
            "ALL": 102.50, "BAM": 1.96, "MKD": 61.70,
            
            # Eastern Europe / Central Asia
            "UAH": 42.50, "RUB": 98.50, "TRY": 34.37, "GEL": 3.05, "KZT": 480.20,
            "BYN": 3.50, "AZN": 1.83, "MDL": 19.15, "AMD": 419.50, "UZS": 13550.0,
            "TJS": 11.85,
            
            # Americas
            "MXN": 20.40, "BRL": 5.90, "ARS": 956.50, "COP": 4233.0, "CLP": 997.0,
            "PEN": 4.05, "UYU": 42.30, "DOP": 63.20, "JMD": 168.50, "BSD": 1.08,
            "BBD": 2.16, "TTD": 7.32,
            
            # Asia
            "INR": 90.11, "PKR": 300.5, "BDT": 126.5, "LKR": 338.0, "NPR": 144.0,
            "THB": 39.65, "IDR": 17550.0, "MYR": 5.07, "PHP": 62.50, "KRW": 1480.0,
            "VND": 27150.0, "TWD": 34.75,
            
            # Middle East
            "AED": 3.97, "SAR": 4.05, "QAR": 3.94, "BHD": 0.41, "KWD": 0.33,
            "OMR": 0.42, "ILS": 3.98, "JOD": 0.77, "LBP": 96750.0,
            
            # Africa
            "ZAR": 19.90, "EGP": 51.0, "MAD": 10.89, "TND": 3.38, "NGN": 1670.0,
            "KES": 140.0, "GHS": 16.35, "TZS": 2850.0, "UGX": 4125.0, "ETB": 61.25
        }
        
        # Calculate exchange rate based on source and destination currencies
        # First convert source currency to EUR equivalent
        if send_currency == "EUR":
            eur_amount = send_amount
        else:
            # If source is not EUR, convert to EUR first (using inverse rate)
            source_eur_rate = eur_rates.get(send_currency, 1.0)
            eur_amount = send_amount / source_eur_rate if source_eur_rate != 0 else send_amount
        
        # Then convert from EUR to destination currency
        dest_eur_rate = eur_rates.get(receive_currency, 10.0)
        exchange_rate = dest_eur_rate
        
        # If source is not EUR, we need to calculate the direct exchange rate
        if send_currency != "EUR":
            source_eur_rate = eur_rates.get(send_currency, 1.0)
            if source_eur_rate > 0:
                exchange_rate = dest_eur_rate / source_eur_rate
        
        # Calculate receive amount based on the exchange rate
        receive_amount = send_amount * exchange_rate
        
        # Define standard fees based on amount and currency
        fee = 0.0
        if send_currency == "EUR":
            if send_amount >= 1000:
                fee = 2.99
            elif send_amount >= 500:
                fee = 1.99
            elif send_amount >= 100:
                fee = 0.99
        elif send_currency == "USD":
            if send_amount >= 1000:
                fee = 3.49
            elif send_amount >= 500:
                fee = 2.49
            elif send_amount >= 100:
                fee = 1.49
        elif send_currency == "GBP":
            if send_amount >= 800:
                fee = 2.49
            elif send_amount >= 400:
                fee = 1.99
            elif send_amount >= 100:
                fee = 0.99
        else:
            # Default fee structure for other currencies
            if send_amount >= 1000:
                fee = 2.99
            elif send_amount >= 500:
                fee = 1.99
            elif send_amount >= 100:
                fee = 0.99
        
        # Build fallback result
        return {
            "provider_id": "TransferGo",
            "source_currency": send_currency,
            "source_amount": send_amount,
            "destination_currency": receive_currency,
            "destination_amount": receive_amount,
            "exchange_rate": exchange_rate,
            "fee": fee,
            "delivery_method": "bank deposit",
            "delivery_time_minutes": 1440,  # Default: 24 hours (in minutes)
            "corridor": f"{source_country}-{receive_country}",
            "payment_method": "Bank Transfer",
            "details": {"is_fallback": True}
        }

    def _get_currency_for_country(self, country_code: str) -> str:
        """
        Get the default currency for a country code.
        
        Args:
            country_code: Two-letter country code
            
        Returns:
            Currency code for the country
        """
        return self.COUNTRY_CURRENCIES.get(country_code, "EUR")
    
    def _get_supported_currencies_for_country(self, country_code: str) -> List[str]:
        """
        Get all supported currencies for a country code.
        Some countries can receive in multiple currencies (local + USD/EUR).
        
        Args:
            country_code: Two-letter country code
            
        Returns:
            List of supported currency codes for the country
        """
        if country_code in self.MULTI_CURRENCY_COUNTRIES:
            return self.MULTI_CURRENCY_COUNTRIES[country_code]
        else:
            return [self.COUNTRY_CURRENCIES.get(country_code, "EUR")]

    def _get_country_for_currency(self, currency_code: str) -> str:
        """
        Get a default country for a currency code.
        
        Args:
            currency_code: Currency code (e.g., USD, EUR)
            
        Returns:
            The two-letter country code for a typical country using this currency
        """
        # Map common currencies to representative countries
        currency_to_country = {
            # Europe
            "EUR": "DE",  # Using Germany as default for Euro
            "GBP": "GB",
            "PLN": "PL",
            "RON": "RO",
            "CZK": "CZ",
            "HUF": "HU",
            "SEK": "SE",
            "NOK": "NO",
            "DKK": "DK",
            "CHF": "CH",
            "BGN": "BG",
            "HRK": "HR",
            
            # Americas
            "USD": "US",
            "CAD": "CA",
            "MXN": "MX",
            "BRL": "BR",
            "COP": "CO",
            "ARS": "AR",
            "CLP": "CL",
            "PEN": "PE",
            "UYU": "UY",
            "DOP": "DO",
            "JMD": "JM",
            "BSD": "BS",
            "BBD": "BB",
            "TTD": "TT",
            
            # Asia Pacific
            "AUD": "AU",
            "NZD": "NZ",
            "JPY": "JP",
            "SGD": "SG",
            "CNY": "CN",
            "HKD": "HK",
            "KRW": "KR",
            "TWD": "TW",
            "MYR": "MY",
            "THB": "TH",
            "VND": "VN",
            "IDR": "ID",
            "PHP": "PH",
            "INR": "IN",
            "PKR": "PK",
            "BDT": "BD",
            "LKR": "LK",
            "NPR": "NP",
            
            # Middle East
            "AED": "AE",
            "SAR": "SA",
            "QAR": "QA",
            "BHD": "BH",
            "KWD": "KW",
            "OMR": "OM",
            "ILS": "IL",
            "JOD": "JO",
            "LBP": "LB",
            "TRY": "TR",
            
            # Africa
            "ZAR": "ZA",
            "NGN": "NG",
            "KES": "KE",
            "EGP": "EG",
            "MAD": "MA",
            "TND": "TN",
            "GHS": "GH",
            "TZS": "TZ",
            "UGX": "UG",
            "ETB": "ET",
            
            # Eastern Europe & Central Asia
            "UAH": "UA",
            "RUB": "RU",
            "KZT": "KZ",
            "GEL": "GE",
            "BYN": "BY",
            "AZN": "AZ",
            "MDL": "MD",
            "ALL": "AL",
            "BAM": "BA",
            "RSD": "RS",
            "MKD": "MK",
            "AMD": "AM",
            "UZS": "UZ",
            "TJS": "TJ"
        }
        
        return currency_to_country.get(currency_code, "GB" if currency_code == "GBP" else "DE")

    def _parse_delivery_time(self, time_string: str) -> Optional[int]:
        """
        Parse delivery time string into minutes.
        
        Args:
            time_string: String describing delivery time (e.g. "1-2 business days")
            
        Returns:
            Estimated delivery time in minutes or None if unknown
        """
        if not time_string:
            return None
            
        time_string = time_string.lower()
        
        # Handle common time formats
        if "minutes" in time_string:
            try:
                mins = int(time_string.split()[0])
                return mins
            except (ValueError, IndexError):
                pass
                
        if "hours" in time_string:
            try:
                hours = int(time_string.split()[0])
                return hours * 60
            except (ValueError, IndexError):
                pass
                
        if "same day" in time_string:
            return 12 * 60  # 12 hours
            
        if "next day" in time_string or "1 business day" in time_string:
            return 24 * 60  # 24 hours
            
        if "1-2" in time_string and "days" in time_string:
            return 36 * 60  # 1.5 days
            
        if "2-3" in time_string and "days" in time_string:
            return 60 * 60  # 2.5 days
            
        if "instant" in time_string or "immediately" in time_string:
            return 5  # 5 minutes
            
        # Default mappings
        mappings = {
            "standard": 48 * 60,  # 2 days
            "fast": 24 * 60,      # 1 day
            "today": 8 * 60,      # 8 hours
            "express": 4 * 60,    # 4 hours
            "urgent": 2 * 60      # 2 hours
        }
        
        for key, value in mappings.items():
            if key in time_string:
                return value
                
        # Default fallback
        return None

    def get_supported_countries_and_currencies(self) -> Dict[str, List[str]]:
        """
        Get a dictionary of all supported countries and their currencies.
        
        Returns:
            Dict with country codes as keys and list of supported currencies as values
        """
        result = {}
        
        # Add all regular countries with their primary currency
        for country, currency in self.COUNTRY_CURRENCIES.items():
            result[country] = [currency]
        
        # Add multi-currency countries with all their supported currencies
        for country, currencies in self.MULTI_CURRENCY_COUNTRIES.items():
            result[country] = currencies
            
        return result
    
    def get_supported_send_countries(self) -> List[str]:
        """
        Get a list of countries that can be used as send countries.
        
        Returns:
            List of two-letter country codes
        """
        # For TransferGo, not all countries can be used as send countries
        # This is a subset of the most common send countries
        return [
            # Europe
            "GB", "DE", "FR", "ES", "IT", "NL", "BE", "AT", "IE", 
            "PL", "RO", "LT", "LV", "CZ", "HU", "SE", "DK", "NO", 
            # Americas
            "US", "CA",
            # Asia Pacific
            "AU", "SG",
            # Middle East
            "AE", "TR",
            # Africa
            "ZA"
        ]
    
    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 