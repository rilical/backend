"""
Dahabshiil provider integration module.

This module implements the Dahabshiil provider for retrieving remittance quotes.
"""

import logging
import requests
import json
from decimal import Decimal
from typing import Dict, Any, List
from datetime import datetime

from apps.providers.base.provider import RemittanceProvider
from .exceptions import DahabshiilApiError

logger = logging.getLogger(__name__)

class DahabshiilProvider(RemittanceProvider):
    """
    Provider implementation for Dahabshiil, an international remittance service
    with a strong presence in East Africa and the Middle East.

    Example usage:
        provider = DahabshiilProvider()
        quote = provider.get_quote(
            amount=Decimal("700.00"),
            source_currency="USD",
            dest_currency="KES",
            source_country="US",
            dest_country="KE"
        )
    """

    # Public Dahabshiil endpoints
    BASE_URL = "https://apigw-us.dahabshiil.com/remit/transaction"
    GET_CHARGES_ENDPOINT = "/get-charges-anonymous"

    def __init__(self, name="dahabshiil"):
        """Initialize the Dahabshiil provider."""
        super().__init__(name=name, base_url=self.BASE_URL)
        self.session = requests.Session()

        # Set browser-like headers
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                          "Version/18.3 Safari/605.1.15"),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Origin": "https://www.dahabshiil.com"
        })
        
        self.logger = logging.getLogger(f"providers.{name}")

    def get_delivery_methods(
        self,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str
    ) -> List[Dict[str, Any]]:
        """Get available delivery methods."""
        # Let the API handle available methods
        return []

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
        Get a quote for a money transfer from Dahabshiil.
        
        Args:
            amount: Amount to send
            source_currency: Source currency code (e.g., "USD")
            dest_currency: Destination currency code (e.g., "KES")
            source_country: Source country code (e.g., "US")
            dest_country: Destination country code (e.g., "KE")
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
            # Build the API request
            payload = {
                "sourceAmount": str(amount),
                "sourceCurrency": source_currency.upper(),
                "targetCurrency": dest_currency.upper(),
                "sourceCountry": source_country.upper(),
                "targetCountry": dest_country.upper()
            }
            
            # Make the API request
            self.logger.info(f"Requesting quote from Dahabshiil: {payload}")
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            response = self.session.post(
                f"{self.BASE_URL}{self.GET_CHARGES_ENDPOINT}",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            self.logger.info(f"Dahabshiil response: {data}")
            
            # Extract relevant information
            if data.get("success", False) and "data" in data:
                quote_data = data["data"]
                # Calculate values
                send_amount = Decimal(str(amount))
                exchange_rate = Decimal(str(quote_data.get("rate", 0)))
                fee = Decimal(str(quote_data.get("fee", 0)))
                receive_amount = send_amount * exchange_rate
                total_cost = send_amount + fee

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
                    "delivery_method": delivery_method
                })
                
                # Include raw data if requested
                if kwargs.get("include_raw", False):
                    quote_result["raw_response"] = data
            else:
                # Handle API error
                error_msg = data.get("message", "Unknown error from Dahabshiil API")
                self.logger.warning(f"Dahabshiil API error: {error_msg}")
                quote_result["error_message"] = error_msg
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            self.logger.error(error_msg)
            quote_result["error_message"] = error_msg
            
        except (ValueError, KeyError, TypeError) as e:
            error_msg = f"Response parsing error: {str(e)}"
            self.logger.error(error_msg)
            quote_result["error_message"] = error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg)
            quote_result["error_message"] = error_msg

        return self.standardize_response(quote_result, provider_specific_data=kwargs.get("include_raw", False))

    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_exchange_rate(
        self,
        source_currency: str,
        target_currency: str,
        source_country: str,
        target_country: str,
        amount: Decimal = Decimal("1000")
    ) -> Dict[str, Any]:
        """
        Get current exchange rate for a currency pair.
        
        Args:
            source_currency: Source currency code (ISO-4217)
            target_currency: Target currency code (ISO-4217)
            source_country: Source country code (ISO-3166-1 alpha-2 or alpha-3)
            target_country: Target country code (ISO-3166-1 alpha-2 or alpha-3)
            amount: Amount to get rate for (defaults to 1000)
            
        Returns:
            Dictionary containing standardized exchange rate information
        """
        try:
            # Use the get_quote method to fetch rate information
            quote = self.get_quote(
                amount=amount,
                source_currency=source_currency,
                dest_currency=target_currency,
                source_country=source_country,
                dest_country=target_country
            )
            
            # Convert to the standardized exchange rate format
            return self.standardize_response({
                "success": quote.get("success", False),
                "source_currency": source_currency,
                "target_currency": target_currency,
                "rate": quote.get("exchange_rate"),
                "fee": quote.get("fee"),
                "timestamp": datetime.now().isoformat(),
                "error_message": quote.get("error_message")
            })
            
        except Exception as e:
            logger.error(f"Failed to get exchange rate: {e}")
            return self.standardize_response({
                "success": False,
                "error_message": str(e),
                "source_currency": source_currency,
                "target_currency": target_currency
            }) 