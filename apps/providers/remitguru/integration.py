"""
RemitGuru Money Transfer Integration

This module implements the integration with RemitGuru, a digital money transfer service
that offers competitive rates for international remittances.

The integration uses RemitGuru's public API to fetch exchange rates and fees
for international money transfers.
"""

import json
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional
import requests

from apps.providers.base.provider import RemittanceProvider

# Setup logging
logger = logging.getLogger(__name__)


class RemitGuruProvider(RemittanceProvider):
    """
    Integration with RemitGuru's public API.
    
    This class implements a client for RemitGuru's API to retrieve
    exchange rates and fees for international money transfers.
    
    Example usage:
        provider = RemitGuruProvider()
        result = provider.get_exchange_rate(
            send_amount=Decimal("500.00"),
            send_currency="GBP",
            receive_country="IN"
        )
    """
    
    BASE_URL = "https://www.remitguru.com"
    QUOTE_ENDPOINT = "/transfer/jsp/getQTStatistics.jsp"
    
    # Corridor mapping: map country codes to RemitGuru's expected country format
    CORRIDOR_MAPPING = {
        "UK": "GB",      # United Kingdom
        "GB": "GB",      # United Kingdom (ISO code)
        "IN": "IN",      # India
        "PH": "PH",      # Philippines
        "PK": "PK",      # Pakistan
        "US": "US",      # United States
        # Add more country mappings as needed
    }
    
    # Currency mapping for countries 
    CURRENCY_MAPPING = {
        "GB": "GBP",     # United Kingdom - British Pound
        "IN": "INR",     # India - Indian Rupee
        "PH": "PHP",     # Philippines - Philippine Peso
        "PK": "PKR",     # Pakistan - Pakistani Rupee
        "US": "USD",     # United States - US Dollar
        # Add more currency mappings as needed
    }
    
    # Known supported corridors based on testing
    SUPPORTED_CORRIDORS = [
        ("GB", "IN"),  # UK to India
        # Add more as they are discovered
    ]
    
    def __init__(self):
        """Initialize the RemitGuruProvider."""
        super().__init__(name="RemitGuru", base_url=self.BASE_URL)
        
        # Create a session for persistent connections and cookies
        self.session = requests.Session()
        
        # Set common headers for all requests
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': '*/*',
            'Origin': self.BASE_URL,
            'Referer': f"{self.BASE_URL}/",
            'Connection': 'keep-alive',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        
        # Visit the homepage first to get cookies
        self._visit_homepage()
    
    def _visit_homepage(self):
        """Visit the homepage to get necessary cookies."""
        try:
            logger.debug("Visiting RemitGuru homepage to get cookies")
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()
            logger.debug(f"HomePage request successful. Cookies: {self.session.cookies}")
            
            # Sleep briefly to avoid rate limiting
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error visiting RemitGuru homepage: {str(e)}")
    
    def _build_corridor_string(self, send_country: str, send_currency: str, 
                              receive_country: str, receive_currency: str) -> str:
        """
        Build the corridor string required by RemitGuru's API.
        
        Format: [SEND_COUNTRY]~[SEND_CURRENCY]~[REC_COUNTRY]~[REC_CURRENCY]
        Example: GB~GBP~IN~INR
        
        Args:
            send_country: Two-letter country code for sending country
            send_currency: Three-letter currency code for sending currency
            receive_country: Two-letter country code for receiving country
            receive_currency: Three-letter currency code for receiving currency
            
        Returns:
            Corridor string
        """
        return f"{send_country}~{send_currency}~{receive_country}~{receive_currency}"
    
    def is_corridor_supported(self, send_country: str, receive_country: str) -> bool:
        """
        Check if a corridor is supported based on our testing.
        
        Args:
            send_country: Two-letter country code for sending country
            receive_country: Two-letter country code for receiving country
            
        Returns:
            True if supported, False otherwise
        """
        return (send_country, receive_country) in self.SUPPORTED_CORRIDORS
    
    def get_quote(self, send_amount: Decimal, send_country: str, receive_country: str) -> Optional[Dict]:
        """
        Call RemitGuru's API to get a quote for international money transfer.
        
        Args:
            send_amount: Amount to send
            send_country: Country code for sending country
            receive_country: Country code for receiving country
            
        Returns:
            Dictionary with exchange rate, fees, and other details or None if the request fails
        """
        # Map country codes to RemitGuru's format
        send_country_mapped = self.CORRIDOR_MAPPING.get(send_country, send_country)
        receive_country_mapped = self.CORRIDOR_MAPPING.get(receive_country, receive_country)
        
        # Get currencies for the countries
        send_currency = self.CURRENCY_MAPPING.get(send_country_mapped)
        receive_currency = self.CURRENCY_MAPPING.get(receive_country_mapped)
        
        if not send_currency or not receive_currency:
            logger.error(f"Unable to determine currencies for corridor {send_country} → {receive_country}")
            return None
        
        # Check if corridor is known to be supported
        if not self.is_corridor_supported(send_country_mapped, receive_country_mapped):
            logger.warning(f"Corridor {send_country_mapped} → {receive_country_mapped} is not in the list of known supported corridors")
            # Still proceed with the request as new corridors might be added
        
        # Build the corridor string
        corridor = self._build_corridor_string(
            send_country=send_country_mapped,
            send_currency=send_currency,
            receive_country=receive_country_mapped,
            receive_currency=receive_currency
        )
        
        # Prepare the payload exactly matching the curl example
        payload = {
            'amountTransfer': str(int(send_amount)),  # Format as integer like in the example
            'corridor': corridor,
            'sendMode': 'CIP-FER'  # This seems to be a default mode based on the example
        }
        
        url = f"{self.BASE_URL}{self.QUOTE_ENDPOINT}"
        
        try:
            logger.debug(f"Making request to RemitGuru API: {url} with payload: {payload}")
            logger.debug(f"Headers: {self.session.headers}")
            logger.debug(f"Cookies: {self.session.cookies}")
            
            # Make the API request
            response = self.session.post(url, data=payload, timeout=30)
            response.raise_for_status()
            
            # RemitGuru returns pipe-delimited response
            # Format: receive_amount|exchange_rate|fee|send_amount|error_message|is_valid|send_currency|error_code
            response_text = response.text.strip()
            logger.debug(f"RemitGuru API response: {response_text}")
            
            # For debugging, print the full response including headers
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            
            if not response_text or '|' not in response_text:
                logger.error(f"Invalid response format from RemitGuru API: {response_text}")
                return None
            
            # Parse the pipe-delimited response
            parts = response_text.split('|')
            if len(parts) < 7:
                logger.error(f"Insufficient data in RemitGuru API response: {response_text}")
                return None
            
            # Extract values from response
            try:
                # Get error message if present
                error_message = parts[4] if len(parts) > 4 and parts[4] else None
                error_code = parts[7] if len(parts) > 7 and parts[7] else None
                
                # Check if response indicates invalid quote
                is_valid_str = parts[5] if len(parts) > 5 else "false"
                is_valid = is_valid_str.lower() == 'true'
                
                if not is_valid:
                    logger.warning(f"RemitGuru returned invalid quote: {error_message} (Error code: {error_code})")
                    return {
                        'is_valid': False,
                        'error': error_message or "Invalid quote returned",
                        'error_code': error_code,
                        'raw_response': response_text
                    }
                
                # Parse values from valid response
                receive_amount = Decimal(parts[0]) if parts[0] and parts[0] != '0' else None
                exchange_rate = Decimal(parts[1]) if parts[1] and parts[1] != '0' else None
                fee = Decimal(parts[2]) if parts[2] else Decimal('0')
                send_amount_confirmed = Decimal(parts[3]) if parts[3] and parts[3] != '0' else send_amount
                send_currency_confirmed = parts[6] if parts[6] and parts[6] != '0' else send_currency
                
                result = {
                    'receive_amount': receive_amount,
                    'exchange_rate': exchange_rate,
                    'fee': fee,
                    'send_amount': send_amount_confirmed,
                    'is_valid': is_valid,
                    'send_currency': send_currency_confirmed,
                    'receive_currency': receive_currency,
                    'raw_response': response_text
                }
                
                return result
                
            except (IndexError, ValueError) as e:
                logger.error(f"Error parsing RemitGuru API response: {str(e)}")
                return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to RemitGuru API: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in RemitGuru API request: {str(e)}")
            return None
    
    def get_exchange_rate(
        self, 
        send_amount: Decimal, 
        send_currency: str, 
        receive_country: str
    ) -> Optional[Dict]:
        """
        Get exchange rate and fees for a money transfer.
        
        Args:
            send_amount: Amount to send
            send_currency: Source currency code (e.g., 'GBP', 'USD')
            receive_country: Destination country code (e.g. 'IN')
            
        Returns:
            Dictionary containing rate information or None if failed
        """
        # Determine the sending country based on currency
        send_country = None
        for country, currency in self.CURRENCY_MAPPING.items():
            if currency == send_currency:
                send_country = country
                break
        
        if not send_country:
            logger.error(f"Unable to determine sending country for currency {send_currency}")
            return None
        
        try:
            # Get the quote from RemitGuru API
            quote = self.get_quote(
                send_amount=send_amount,
                send_country=send_country,
                receive_country=receive_country
            )
            
            if not quote:
                logger.error(f"Failed to get quote from RemitGuru for {send_currency} → {receive_country}")
                return None
            
            # Check if the quote is valid
            if not quote.get('is_valid', False):
                error_message = quote.get('error', "Invalid quote returned by provider")
                error_code = quote.get('error_code')
                
                logger.warning(f"RemitGuru returned an invalid quote for {send_currency} → {receive_country}: {error_message} ({error_code})")
                
                return {
                    "provider": self.name,
                    "send_amount": float(send_amount),
                    "send_currency": send_currency,
                    "receive_country": receive_country,
                    "supported": False,
                    "error": error_message,
                    "error_code": error_code,
                    "raw_json": quote
                }
            
            # Format the response in our standard format
            receive_currency = quote.get('receive_currency')
            
            result = {
                "provider": self.name,
                "send_amount": float(send_amount),
                "send_currency": send_currency,
                "receive_currency": receive_currency,
                "receive_country": receive_country,
                "exchange_rate": float(quote.get('exchange_rate')) if quote.get('exchange_rate') else None,
                "receive_amount": float(quote.get('receive_amount')) if quote.get('receive_amount') else None,
                "fee": float(quote.get('fee')) if quote.get('fee') else 0.0,
                "delivery_time": 48.0,  # Default to 48 hours
                "supported": True,
                "raw_json": quote
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting RemitGuru exchange rate: {str(e)}")
            return None
    
    def get_supported_countries(self) -> List[Dict]:
        """
        Get a list of countries supported by RemitGuru.
        
        Returns:
            List of dictionaries containing country information
        """
        # Based on our testing, we only include confirmed supported corridors
        supported_corridors = [
            {"from_country": "GB", "to_country": "IN", "from_currency": "GBP", "to_currency": "INR"},
            # Other corridors we've tested (GBP→PH, GBP→PK, USD→IN) have error "Fee Not Define"
        ]
        
        return supported_corridors 