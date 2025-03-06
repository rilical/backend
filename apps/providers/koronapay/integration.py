"""
KoronaPay Provider Integration

This module provides integration with the KoronaPay remittance service.
It supports sending money from Europe to various countries with multiple payment methods.
"""

import logging
import requests
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import json

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    KoronaPayError,
    KoronaPayAuthError,
    KoronaPayAPIError,
    KoronaPayValidationError,
    KoronaPayCorridorError,
    KoronaPayPaymentMethodError
)
from .mapping import (
    get_currency_id,
    get_country_id,
    get_payment_method,
    get_receiving_method,
    get_supported_currencies,
    get_supported_countries,
    get_supported_payment_methods,
    get_supported_receiving_methods
)

logger = logging.getLogger(__name__)

class KoronaPayProvider(RemittanceProvider):
    """
    KoronaPay integration for retrieving fees, exchange rates, and quotes.
    
    The API requires specific headers and supports various payment methods:
    - Payment methods: debitCard, bankAccount
    - Receiving methods: cash, card
    
    Currency IDs:
    - 978: EUR (Euro)
    - 840: USD (US Dollar)
    - 949: TRY (Turkish Lira)
    - 360: IDR (Indonesian Rupiah)
    - And many more...
    """
    
    BASE_URL = "https://koronapay.com/api"
    API_VERSION = "v2.138"
    
    # Payment method mappings
    PAYMENT_METHODS = {
        "debit_card": "debitCard",
        "bank_account": "bankAccount"
    }
    
    RECEIVING_METHODS = {
        "cash": "cash",
        "card": "card"
    }
    
    # Currency mappings
    CURRENCY_IDS = {
        "EUR": "978",  # Euro
        "USD": "840",  # US Dollar
        "TRY": "949",  # Turkish Lira
        "IDR": "360",  # Indonesian Rupiah
        "GBP": "826",  # British Pound
        "PLN": "985",  # Polish Zloty
        "CZK": "203",  # Czech Koruna
        "HUF": "348",  # Hungarian Forint
        "RON": "946",  # Romanian Leu
        "BGN": "975",  # Bulgarian Lev
        "HRK": "191",  # Croatian Kuna
        "DKK": "208",  # Danish Krone
        "SEK": "752",  # Swedish Krona
        "NOK": "578",  # Norwegian Krone
        "VND": "704",  # Vietnamese Dong
        "PHP": "608",  # Philippine Peso
        "THB": "764",  # Thai Baht
        "MYR": "458"   # Malaysian Ringgit
    }
    
    # Country mappings
    COUNTRY_IDS = {
        # Source Countries (Europe)
        "AUT": "Austria",
        "BEL": "Belgium",
        "BGR": "Bulgaria",
        "HRV": "Croatia",
        "CYP": "Cyprus",
        "CZE": "Czech Republic",
        "DNK": "Denmark",
        "EST": "Estonia",
        "FIN": "Finland",
        "FRA": "France",
        "DEU": "Germany",
        "GRC": "Greece",
        "HUN": "Hungary",
        "ISL": "Iceland",
        "IRL": "Ireland",
        "ITA": "Italy",
        "LVA": "Latvia",
        "LIE": "Liechtenstein",
        "LTU": "Lithuania",
        "LUX": "Luxembourg",
        "MLT": "Malta",
        "NLD": "Netherlands",
        "NOR": "Norway",
        "POL": "Poland",
        "PRT": "Portugal",
        "ROU": "Romania",
        "SVK": "Slovakia",
        "SVN": "Slovenia",
        "ESP": "Spain",
        "SWE": "Sweden",
        "GBR": "United Kingdom",
        
        # Destination Countries
        "IDN": "Indonesia",
        "TUR": "Turkey",
        "VNM": "Vietnam",
        "PHL": "Philippines",
        "THA": "Thailand",
        "MYS": "Malaysia"
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the KoronaPay provider."""
        super().__init__(name="koronapay", base_url=self.BASE_URL)
        self.config = config or {}
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Set up the session with required headers."""
        self.session.headers.update({
            "Accept": f"application/vnd.cft-data.{self.API_VERSION}+json",
            "Accept-Language": "en",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "x-application": "Qpay-Web/3.0"
        })
    
    def _get_request_headers(self) -> Dict[str, str]:
        """Get headers for API request."""
        return {
            "Request-ID": str(uuid.uuid4()),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
    
    def _validate_currency(self, currency: str) -> str:
        """Validate and return currency ID."""
        currency_id = get_currency_id(currency)
        if not currency_id:
            raise KoronaPayValidationError(f"Unsupported currency: {currency}")
        return currency_id
    
    def _validate_country(self, country: str) -> str:
        """Validate and return country ID."""
        country_id = get_country_id(country)
        if not country_id:
            raise KoronaPayValidationError(f"Unsupported country: {country}")
        return country_id
    
    def _validate_payment_method(self, method: str) -> str:
        """Validate and return payment method."""
        payment_method = get_payment_method(method)
        if not payment_method:
            raise KoronaPayPaymentMethodError(f"Unsupported payment method: {method}")
        return payment_method
    
    def _validate_receiving_method(self, method: str) -> str:
        """Validate and return receiving method."""
        receiving_method = get_receiving_method(method)
        if not receiving_method:
            raise KoronaPayPaymentMethodError(f"Unsupported receiving method: {method}")
        return receiving_method
    
    def get_tariffs(
        self,
        sending_country: str,
        receiving_country: str,
        sending_currency: str,
        receiving_currency: str,
        amount: Decimal,
        is_amount_receiving: bool = False,
        payment_method: str = "debit_card",
        receiving_method: str = "cash"
    ) -> Dict[str, Any]:
        """
        Get transfer tariffs from KoronaPay API.
        
        Args:
            sending_country: Country code of sender (e.g., "ESP")
            receiving_country: Country code of receiver (e.g., "TUR")
            sending_currency: Currency code to send (e.g., "EUR")
            receiving_currency: Currency code to receive (e.g., "USD")
            amount: Amount to send/receive
            is_amount_receiving: Whether amount is receiving amount
            payment_method: Method of payment (debit_card, bank_account)
            receiving_method: Method of receiving (cash, card)
            
        Returns:
            Dictionary containing tariff information
        """
        try:
            # Validate inputs
            sending_country_id = self._validate_country(sending_country)
            receiving_country_id = self._validate_country(receiving_country)
            sending_currency_id = self._validate_currency(sending_currency)
            receiving_currency_id = self._validate_currency(receiving_currency)
            payment_method = self._validate_payment_method(payment_method)
            receiving_method = self._validate_receiving_method(receiving_method)
            
            # Prepare query parameters
            params = {
                "sendingCountryId": sending_country_id,
                "receivingCountryId": receiving_country_id,
                "sendingCurrencyId": sending_currency_id,
                "receivingCurrencyId": receiving_currency_id,
                "paymentMethod": payment_method,
                "receivingMethod": receiving_method,
                "paidNotificationEnabled": "false"
            }
            
            # Add amount parameter based on type
            amount_key = "receivingAmount" if is_amount_receiving else "sendingAmount"
            params[amount_key] = str(int(amount * 100))  # Convert to cents
            
            # Make API request
            response = self.session.get(
                f"{self.BASE_URL}/transfers/tariffs",
                params=params,
                headers=self._get_request_headers(),
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_msg)
                except:
                    pass
                raise KoronaPayAPIError(
                    error_msg,
                    status_code=response.status_code,
                    response=response.json() if response.text else None
                )
            
            # Parse response
            try:
                tariffs = response.json()
            except json.JSONDecodeError as e:
                raise KoronaPayAPIError(f"Invalid JSON response: {str(e)}")
            
            if not tariffs:
                raise KoronaPayAPIError("No tariffs available for this corridor")
            
            if isinstance(tariffs, dict):
                # Handle single tariff response
                tariff = tariffs
            elif isinstance(tariffs, list):
                # Handle list of tariffs
                if not tariffs:
                    raise KoronaPayAPIError("No tariffs available for this corridor")
                tariff = tariffs[0]
            else:
                raise KoronaPayAPIError("Invalid tariff response format")
            
            # Validate required fields
            required_fields = ["sendingAmount", "receivingAmount", "exchangeRate", "sendingCommission"]
            missing_fields = [field for field in required_fields if field not in tariff]
            if missing_fields:
                raise KoronaPayAPIError(f"Missing required fields in tariff: {', '.join(missing_fields)}")
            
            return {
                "success": True,
                "sending_amount": Decimal(str(tariff["sendingAmount"])) / 100,
                "sending_currency": sending_currency,
                "receiving_amount": Decimal(str(tariff["receivingAmount"])) / 100,
                "receiving_currency": receiving_currency,
                "exchange_rate": Decimal(str(tariff["exchangeRate"])),
                "fee": Decimal(str(tariff["sendingCommission"])) / 100,
                "total_cost": Decimal(str(tariff["sendingAmount"])) / 100,
                "provider": "koronapay",
                "timestamp": datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"KoronaPay API request failed: {e}")
            raise KoronaPayAPIError(f"API request failed: {str(e)}")
        
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing KoronaPay response: {e}")
            raise KoronaPayAPIError(f"Error parsing response: {str(e)}")
    
    def get_quote(
        self,
        send_amount: Optional[float] = None,
        receive_amount: Optional[float] = None,
        send_currency: str = "EUR",
        receive_currency: str = "USD",
        send_country: str = "ESP",
        receive_country: str = "TUR",
        payment_method: str = "debit_card",
        receiving_method: str = "cash",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for a money transfer from KoronaPay.
        
        Args:
            send_amount: Amount to send (in source currency)
            receive_amount: Amount to receive (in target currency)
            send_currency: Currency to send (e.g., "EUR")
            receive_currency: Currency to receive (e.g., "USD")
            send_country: Sending country code (e.g., "ESP")
            receive_country: Receiving country code (e.g., "TUR")
            payment_method: Method of payment
            receiving_method: Method of delivery
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing standardized quote information
        """
        if send_amount is None and receive_amount is None:
            return self.standardize_response({
                "success": False,
                "error_message": "Either send_amount or receive_amount must be provided"
            })
            
        is_amount_receiving = send_amount is None
        amount = Decimal(str(receive_amount if is_amount_receiving else send_amount))
        
        try:
            # Validate inputs
            send_currency = self._validate_currency(send_currency)
            receive_currency = self._validate_currency(receive_currency)
            send_country = self._validate_country(send_country)
            receive_country = self._validate_country(receive_country)
            payment_method = self._validate_payment_method(payment_method)
            receiving_method = self._validate_receiving_method(receiving_method)
            
            # Get tariff information
            tariff = self.get_tariffs(
                sending_country=send_country,
                receiving_country=receive_country,
                sending_currency=send_currency,
                receiving_currency=receive_currency,
                amount=amount,
                is_amount_receiving=is_amount_receiving,
                payment_method=payment_method,
                receiving_method=receiving_method
            )
            
            # Build result
            result = {
                "success": True,
                "send_amount": float(tariff["sending_amount"]),
                "send_currency": send_currency,
                "receive_amount": float(tariff["receiving_amount"]),
                "receive_currency": receive_currency,
                "exchange_rate": float(tariff["exchange_rate"]),
                "fee": float(tariff["fee"]),
                "total_cost": float(tariff["total_cost"]),
                "payment_method": payment_method,
                "delivery_method": receiving_method,
                "timestamp": tariff["timestamp"]
            }
            
            # Include raw response if requested
            if kwargs.get("include_raw", False):
                result["raw_response"] = tariff
                
            return self.standardize_response(result, provider_specific_data=kwargs.get("include_raw", False))
                
        except KoronaPayError as e:
            logger.error(f"Failed to get quote: {e}")
            return self.standardize_response({
                "success": False,
                "error_message": str(e)
            })
        except Exception as e:
            logger.error(f"Unexpected error getting quote: {e}")
            return self.standardize_response({
                "success": False,
                "error_message": f"Unexpected error: {str(e)}"
            })
    
    def get_exchange_rate(
        self,
        send_currency: str,
        receive_currency: str,
        send_country: str = "ESP",
        receive_country: str = "TUR",
        amount: Decimal = Decimal("1000")
    ) -> Dict[str, Any]:
        """
        Get current exchange rate for a currency pair.
        
        Args:
            send_currency: Currency to send
            receive_currency: Currency to receive
            send_country: Sending country code
            receive_country: Receiving country code
            amount: Amount to get rate for (defaults to 1000)
            
        Returns:
            Dictionary containing standardized exchange rate information
        """
        try:
            # Get tariff information (which includes exchange rate)
            tariff = self.get_tariffs(
                sending_country=send_country,
                receiving_country=receive_country,
                sending_currency=send_currency,
                receiving_currency=receive_currency,
                amount=amount,
                is_amount_receiving=False
            )
            
            return self.standardize_response({
                "success": True,
                "source_currency": send_currency,
                "target_currency": receive_currency,
                "rate": float(tariff["exchange_rate"]),
                "fee": float(tariff["fee"]),
                "timestamp": tariff["timestamp"]
            })
            
        except KoronaPayError as e:
            logger.error(f"Failed to get exchange rate: {e}")
            return self.standardize_response({
                "success": False,
                "error_message": str(e),
                "source_currency": send_currency,
                "target_currency": receive_currency
            })
        except Exception as e:
            logger.error(f"Unexpected error getting exchange rate: {e}")
            return self.standardize_response({
                "success": False,
                "error_message": f"Unexpected error: {str(e)}",
                "source_currency": send_currency,
                "target_currency": receive_currency
            })
    
    def get_supported_countries(self) -> List[str]:
        """Get list of supported destination countries."""
        return get_supported_countries()
    
    def get_supported_currencies(self) -> List[str]:
        """Get list of supported currencies."""
        return get_supported_currencies()
    
    def get_supported_payment_methods(self) -> List[str]:
        """Get list of supported payment methods."""
        return get_supported_payment_methods()
    
    def get_supported_receiving_methods(self) -> List[str]:
        """Get list of supported receiving methods."""
        return get_supported_receiving_methods() 