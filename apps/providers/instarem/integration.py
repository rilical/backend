"""
InstaRem Money Transfer Integration

This module implements the integration with InstaRem, a service for international
money transfers. InstaRem is known for competitive exchange rates, especially for
Asian corridors.

The integration uses InstaRem's public API to fetch quotes for international money transfers.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from apps.providers.instarem.exceptions import InstaRemApiError

# Setup logging
logger = logging.getLogger(__name__)

class InstaRemProvider(RemittanceProvider):
    """
    Integration with InstaRem's public transaction computed-value endpoint.
    
    Example usage:
        provider = InstaRemProvider()
        quote = provider.get_quote(
            amount=Decimal("1000.00"),
            source_currency="USD",
            dest_currency="INR",
            source_country="US",
            dest_country="IN"
        )
    """

    BASE_URL = "https://www.instarem.com"
    QUOTE_ENDPOINT = "/api/v1/public/transaction/computed-value"
    
    # Bank account IDs for different delivery methods
    DELIVERY_METHODS = {
        "BankDeposit": {
            "id": 58,
            "name": "Bank Deposit",
            "description": "Direct deposit to bank account",
            "estimated_minutes": 60
        },
        "InstantTransfer": {
            "id": 95,
            "name": "Instant Transfer",
            "description": "Instant transfer to bank account",
            "estimated_minutes": 15
        },
        "PesoNet": {
            "id": 96,
            "name": "PesoNet",
            "description": "PesoNet transfer (Philippines)",
            "estimated_minutes": 120
        }
    }

    def __init__(self, name="instarem"):
        """Initialize the InstaRem provider."""
        super().__init__(name=name, base_url=self.BASE_URL)
        self.session = requests.Session()

        # Set browser-like headers
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                          "Version/18.3 Safari/605.1.15"),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://www.instarem.com/en-us/",
            "X-Requested-With": "XMLHttpRequest",
            "Priority": "u=3, i"
        })

        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.logger = logging.getLogger(f"providers.{name}")

    def get_delivery_methods(
        self,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str
    ) -> List[Dict[str, Any]]:
        """Get available delivery methods."""
        methods = []
        for method_name, method_info in self.DELIVERY_METHODS.items():
            methods.append({
                "id": method_info["id"],
                "name": method_info["name"],
                "type": method_name,
                "estimated_minutes": method_info["estimated_minutes"],
                "description": method_info["description"],
                "is_default": method_name == "BankDeposit"
            })
        return methods

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        dest_currency: str,
        source_country: str,
        dest_country: str,
        delivery_method: str = None,
        payment_method: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for a money transfer from InstaRem.
        
        Args:
            amount: Amount to send
            source_currency: Source currency code (e.g., "USD")
            dest_currency: Destination currency code (e.g., "INR")
            source_country: Source country code (e.g., "US")
            dest_country: Destination country code (e.g., "IN")
            delivery_method: Method of delivery (optional)
            payment_method: Method of payment (optional)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing standardized quote information
        """
        # Initialize result with default values
        quote_result = {
            "success": False,
            "send_amount": float(amount),
            "send_currency": source_currency.upper(),
            "receive_currency": dest_currency.upper(),
            "exchange_rate": None,
            "fee": None,
            "total_cost": None,
            "receive_amount": None,
            "error_message": None
        }
        
        try:
            # Format the currency codes to uppercase
            source_currency = source_currency.upper()
            dest_currency = dest_currency.upper()
            
            # Get the bank account ID for delivery method
            bank_account_id = self.DELIVERY_METHODS.get(delivery_method, self.DEFAULT_BANK_ACCOUNT_ID)
            
            # Construct the API request data
            payload = {
                "sourceCurrency": source_currency,
                "targetCurrency": dest_currency,
                "amount": str(amount),
                "amountType": "SOURCE",
                "recipientTypeCode": "bank_account",
                "bankAccountId": bank_account_id
            }
            
            # Make the API request
            logger.info(f"Requesting quote from InstaRem: {payload}")
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            response = self.session.post(
                f"{self.BASE_URL}{self.QUOTE_ENDPOINT}",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Include raw data if requested
            if kwargs.get("include_raw", False):
                quote_result["raw_response"] = data
            
            # Check for errors in the response
            if data.get("status") == "error":
                error_msg = data.get("message", "Unknown error from InstaRem API")
                logger.warning(f"InstaRem API error: {error_msg}")
                quote_result["error_message"] = error_msg
                return self.standardize_response(quote_result, provider_specific_data=kwargs.get("include_raw", False))
            
            # Extract the quote information
            quote_data = data.get("data", {})
            if not quote_data:
                quote_result["error_message"] = "No quote data returned from InstaRem API"
                return self.standardize_response(quote_result, provider_specific_data=kwargs.get("include_raw", False))
            
            # Calculate values
            send_amount = Decimal(str(amount))
            exchange_rate = Decimal(str(quote_data.get("fx_rate", 0)))
            fee = Decimal(str(quote_data.get("fee", 0)))
            receive_amount = Decimal(str(quote_data.get("target_amount", 0)))
            total_cost = send_amount + fee
            
            # Extract delivery time if available
            delivery_time_minutes = None
            delivery_time_hours = quote_data.get("estimated_delivery_time")
            if delivery_time_hours:
                try:
                    delivery_time_minutes = int(delivery_time_hours) * 60
                except (ValueError, TypeError):
                    pass
            
            # Update result with extracted data
            quote_result.update({
                "success": True,
                "send_amount": float(send_amount),
                "exchange_rate": float(exchange_rate),
                "fee": float(fee),
                "receive_amount": float(receive_amount),
                "total_cost": float(total_cost),
                "timestamp": datetime.now().isoformat(),
                "payment_method": payment_method,
                "delivery_method": delivery_method,
                "delivery_time_minutes": delivery_time_minutes
            })
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(error_msg)
            quote_result["error_message"] = error_msg
            
        except (ValueError, KeyError, TypeError) as e:
            error_msg = f"Response parsing error: {str(e)}"
            logger.error(error_msg)
            quote_result["error_message"] = error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            quote_result["error_message"] = error_msg
        
        return self.standardize_response(quote_result, provider_specific_data=kwargs.get("include_raw", False))

    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 