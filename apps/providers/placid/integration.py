"""
Placid provider integration module.

This module implements the Placid provider for retrieving remittance
exchange rates and fees.
"""

import logging
import requests
import re
from decimal import Decimal
from typing import Any, Dict, Optional, List, Union

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    PlacidError,
    PlacidConnectionError,
    PlacidApiError,
    PlacidResponseError,
    PlacidCorridorUnsupportedError,
    PlacidCloudflareError,
)

logger = logging.getLogger(__name__)

class PlacidProvider(RemittanceProvider):
    """
    Example of adding Placid integration for retrieving rates or quotes.

    Observed usage from logs:
      POST /conf/sqls/pstRqstNS.php?TaskType=ChgContIndx&Val1=PAK&Val2=NIL&Val3=NIL&Val4=NIL&Val5=NIL&Val6=NIL
      body: rndval=1740963881748

    The response might contain HTML or text with lines like:
      PAK|//|Pakistan|//|PKR|//|ADP|//|Bank Deposit ...
      279.25 PKR
    ... which we'd parse to get the final exchange rate or corridor info.
    """

    BASE_URL = "https://www.placid.net"
    ENDPOINT = "/conf/sqls/pstRqstNS.php"
    
    # Mapping of country codes to corridor values
    CORRIDOR_MAPPING = {
        'PAK': {'currency': 'PKR', 'name': 'Pakistan'},      # Pakistan - Pakistani Rupee
        'IND': {'currency': 'INR', 'name': 'India'},         # India - Indian Rupee
        'BGD': {'currency': 'BDT', 'name': 'Bangladesh'},    # Bangladesh - Bangladesh Taka
        'PHL': {'currency': 'PHP', 'name': 'Philippines'},   # Philippines - Philippine Peso
        'NPL': {'currency': 'NPR', 'name': 'Nepal'},         # Nepal - Nepalese Rupee
        'LKA': {'currency': 'LKR', 'name': 'Sri Lanka'},     # Sri Lanka - Sri Lankan Rupee
        'IDN': {'currency': 'IDR', 'name': 'Indonesia'},     # Indonesia - Indonesian Rupiah
        'VNM': {'currency': 'VND', 'name': 'Vietnam'},       # Vietnam - Vietnamese Dong
    }
    
    # Reverse mapping from currency to corridor
    CURRENCY_TO_CORRIDOR = {
        'PKR': 'PAK',
        'INR': 'IND',
        'BDT': 'BGD',
        'PHP': 'PHL',
        'NPR': 'NPL',
        'LKR': 'LKA',
        'IDR': 'IDN',
        'VND': 'VNM',
    }

    def __init__(self, name="placid", **kwargs):
        """
        Initialize the Placid provider.

        Args:
            name: Internal provider name (defaults to 'placid')
            kwargs: Additional config / session parameters
        """
        super().__init__(name=name, base_url=self.BASE_URL, **kwargs)
        self.session = requests.Session()

        # Example default headers matching your logs
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                           "Version/18.3 Safari/605.1.15"),
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        
        # Initialize logger
        self.logger = logging.getLogger(f"providers.{name}")

    def get_exchange_rate(
        self,
        source_country: str,
        corridor_val: str = "PAK",
        rndval: str = "1740963881748",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get exchange rate from Placid for a given corridor.
        
        Args:
            source_country: Source country code (e.g., "US")
            corridor_val: Corridor value (e.g., "PAK" for Pakistan)
            rndval: Random value for request
            
        Returns:
            Dictionary with exchange rate data
        """
        # Validate inputs to prevent unnecessary API calls
        if not corridor_val:
            return {
                "provider": self.name,
                "success": False,
                "source_country": source_country,
                "corridor_val": corridor_val,
                "rate": 0.0,
                "error_message": "Corridor value cannot be empty"
            }
            
        if not source_country:
            return {
                "provider": self.name,
                "success": False,
                "source_country": source_country,
                "corridor_val": corridor_val,
                "rate": 0.0,
                "error_message": "Source country cannot be empty"
            }
            
        if not isinstance(rndval, str) or not rndval.isdigit():
            return {
                "provider": self.name,
                "success": False,
                "source_country": source_country,
                "corridor_val": corridor_val,
                "rate": 0.0,
                "error_message": "Invalid rndval parameter"
            }
            
        # Normalize inputs
        corridor_val = corridor_val.strip().upper()
        source_country = source_country.strip().upper()
        
        # Check if source country is valid
        valid_source_countries = ["US", "GB", "EU", "CA", "AU"]
        if source_country not in valid_source_countries:
            self.logger.warning(f"Unknown source country: {source_country}, this may affect rate accuracy")
            return {
                "provider": self.name,
                "success": False,
                "source_country": source_country,
                "corridor_val": corridor_val,
                "rate": 0.0,
                "error_message": f"Invalid source country. Supported countries: {', '.join(valid_source_countries)}"
            }
        
        try:
            # Get a current timestamp for rndval if not provided
            if not rndval:
                rndval = str(int(time.time() * 1000))
                
            # Build the query params
            query_params = {
                "TaskType": "ChgContIndx",
                "Val1": corridor_val,
                "Val2": "NIL",
                "Val3": "NIL",
                "Val4": "NIL",
                "Val5": "NIL",
                "Val6": "NIL",
            }
            
            # Build the POST data
            data = {
                "rndval": rndval,
            }
            
            # Make the request
            url = f"{self.BASE_URL}{self.ENDPOINT}"
            response = self.session.post(url, params=query_params, data=data, timeout=15)
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            content = response.text
            
            # Check if the response contains the corridor
            if corridor_val not in content:
                # For empty corridor, we might still get a response but not with the corridor
                # Look for standard pattern of data being returned
                if '|//|' in content:
                    # Generic response without specific corridor data
                    self.logger.warning(f"Response does not contain specific data for corridor {corridor_val}")
                    return {
                        "provider": self.name,
                        "success": True,
                        "source_country": source_country,
                        "corridor_val": corridor_val,
                        "rate": 0.0,
                        "raw_data": content,
                        "error_message": None
                    }
                else:
                    self.logger.error(f"Corridor {corridor_val} not found in response")
                    raise PlacidCorridorUnsupportedError(f"Corridor {corridor_val} not supported")
            
            # Extract the currency code
            # If it's in our mapping, use that, otherwise use the provided corridor value
            if corridor_val in self.CORRIDOR_MAPPING:
                currency_code = self.CORRIDOR_MAPPING[corridor_val]["currency"]
            else:
                self.logger.warning(f"Unknown corridor value: {corridor_val}, using it as currency code")
                currency_code = corridor_val
            
            # Try to extract the exchange rate
            pattern = rf"(\d+[\.,]?\d*)\s*{currency_code}"
            match = re.search(pattern, content)
            
            if match:
                # Parse the rate and remove commas (used as thousands separators)
                rate_str = match.group(1).replace(",", "")
                rate = float(rate_str)
                
                return {
                    "provider": self.name,
                    "success": True,
                    "source_country": source_country,
                    "corridor_val": corridor_val,
                    "rate": rate,
                    "raw_data": content,
                    "error_message": None
                }
            else:
                # Response doesn't have an exchange rate
                self.logger.error(f"Could not find exchange rate for {currency_code} in Placid response.")
                raise PlacidResponseError(f"Could not find exchange rate for {currency_code} in Placid response.")
            
        except (requests.RequestException, ConnectionError) as e:
            self.logger.error(f"Connection error to Placid API: {str(e)}")
            raise PlacidConnectionError(f"Failed to connect to Placid API: {str(e)}")
        
        except PlacidError:
            # Just re-raise Placid-specific errors
            raise
        
        except Exception as e:
            self.logger.error(f"Unexpected error processing Placid exchange rate: {str(e)}")
            raise PlacidApiError(f"Error processing Placid response: {str(e)}")
        
    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        target_currency: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for converting an amount from source to target currency.
        
        Args:
            amount: Amount to convert
            source_currency: Source currency code (e.g., "USD")
            target_currency: Target currency code (e.g., "PKR")
            
        Optional kwargs:
            source_country: Source country code (defaults based on currency)
            
        Returns:
            Dictionary with quote data
        """
        # Validate inputs
        if not source_currency or not target_currency:
            return {
                "provider": self.name,
                "success": False,
                "source_currency": source_currency,
                "target_currency": target_currency,
                "send_amount": float(amount) if amount else 0.0,
                "exchange_rate": 0.0,
                "error_message": "Source or target currency cannot be empty",
                "receive_amount": 0.0
            }
        
        # Validate amount
        try:
            amount_value = float(amount)
            if amount_value <= 0:
                return {
                    "provider": self.name,
                    "success": False,
                    "source_currency": source_currency,
                    "target_currency": target_currency,
                    "send_amount": float(amount),
                    "exchange_rate": 0.0,
                    "error_message": "Amount must be positive",
                    "receive_amount": 0.0
                }
        except (ValueError, TypeError):
            return {
                "provider": self.name,
                "success": False,
                "source_currency": source_currency,
                "target_currency": target_currency,
                "send_amount": 0.0,
                "exchange_rate": 0.0,
                "error_message": "Invalid amount",
                "receive_amount": 0.0
            }
            
        # Normalize inputs
        source_currency = source_currency.strip().upper()
        target_currency = target_currency.strip().upper()
        
        # Get source country from kwargs or default mapping
        source_country = kwargs.get("source_country", None)
        if not source_country:
            # Map currency to default country code
            currency_to_country = {
                "USD": "US",
                "GBP": "GB",
                "EUR": "EU",
                "CAD": "CA",
                "AUD": "AU"
            }
            source_country = currency_to_country.get(source_currency, "US")
            self.logger.info(f"Source country not provided, defaulting to {source_country} for {source_currency}")
        
        # Find corridor value for target currency
        corridor_val = self.CURRENCY_TO_CORRIDOR.get(target_currency)
        
        if not corridor_val:
            self.logger.warning(f"No corridor mapping found for currency {target_currency}, using as-is")
            corridor_val = target_currency
            
        # Validate the source currency
        valid_source_currencies = ["USD", "GBP", "EUR", "CAD", "AUD"]
        if source_currency not in valid_source_currencies:
            return {
                "provider": self.name,
                "success": False,
                "source_country": source_country,
                "source_currency": source_currency,
                "target_currency": target_currency,
                "send_amount": float(amount),
                "exchange_rate": 0.0,
                "error_message": f"Invalid source currency. Supported currencies: {', '.join(valid_source_currencies)}",
                "receive_amount": 0.0
            }
        
        try:
            # Get exchange rate
            rate_result = self.get_exchange_rate(
                source_country=source_country,
                corridor_val=corridor_val
            )
            
            # Calculate receive amount
            exchange_rate = rate_result.get("rate", 0.0)
            receive_amount = float(amount) * exchange_rate
            
            return {
                "provider": self.name,
                "success": True,
                "source_country": source_country,
                "source_currency": source_currency,
                "target_currency": target_currency,
                "send_amount": float(amount),
                "exchange_rate": exchange_rate,
                "error_message": None,
                "receive_amount": receive_amount
            }
            
        except PlacidError as e:
            return {
                "provider": self.name,
                "success": False,
                "source_country": source_country,
                "source_currency": source_currency,
                "target_currency": target_currency,
                "send_amount": float(amount),
                "exchange_rate": 0.0,
                "error_message": str(e),
                "receive_amount": 0.0
            }
        
        except Exception as e:
            self.logger.error(f"Error getting quote from Placid: {str(e)}")
            return {
                "provider": self.name,
                "success": False,
                "source_country": source_country if source_country else "unknown",
                "source_currency": source_currency,
                "target_currency": target_currency,
                "send_amount": float(amount),
                "exchange_rate": 0.0,
                "error_message": f"Unexpected error: {str(e)}",
                "receive_amount": 0.0
            } 