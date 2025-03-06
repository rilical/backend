"""
Intermex Provider Integration

This module provides integration with the Intermex remittance service.
It supports sending money from the US to various countries with multiple payment methods.
"""

import logging
import requests
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    IntermexError,
    IntermexAuthError,
    IntermexAPIError,
    IntermexValidationError
)
from .mapping import (
    map_country_code,
    map_payment_method,
    map_delivery_method,
    validate_corridor
)

logger = logging.getLogger(__name__)

class IntermexProvider(RemittanceProvider):
    """
    Intermex integration for retrieving fees, exchange rates, and quotes.
    
    The API requires specific headers and supports various payment methods:
    - Payment methods: debitCard, creditCard, bankAccount, cash, ACH, wireTransfer
    - Delivery methods: bankDeposit, cashPickup, mobileWallet, homeDelivery
    
    Currency IDs:
    - USD: US Dollar (source)
    - MXN: Mexican Peso
    - GTQ: Guatemalan Quetzal
    - HNL: Honduran Lempira
    - NIO: Nicaraguan Cordoba
    - CRC: Costa Rican Colon
    - PAB: Panamanian Balboa
    - COP: Colombian Peso
    - PEN: Peruvian Sol
    - BOB: Bolivian Boliviano
    - ARS: Argentine Peso
    - BRL: Brazilian Real
    - UYU: Uruguayan Peso
    - PYG: Paraguayan Guarani
    - VES: Venezuelan Bolivar
    - DOP: Dominican Peso
    - HTG: Haitian Gourde
    - JMD: Jamaican Dollar
    - CUP: Cuban Peso
    - EUR: Euro (for European countries)
    - GBP: British Pound
    - RON: Romanian Leu
    - PLN: Polish Zloty
    - HUF: Hungarian Forint
    - CZK: Czech Koruna
    - BGN: Bulgarian Lev
    - DKK: Danish Krone
    - SEK: Swedish Krona
    - NOK: Norwegian Krone
    - ISK: Icelandic Krona
    - CHF: Swiss Franc
    """
    
    BASE_URL = "https://api.intermexonline.com/api"  # Updated endpoint
    API_VERSION = "v1"
    
    # Supported countries
    SUPPORTED_COUNTRIES = {
        "US": "United States",
        "MX": "Mexico",
        "GT": "Guatemala",
        "HN": "Honduras",
        "SV": "El Salvador",
        "NI": "Nicaragua",
        "CR": "Costa Rica",
        "PA": "Panama",
        "CO": "Colombia",
        "PE": "Peru",
        "EC": "Ecuador",
        "BO": "Bolivia",
        "BR": "Brazil",
        "AR": "Argentina",
        "UY": "Uruguay",
        "PY": "Paraguay",
        "CL": "Chile",
        "DO": "Dominican Republic",
        "HT": "Haiti",
        "JM": "Jamaica"
    }
    
    # Supported currencies
    SUPPORTED_CURRENCIES = {
        "USD": "US Dollar",
        "MXN": "Mexican Peso",
        "GTQ": "Guatemalan Quetzal",
        "HNL": "Honduran Lempira",
        "SVC": "Salvadoran Colon",
        "NIO": "Nicaraguan Cordoba",
        "CRC": "Costa Rican Colon",
        "PAB": "Panamanian Balboa",
        "COP": "Colombian Peso",
        "PEN": "Peruvian Sol",
        "BOB": "Bolivian Boliviano",
        "BRL": "Brazilian Real",
        "ARS": "Argentine Peso",
        "UYU": "Uruguayan Peso",
        "PYG": "Paraguayan Guarani",
        "CLP": "Chilean Peso",
        "DOP": "Dominican Peso",
        "HTG": "Haitian Gourde",
        "JMD": "Jamaican Dollar"
    }
    
    # Payment methods
    PAYMENT_METHODS = {
        "debitCard": "Debit Card",
        "creditCard": "Credit Card",
        "bankAccount": "Bank Account",
        "cash": "Cash",
        "ACH": "ACH Transfer",
        "wireTransfer": "Wire Transfer"
    }
    
    # Receiving methods
    RECEIVING_METHODS = {
        "bankDeposit": "Bank Deposit",
        "cashPickup": "Cash Pickup",
        "mobileWallet": "Mobile Wallet",
        "homeDelivery": "Home Delivery"
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the Intermex provider."""
        super().__init__(name="intermex", base_url=self.BASE_URL)
        self.config = config or {}
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Set up the session with required headers."""
        self.session.headers.update({
            "Accept": f"application/vnd.intermex.{self.API_VERSION}+json",
            "Accept-Language": "en",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
        })
    
    def _get_request_headers(self) -> Dict[str, str]:
        """Get headers for API request."""
        return {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
    
    def get_supported_countries(self) -> List[str]:
        """Get list of supported destination countries."""
        return list(self.SUPPORTED_COUNTRIES.keys())
    
    def get_supported_currencies(self) -> List[str]:
        """Get list of supported currencies."""
        return list(self.SUPPORTED_CURRENCIES.keys())
    
    def get_supported_payment_methods(self) -> List[str]:
        """Get list of supported payment methods."""
        return list(self.PAYMENT_METHODS.keys())
    
    def get_supported_receiving_methods(self) -> List[str]:
        """Get list of supported receiving methods."""
        return list(self.RECEIVING_METHODS.keys())
    
    def get_delivery_methods(
        self,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str
    ) -> Dict[str, Any]:
        """
        Get available delivery methods for a corridor.
        
        Args:
            source_country: Source country code
            dest_country: Destination country code
            source_currency: Source currency code
            dest_currency: Destination currency code
            
        Returns:
            Dictionary containing delivery methods
        """
        try:
            # Validate corridor
            is_valid, error = validate_corridor(
                source_country,
                source_currency,
                dest_country,
                dest_currency
            )
            if not is_valid:
                return {
                    "success": False,
                    "error": error,
                    "provider": "intermex"
                }
            
            # Map country codes
            mapped_source = map_country_code(source_country)
            mapped_dest = map_country_code(dest_country)
            
            # Prepare query parameters
            params = {
                "sourceCountry": mapped_source,
                "destinationCountry": mapped_dest,
                "sourceCurrency": source_currency.upper(),
                "destinationCurrency": dest_currency.upper()
            }
            
            # Make API request
            response = self.session.get(
                f"{self.BASE_URL}/delivery-methods",
                params=params,
                headers=self._get_request_headers(),
                timeout=30
            )
            
            if response.status_code != 200:
                raise IntermexAPIError(
                    f"API request failed with status {response.status_code}",
                    status_code=response.status_code,
                    response=response.json() if response.text else None
                )
            
            # Parse response
            methods = response.json()
            if not methods or not isinstance(methods, list):
                raise IntermexAPIError("Invalid delivery methods response format")
            
            # Map delivery methods to standard format
            delivery_methods = []
            for method in methods:
                mapped_method = map_delivery_method(method.get("name"))
                if mapped_method:
                    delivery_methods.append({
                        "id": mapped_method["tranTypeId"],
                        "name": mapped_method["tranTypeName"],
                        "type": mapped_method["deliveryType"],
                        "estimated_minutes": method.get("estimatedMinutes", 60),
                        "description": method.get("description", ""),
                        "is_default": method.get("isDefault", False)
                    })
            
            return {
                "success": True,
                "delivery_methods": delivery_methods,
                "provider": "intermex",
                "timestamp": datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Intermex API request failed: {e}")
            return {
                "success": False,
                "error": f"API request failed: {str(e)}",
                "provider": "intermex"
            }
        
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing Intermex response: {e}")
            return {
                "success": False,
                "error": f"Error parsing response: {str(e)}",
                "provider": "intermex"
            }
    
    def get_quote(
        self,
        send_amount: Optional[float] = None,
        receive_amount: Optional[float] = None,
        send_currency: str = "USD",
        receive_currency: str = "MXN",
        send_country: str = "US",
        receive_country: str = "MX",
        payment_method: str = "debitCard",
        delivery_method: str = "bankDeposit",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for a money transfer from Intermex.
        
        Args:
            send_amount: Amount to send (in source currency)
            receive_amount: Amount to receive (in target currency)
            send_currency: Currency to send (e.g., "USD")
            receive_currency: Currency to receive (e.g., "MXN")
            send_country: Sending country code (e.g., "US")
            receive_country: Receiving country code (e.g., "MX")
            payment_method: Method of payment (e.g., "debitCard")
            delivery_method: Method of delivery (e.g., "bankDeposit")
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
        
        # Build endpoint URL
        endpoint = f"{self.BASE_URL}/{self.API_VERSION}/money-transfer/quote"
        
        # Build request parameters
        params = {
            "sendingCountry": send_country,
            "receivingCountry": receive_country,
            "sendingCurrency": send_currency,
            "receivingCurrency": receive_currency,
            "paymentMethod": payment_method,
            "deliveryMethod": delivery_method
        }
        
        # Add amount parameters based on direction
        if is_amount_receiving:
            params["amountReceiving"] = str(amount)
        else:
            params["amountSending"] = str(amount)
        
        try:
            # Make the API request
            headers = self._get_request_headers()
            response = self.session.get(endpoint, params=params, headers=headers)
            
            # Check if the request was successful
            if response.status_code != 200:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return self.standardize_response({
                    "success": False,
                    "error_message": error_msg
                })

            # Parse the response
            quote_data = response.json()
            
            # Check if the API returned an error
            if "error" in quote_data:
                error_msg = f"API returned an error: {quote_data['error']}"
                logger.error(error_msg)
                return self.standardize_response({
                    "success": False,
                    "error_message": error_msg
                })
            
            # Extract the quote information
            result = {
                "success": True,
                "send_amount": float(quote_data.get("sendingAmount", 0)),
                "send_currency": send_currency,
                "receive_amount": float(quote_data.get("receivingAmount", 0)),
                "receive_currency": receive_currency,
                "exchange_rate": float(quote_data.get("exchangeRate", 0)),
                "fee": float(quote_data.get("fee", 0)),
                "total_cost": float(quote_data.get("totalCost", 0)),
                "payment_method": payment_method,
                "delivery_method": delivery_method,
                "timestamp": datetime.now().isoformat(),
                "delivery_time_minutes": quote_data.get("estimatedDeliveryTimeMinutes")
            }
            
            # Include raw response if requested
            if kwargs.get("include_raw", False):
                result["raw_response"] = quote_data
                
            return self.standardize_response(result, provider_specific_data=kwargs.get("include_raw", False))
            
        except Exception as e:
            error_msg = f"Failed to get quote: {str(e)}"
            logger.error(error_msg)
            return self.standardize_response({
                "success": False,
                "error_message": error_msg
            })
    
    def get_exchange_rate(
        self,
        send_currency: str,
        receive_currency: str,
        send_country: str = "US",
        receive_country: str = "MX",
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
            # Get a quote with the specified amount
            quote = self.get_quote(
                send_amount=float(amount),
                send_currency=send_currency,
                receive_currency=receive_currency,
                send_country=send_country,
                receive_country=receive_country
            )
            
            # Convert to the standardized exchange rate format
            return self.standardize_response({
                "success": quote.get("success", False),
                "source_currency": send_currency,
                "target_currency": receive_currency,
                "rate": quote.get("exchange_rate"),
                "fee": quote.get("fee"),
                "timestamp": quote.get("timestamp"),
                "error_message": quote.get("error_message")
            })
            
        except Exception as e:
            logger.error(f"Failed to get exchange rate: {e}")
            return self.standardize_response({
                "success": False,
                "error_message": str(e),
                "source_currency": send_currency,
                "target_currency": receive_currency
            }) 